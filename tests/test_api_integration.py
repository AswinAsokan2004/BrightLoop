"""Real API/service workflows through an isolated SQLite adapter; no production DB needed."""
import pytest
from fastapi.testclient import TestClient
from tests.browser_api import create_test_app


@pytest.fixture
def client(tmp_path):
    app = create_test_app(tmp_path / 'test.sqlite')
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def authenticate(client, email='integration@example.com', password='Integration!Pass123'):
    result = client.post('/api/auth/login', json={'email': email, 'password': password})
    assert result.status_code == 200, result.text
    return {'Authorization': 'Bearer ' + result.json()['access_token']}, result.json()


def test_subscription_invoice_payment_and_reports(client):
    headers, _ = authenticate(client)
    customer = client.post('/api/customers', headers=headers, json={'name': 'UI Customer', 'email': 'ui@example.com'}).json()
    result = client.post('/api/subscriptions', headers=headers, json={
        'customer_id': customer['id'], 'plan_id': 1, 'payment_term_id': 1,
        'start_date': '2026-10-31', 'currency': 'INR',
        'lines': [{'product_id': 1, 'quantity': 1}],
    })
    assert result.status_code == 201, result.text
    sub = result.json()
    assert sub['recurring_total'] == '100.00'
    for state in ['quotation', 'confirmed', 'active']:
        result = client.post(f"/api/subscriptions/{sub['id']}/state", headers=headers, json={'state': state})
        assert result.status_code == 200, result.text
    result = client.post(f"/api/subscriptions/{sub['id']}/invoices", headers=headers)
    assert result.status_code == 201, result.text
    invoice = result.json()
    result = client.post(f"/api/invoices/{invoice['id']}/confirm", headers=headers)
    assert result.status_code == 200, result.text
    result = client.post(f"/api/invoices/{invoice['id']}/payments", headers=headers, json={'method': 'bank_transfer', 'amount': '100.00', 'payment_date': '2026-10-31'})
    assert result.status_code == 201, result.text
    result = client.get(f"/api/invoices/{invoice['id']}", headers=headers)
    assert result.json()['state'] == 'paid'
    assert result.json()['amount_due'] == '0.00'
    customer_headers, _ = authenticate(client, 'customer@example.com', 'Customer!Pass123')
    assert client.get(f"/api/portal/subscriptions/{sub['id']}", headers=customer_headers).status_code == 404
    assert client.get(f"/api/portal/invoices/{invoice['id']}", headers=customer_headers).status_code == 404
    assert client.get(f"/api/invoices/{invoice['id']}/print", headers=headers).status_code == 200
    report = client.get('/api/reports/summary', headers=headers)
    assert report.status_code == 200, report.text
    assert report.json()['revenue_collected'] == '100.00'
    monthly = client.get('/api/reports/revenue-by-month', headers=headers)
    assert monthly.status_code == 200, monthly.text
    assert monthly.json()[0]['collected'] == '100.00'
    assert client.post('/api/billing/run', headers=headers, json={'run_date': '2026-10-31'}).status_code == 200


def test_customer_isolation_and_staff_permissions(client):
    admin, _ = authenticate(client)
    customer, _ = authenticate(client, 'customer@example.com', 'Customer!Pass123')
    staff, _ = authenticate(client, 'staff@example.com', 'Staff!Pass123')
    assert client.get('/api/customers', headers=customer).status_code == 403
    assert client.get('/api/portal/profile', headers=customer).json()['email'] == 'customer@example.com'
    assert client.get('/api/portal/subscriptions/9999', headers=customer).status_code == 404
    assert client.get('/api/products', headers=staff).status_code == 200
    assert client.post('/api/products', headers=staff, json={'name': 'Forbidden', 'product_type': 'service'}).status_code == 403
    assert client.get('/api/users', headers=staff).status_code == 403


def test_auth_rotation_and_validation(client):
    _, tokens = authenticate(client)
    response = client.post('/api/auth/refresh', json={'refresh_token': tokens['refresh_token']})
    assert response.status_code == 200, response.text
    assert client.post('/api/auth/refresh', json={'refresh_token': tokens['refresh_token']}).status_code == 401
    headers = {'Authorization': 'Bearer ' + response.json()['access_token']}
    invalid = client.post('/api/plans', headers=headers, json={'name': 'Invalid', 'code': 'INVALID', 'price': '100.00', 'billing_period': 'monthly', 'start_date': '2026-12-01', 'end_date': '2026-01-01'})
    assert invalid.status_code == 422


def test_catalog_template_discount_and_repeat_billing(client):
    headers, _ = authenticate(client)

    def create(path, body):
        response = client.post('/api' + path, headers=headers, json=body)
        assert response.status_code == 201, response.text
        return response.json()

    tax = create('/taxes', {'name': 'GST', 'tax_type': 'percent', 'rate': '18'})
    product = create('/products', {'name': 'CRM seats', 'product_type': 'service', 'sales_price': '1000.00', 'tax_ids': [tax['id']]})
    attribute = create('/attributes', {'name': 'Brand', 'values': [{'value': 'Odoo', 'extra_price': '50.00'}]})
    variant = create(f"/products/{product['id']}/variants", {'sku': 'CRM-ODOO', 'attribute_value_ids': [attribute['values'][0]['id']]})
    assert variant['unit_price'] == '1050.00'
    discount = create('/discounts', {'name': 'Volume', 'discount_type': 'percent', 'value': '10.00', 'scope': 'product', 'min_quantity': 5, 'product_ids': [product['id']], 'start_date': '2026-01-01'})
    template = create('/quotation-templates', {'name': 'CRM quote', 'plan_id': 1, 'validity_days': 30, 'lines': [{'product_id': product['id'], 'variant_id': variant['id'], 'quantity': 5}]})
    subscription = create('/subscriptions/from-template', {'template_id': template['id'], 'customer_id': 1, 'payment_term_id': 1, 'start_date': '2026-10-31'})
    assert subscription['state'] == 'quotation'
    for state in ['confirmed', 'active']:
        result = client.post(f"/api/subscriptions/{subscription['id']}/state", headers=headers, json={'state': state})
        assert result.status_code == 200, result.text
    run = client.post('/api/billing/run', headers=headers, json={'run_date': '2026-10-31'})
    assert run.status_code == 200, run.text
    assert run.json()['invoices_created'] == 1
    assert client.post('/api/billing/run', headers=headers, json={'run_date': '2026-10-31'}).json()['invoices_created'] == 0
    invoice = client.get('/api/invoices', headers=headers).json()['items'][0]
    assert invoice['total'] == '5575.50'
    assert client.get(f"/api/discounts/{discount['id']}", headers=headers).json()['used_count'] == 1
    assert client.post(f"/api/invoices/{invoice['id']}/cancel", headers=headers).status_code == 200
    assert client.get(f"/api/discounts/{discount['id']}", headers=headers).json()['used_count'] == 0
