from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import update
from app.core.database import get_db
from app.models import Customer, Invoice
from tests.test_api_integration import authenticate
from tests.test_subscription_workspace import create_subscription, invoice_subscription


def test_finance_currency_filters_and_drilldown_consistency(client):
    admin, _ = authenticate(client)
    own = create_subscription(client, admin)
    invoice = invoice_subscription(client, admin, own)
    assert client.post(f"/api/invoices/{invoice['id']}/confirm", headers=admin).status_code == 200
    assert (
        client.post(
            f"/api/invoices/{invoice['id']}/payments",
            headers=admin,
            json={
                "method": "bank_transfer",
                "amount": "40.00",
                "payment_date": date.today().isoformat(),
                "reference": "FINANCE-40",
            },
        ).status_code
        == 201
    )
    usd = client.post(
        "/api/subscriptions",
        headers=admin,
        json={
            "customer_id": 1,
            "plan_id": 1,
            "payment_term_id": 1,
            "start_date": date.today().isoformat(),
            "expiry_date": (date.today() + timedelta(days=90)).isoformat(),
            "currency": "USD",
            "lines": [{"product_id": 1, "quantity": 2}],
        },
    ).json()
    usd_invoice = invoice_subscription(client, admin, usd)
    client.post(f"/api/invoices/{usd_invoice['id']}/confirm", headers=admin)
    get_session = client.app.dependency_overrides[get_db]
    with next(get_session()) as db:
        db.execute(
            update(Invoice)
            .where(Invoice.id == invoice["id"])
            .values(due_date=date.today() - timedelta(days=1))
        )
        db.commit()
    report = client.get("/api/reports/finance?currency=INR", headers=admin)
    assert report.status_code == 200, report.text
    data = report.json()
    assert data["currencies"] == ["INR", "USD"]
    assert data["active_subscriptions"] == 1
    assert Decimal(data["invoiced_total"]) == 100
    assert Decimal(data["revenue_collected"]) == 40
    assert Decimal(data["outstanding_amount"]) == 60
    assert Decimal(data["overdue_amount"]) == 60
    assert data["overdue_count"] == data["invoice_count"] == 1
    assert data["invoices"][0]["id"] == invoice["id"]
    assert data["payments"][0]["invoice_number"] == invoice["number"]
    assert data["payments"][0]["customer_name"] == "Browser Customer"
    usd_data = client.get("/api/reports/finance?currency=USD", headers=admin).json()
    assert Decimal(usd_data["invoiced_total"]) == 200
    assert Decimal(usd_data["revenue_collected"]) == 0
    filtered = client.get("/api/reports/finance?currency=INR&customer_id=999999", headers=admin).json()
    assert filtered["active_subscriptions"] == filtered["invoice_count"] == filtered["payment_count"] == 0
    assert Decimal(filtered["invoiced_total"]) == 0
    future = (date.today() + timedelta(days=1)).isoformat()
    dated = client.get(f"/api/reports/finance?currency=INR&date_from={future}", headers=admin).json()
    assert dated["active_subscriptions"] == 1  # current portfolio is independent of report dates
    assert Decimal(dated["invoiced_total"]) == Decimal(dated["revenue_collected"]) == 0
    assert dated["invoices"] == dated["payments"] == dated["monthly"] == []
    billed = client.get("/api/reports/finance?currency=INR&invoice_view=billed", headers=admin).json()
    assert sum(Decimal(row["total"]) for row in billed["invoices"]) == Decimal(billed["invoiced_total"])
    assert len(data["monthly"]) == 1
    assert Decimal(data["monthly"][0]["collected"]) == 40


def test_finance_validation_permissions_and_bounded_name_options(client):
    admin, _ = authenticate(client)
    assert client.get("/api/reports/finance").status_code == 401
    staff, _ = authenticate(client, "staff@example.com", "Staff!Pass123")
    assert client.get("/api/reports/finance", headers=staff).status_code == 200
    customer, _ = authenticate(client, "customer@example.com", "Customer!Pass123")
    for path in ["/api/reports/finance", "/api/reports/options?kind=customer"]:
        assert client.get(path, headers=customer).status_code == 403
    for query in [
        "date_from=2026-10-31&date_to=2026-01-01",
        "size=51",
        "invoice_page=0",
        "currency=invalid",
        "invoice_view=invalid",
    ]:
        assert client.get("/api/reports/finance?" + query, headers=admin).status_code in [400, 422]
    get_session = client.app.dependency_overrides[get_db]
    with next(get_session()) as db:
        db.add_all(
            [Customer(name=f"Finance Name {i:02d}", email=f"finance{i}@example.com") for i in range(25)]
        )
        db.commit()
    first = client.get("/api/reports/options?kind=customer&q=Finance%20Name", headers=admin).json()
    second = client.get("/api/reports/options?kind=customer&q=Finance%20Name&page=2", headers=admin).json()
    assert len(first["items"]) == 20 and first["has_more"] is True
    assert len(second["items"]) == 5 and second["has_more"] is False
    assert not ({r["id"] for r in first["items"]} & {r["id"] for r in second["items"]})
    exact = client.get("/api/reports/options?kind=customer&q=Finance%20Name%2024", headers=admin).json()
    assert exact["items"][0]["name"] == "Finance Name 24"
    assert client.get("/api/reports/options?kind=customer&q=%25", headers=admin).json()["items"] == []
    assert client.get("/api/reports/options?kind=plan", headers=admin).json()["items"][0]["name"] == "Monthly"


def test_finance_status_boundaries_and_independent_pagination(client):
    """Draft/cancelled invoices and unsuccessful receipts must not inflate finance totals."""
    from app.models import Payment
    from app.models.enums import InvoiceState, PaymentMethod, PaymentStatus

    admin, _ = authenticate(client)
    invoices = [invoice_subscription(client, admin, create_subscription(client, admin)) for _ in range(5)]
    for invoice in invoices[1:4]:
        assert client.post(f"/api/invoices/{invoice['id']}/confirm", headers=admin).status_code == 200
    paid = invoices[3]
    assert (
        client.post(
            f"/api/invoices/{paid['id']}/payments",
            headers=admin,
            json={
                "method": "cash",
                "amount": "100.00",
                "payment_date": date.today().isoformat(),
            },
        ).status_code
        == 201
    )
    assert client.post(f"/api/invoices/{invoices[4]['id']}/cancel", headers=admin).status_code == 200
    get_session = client.app.dependency_overrides[get_db]
    with next(get_session()) as db:
        db.execute(
            update(Invoice)
            .where(Invoice.id == invoices[1]["id"])
            .values(due_date=date.today() - timedelta(days=1))
        )
        db.execute(update(Invoice).where(Invoice.id == invoices[2]["id"]).values(due_date=date.today()))
        for status in [PaymentStatus.pending, PaymentStatus.failed, PaymentStatus.refunded]:
            db.add(
                Payment(
                    invoice_id=invoices[1]["id"],
                    customer_id=1,
                    amount=Decimal("999.00"),
                    method=PaymentMethod.bank_transfer,
                    payment_date=date.today(),
                    status=status,
                )
            )
        db.commit()
    today = date.today().isoformat()
    query = f"/api/reports/finance?currency=INR&date_from={today}&date_to={today}"
    data = client.get(query, headers=admin).json()
    assert Decimal(data["invoiced_total"]) == 300
    assert Decimal(data["revenue_collected"]) == 100
    assert Decimal(data["outstanding_amount"]) == 200
    assert Decimal(data["overdue_amount"]) == 100
    assert data["overdue_count"] == data["payment_count"] == 1
    assert data["invoices"][0]["id"] == invoices[1]["id"]  # due today is not yet overdue
    assert Decimal(data["monthly"][0]["collected"]) == 100
    expected = {"all": 5, "billed": 3, "outstanding": 2, "overdue": 1}
    for view, count in expected.items():
        response = client.get(query + f"&invoice_view={view}", headers=admin).json()
        assert response["invoice_count"] == len(response["invoices"]) == count
        if view == "billed":
            assert {row["state"] for row in response["invoices"]} == {
                InvoiceState.confirmed.value,
                InvoiceState.paid.value,
            }
    first = client.get(query + "&invoice_view=all&size=1", headers=admin).json()
    second = client.get(
        query + "&invoice_view=all&size=1&invoice_page=2&subscription_page=2", headers=admin
    ).json()
    assert first["invoices"][0]["id"] != second["invoices"][0]["id"]
    assert first["subscriptions"][0]["id"] != second["subscriptions"][0]["id"]
    assert first["payments"] == second["payments"]  # other page controls do not move payments
    assert first["invoiced_total"] == second["invoiced_total"]
    beyond = client.get(query + "&payment_page=2&size=1", headers=admin).json()
    assert beyond["payments"] == [] and beyond["payment_count"] == 1
