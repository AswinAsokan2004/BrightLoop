"""Read context for the workspace stays scoped to the subscription, including portal use."""
from datetime import date, timedelta
from sqlalchemy import update
from app.core.database import get_db
from app.models import Subscription
from tests.test_api_integration import authenticate


def create_subscription(client, headers, customer_id=1, lines=None):
    response=client.post('/api/subscriptions',headers=headers,json={
        'customer_id':customer_id,'plan_id':1,'payment_term_id':1,
        'start_date':date.today().isoformat(),'expiry_date':(date.today()+timedelta(days=90)).isoformat(),
        'lines':lines or [{'product_id':1,'quantity':1}],
    })
    assert response.status_code==201,response.text
    return response.json()


def invoice_subscription(client,headers,subscription):
    for state in ['quotation','confirmed','active']:
        response=client.post(f"/api/subscriptions/{subscription['id']}/state",headers=headers,json={'state':state})
        assert response.status_code==200,response.text
    response=client.post(f"/api/subscriptions/{subscription['id']}/invoices",headers=headers)
    assert response.status_code==201,response.text
    return response.json()


def test_workspace_named_context_and_policy_are_available_to_owner(client):
    admin,_=authenticate(client)
    subscription=create_subscription(client,admin)
    detail=client.get(f"/api/subscriptions/{subscription['id']}",headers=admin).json()
    assert detail['customer_name']=='Browser Customer'
    assert detail['plan_name']=='Monthly'
    assert detail['customer']['email']=='customer@example.com'
    assert detail['payment_term']=={'id':1,'name':'Immediate','due_days':0}
    assert detail['plan']['pausable'] is True
    assert detail['lines'][0]['product']=={'id':1,'name':'Test CRM'}
    assert detail['state_logs'][0]['changed_by_user']=={'id':1,'name':'Integration Admin'}
    assert detail['salesperson']=={'id':1,'name':'Integration Admin'}
    assert 'price' not in detail['plan']  # agreed line prices are shown, not an unrelated plan price
    assert 'cost_price' not in detail['lines'][0]['product']
    assert 'password_hash' not in str(detail)
    summary=client.get('/api/subscriptions',headers=admin).json()['items'][0]
    assert (summary['customer_name'],summary['plan_name'])==('Browser Customer','Monthly')
    customer,_=authenticate(client,'customer@example.com','Customer!Pass123')
    owned=client.get(f"/api/portal/subscriptions/{subscription['id']}",headers=customer)
    assert owned.status_code==200,owned.text
    assert owned.json()['plan']['pausable'] is True
    assert client.get('/api/plans/1',headers=customer).status_code==403


def test_portal_related_invoices_filter_preserves_ownership(client):
    admin,_=authenticate(client)
    first=create_subscription(client,admin)
    second=create_subscription(client,admin)
    foreign_customer=client.post('/api/customers',headers=admin,json={'name':'Other Company','email':'other@example.com'}).json()
    foreign=create_subscription(client,admin,foreign_customer['id'])
    own_invoice=invoice_subscription(client,admin,first)
    invoice_subscription(client,admin,second)
    invoice_subscription(client,admin,foreign)
    customer,_=authenticate(client,'customer@example.com','Customer!Pass123')
    response=client.get(f"/api/portal/invoices?subscription_id={first['id']}",headers=customer)
    assert response.status_code==200,response.text
    assert response.json()['total']==1
    assert response.json()['items'][0]['id']==own_invoice['id']
    assert client.get(f"/api/portal/invoices?subscription_id={foreign['id']}",headers=customer).json()['total']==0
    assert client.get(f"/api/portal/subscriptions/{foreign['id']}",headers=customer).status_code==404


def test_expired_quotation_can_be_revised_and_line_tax_details_survive(client):
    admin,_=authenticate(client)
    tax=client.post('/api/taxes',headers=admin,json={'name':'Reduced tax','tax_type':'percent','rate':'5.00'}).json()
    subscription=create_subscription(client,admin,lines=[{'product_id':1,'quantity':2,'unit_price':'25.00','description':'Negotiated CRM seats','tax_ids':[tax['id']]}])
    assert subscription['lines'][0]['taxes'][0]['name']=='Reduced tax'
    assert subscription['recurring_total']=='52.50'
    client.post(f"/api/subscriptions/{subscription['id']}/state",headers=admin,json={'state':'quotation'})
    dependency=client.app.dependency_overrides[get_db]()
    db=next(dependency)
    try:
        db.execute(update(Subscription).where(Subscription.id==subscription['id']).values(quotation_valid_until=date.today()-timedelta(days=1)))
        db.commit()
    finally:
        dependency.close()
    assert client.post(f"/api/subscriptions/{subscription['id']}/state",headers=admin,json={'state':'confirmed'}).status_code==400
    assert client.post(f"/api/subscriptions/{subscription['id']}/state",headers=admin,json={'state':'draft'}).status_code==200
    refreshed=client.post(f"/api/subscriptions/{subscription['id']}/state",headers=admin,json={'state':'quotation'})
    assert refreshed.status_code==200
    assert refreshed.json()['quotation_valid_until']>=date.today().isoformat()
    assert refreshed.json()['lines'][0]['description']=='Negotiated CRM seats'
