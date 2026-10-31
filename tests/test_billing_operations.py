from datetime import date
from app.services.billing import BillingService
from tests.test_api_integration import authenticate


def setup_plan(client, headers, code="BILL-OPS", period="daily", auto_close=True):
    response = client.post(
        "/api/plans",
        headers=headers,
        json={
            "name": "Operations plan",
            "code": code,
            "price": "100.00",
            "billing_period": period,
            "start_date": "2020-01-01",
            "pausable": True,
            "auto_close": auto_close,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def subscription(client, headers, plan, state="active", start="2026-01-01", expiry="2026-01-03"):
    response = client.post(
        "/api/subscriptions",
        headers=headers,
        json={
            "customer_id": 1,
            "plan_id": plan,
            "payment_term_id": 1,
            "start_date": start,
            "expiry_date": expiry,
            "lines": [{"product_id": 1, "quantity": 1}],
        },
    )
    assert response.status_code == 201, response.text
    sub = response.json()
    if state != "draft":
        for target in ["quotation", "confirmed", "active"] + (["paused"] if state == "paused" else []):
            response = client.post(
                f"/api/subscriptions/{sub['id']}/state", headers=headers, json={"state": target}
            )
            assert response.status_code == 200, response.text
    return sub


def test_read_only_preview_matches_catchup_and_automatic_closure(client):
    headers, _ = authenticate(client)
    plan = setup_plan(client, headers)
    active = subscription(client, headers, plan)
    paused = subscription(client, headers, plan, "paused")
    subscription(client, headers, plan, "draft")
    subscription(client, headers, plan, start="2027-01-01", expiry="2027-12-31")
    before = client.get(f"/api/subscriptions/{active['id']}", headers=headers).json()
    preview = client.get("/api/billing/preview?run_date=2026-01-10&size=1", headers=headers)
    assert preview.status_code == 200, preview.text
    data = preview.json()
    assert (data["due_subscriptions"], data["auto_close_subscriptions"], data["total"]) == (1, 2, 1)
    assert data["items"][0]["id"] == active["id"]
    assert data["items"][0]["due_periods"] == 3
    assert data["items"][0]["first_period_end"] == "2026-01-01"
    closing = client.get(
        "/api/billing/preview?run_date=2026-01-10&kind=closing&size=1&page=2", headers=headers
    ).json()
    assert closing["items"][0]["id"] == paused["id"]
    assert closing["items"][0]["due_periods"] == 0
    assert client.get(f"/api/subscriptions/{active['id']}", headers=headers).json() == before
    assert client.get("/api/invoices", headers=headers).json()["total"] == 0
    run = client.post("/api/billing/run", headers=headers, json={"run_date": "2026-01-10"}).json()
    assert (run["invoices_created"], run["errors_count"]) == (3, 0)
    for sub in [active, paused]:
        assert client.get(f"/api/subscriptions/{sub['id']}", headers=headers).json()["state"] == "closed"
    first = client.get(f"/api/billing/runs/{run['id']}/invoices?size=2", headers=headers).json()
    second = client.get(f"/api/billing/runs/{run['id']}/invoices?size=2&page=2", headers=headers).json()
    assert first["total"] == second["total"] == 3
    assert len(first["items"]) == 2 and len(second["items"]) == 1
    assert {i["id"] for i in first["items"]}.isdisjoint(i["id"] for i in second["items"])
    assert first["items"][0]["customer_name"] == "Browser Customer"
    assert first["items"][0]["subscription_number"] == active["number"]
    again = client.post("/api/billing/run", headers=headers, json={"run_date": "2026-01-10"}).json()
    assert again["invoices_created"] == 0
    assert client.get(f"/api/billing/runs/{again['id']}/invoices", headers=headers).json()["items"] == []
    assert (
        client.get("/api/billing/preview?run_date=2026-01-10", headers=headers).json()["due_subscriptions"]
        == 0
    )


def test_month_end_preview_agrees_with_generated_periods(client):
    headers, _ = authenticate(client)
    plan = setup_plan(client, headers, period="monthly", auto_close=False)
    sub = subscription(client, headers, plan, start="2026-01-31", expiry="2026-12-31")
    preview = client.get("/api/billing/preview?run_date=2026-03-31", headers=headers).json()
    assert preview["items"][0]["due_periods"] == 3
    assert preview["items"][0]["first_period_end"] == "2026-02-27"
    run = client.post("/api/billing/run", headers=headers, json={"run_date": "2026-03-31"}).json()
    rows = client.get(f"/api/billing/runs/{run['id']}/invoices", headers=headers).json()["items"]
    assert [row["period_start"] for row in rows] == ["2026-01-31", "2026-02-28", "2026-03-31"]
    assert all(row["subscription_id"] == sub["id"] for row in rows)


def test_billing_failure_links_retry_and_permissions(client, monkeypatch):
    headers, _ = authenticate(client)
    plan = setup_plan(client, headers, auto_close=False)
    bad = subscription(client, headers, plan)
    good = subscription(client, headers, plan)
    original = BillingService._bill_subscription

    def fail_one(self, subscription_id, *args):
        if subscription_id == bad["id"]:
            raise ValueError("Invalid billing setup\nReview product lines")
        return original(self, subscription_id, *args)

    with monkeypatch.context() as patch:
        patch.setattr(BillingService, "_bill_subscription", fail_one)
        response = client.post("/api/billing/run", headers=headers, json={"run_date": "2026-01-03"})
    assert response.status_code == 200, response.text
    run = response.json()
    assert run["status"] == "completed" and run["errors_count"] == 1 and run["invoices_created"] == 3
    errors = client.get(f"/api/billing/runs/{run['id']}/failures", headers=headers).json()
    assert errors["total"] == 1
    assert errors["items"][0]["subscription_id"] == bad["id"]
    assert errors["items"][0]["subscription_number"] == bad["number"]
    assert errors["items"][0]["message"] == "Invalid billing setup\nReview product lines"
    assert (
        client.get(f"/api/billing/runs/{run['id']}/failures?size=1&page=2", headers=headers).json()["items"]
        == []
    )
    retry = client.post("/api/billing/run", headers=headers, json={"run_date": "2026-01-03"}).json()
    assert retry["errors_count"] == 0 and retry["invoices_created"] == 3
    assert client.get(f"/api/billing/runs/{retry['id']}/invoices", headers=headers).json()["total"] == 3
    assert client.get(f"/api/billing/runs/{run['id']}/invoices", headers=headers).json()["total"] == 3
    paths = [
        "/api/billing/preview?run_date=2026-01-03",
        f"/api/billing/runs/{run['id']}/invoices",
        f"/api/billing/runs/{run['id']}/failures",
    ]
    customer, _ = authenticate(client, "customer@example.com", "Customer!Pass123")
    staff, _ = authenticate(client, "staff@example.com", "Staff!Pass123")
    for path in paths:
        assert client.get(path).status_code == 401
        assert client.get(path, headers=customer).status_code == 403
        assert client.get(path, headers=staff).status_code == 200
    assert client.get("/api/billing/runs/999999/invoices", headers=headers).status_code == 404
    assert client.get("/api/billing/runs/999999/failures", headers=headers).status_code == 404
    assert client.get("/api/billing/preview?run_date=invalid", headers=headers).status_code == 422
    assert (
        client.get("/api/billing/preview?run_date=2026-01-03&kind=invalid", headers=headers).status_code
        == 422
    )


def test_preview_does_not_reserve_subscription_state(client):
    headers, _ = authenticate(client)
    plan = setup_plan(client, headers, auto_close=False)
    sub = subscription(client, headers, plan)
    preview = client.get("/api/billing/preview?run_date=2026-01-03", headers=headers).json()
    assert preview["due_subscriptions"] == 1 and preview["items"][0]["due_periods"] == 3
    # Someone pauses the subscription after the preview but before confirmation.
    assert (
        client.post(
            f"/api/subscriptions/{sub['id']}/state", headers=headers, json={"state": "paused"}
        ).status_code
        == 200
    )
    run = client.post("/api/billing/run", headers=headers, json={"run_date": "2026-01-03"}).json()
    assert run["invoices_created"] == run["errors_count"] == 0
    assert client.get(f"/api/billing/runs/{run['id']}/invoices", headers=headers).json()["total"] == 0
    assert client.get(f"/api/subscriptions/{sub['id']}", headers=headers).json()["state"] == "paused"


def test_cancelled_period_is_not_recreated_and_exhausted_schedule_can_be_cleared(client):
    from sqlalchemy import update
    from app.core.database import get_db
    from app.models import Subscription

    headers, _ = authenticate(client)
    plan = setup_plan(client, headers, auto_close=False)
    sub = subscription(client, headers, plan)
    response = client.post(f"/api/subscriptions/{sub['id']}/invoices", headers=headers)
    assert response.status_code == 201, response.text
    invoice = response.json()
    assert client.post(f"/api/invoices/{invoice['id']}/cancel", headers=headers).status_code == 200
    # Reproduce a stale scheduling pointer: uniqueness still protects the cancelled period.
    get_session = client.app.dependency_overrides[get_db]
    with next(get_session()) as db:
        db.execute(
            update(Subscription)
            .where(Subscription.id == sub["id"])
            .values(next_invoice_date=date(2026, 1, 1))
        )
        db.commit()
    preview = client.get("/api/billing/preview?run_date=2026-01-03", headers=headers).json()
    assert preview["items"][0]["due_periods"] == 3  # periods to check, not promised new invoices
    run = client.post("/api/billing/run", headers=headers, json={"run_date": "2026-01-03"}).json()
    assert run["invoices_created"] == 2
    linked = client.get(f"/api/billing/runs/{run['id']}/invoices", headers=headers).json()
    assert [row["period_start"] for row in linked["items"]] == ["2026-01-02", "2026-01-03"]
    assert client.get(f"/api/invoices/{invoice['id']}", headers=headers).json()["state"] == "cancelled"
    cleanup = client.get("/api/billing/preview?run_date=2026-01-10", headers=headers).json()
    assert cleanup["due_subscriptions"] == 1 and cleanup["items"][0]["due_periods"] == 0
    assert cleanup["items"][0]["first_period_end"] is None
    cleared = client.post("/api/billing/run", headers=headers, json={"run_date": "2026-01-10"}).json()
    assert cleared["invoices_created"] == 0
    final = client.get(f"/api/subscriptions/{sub['id']}", headers=headers).json()
    assert final["next_invoice_date"] is None and final["state"] == "active"
    assert (
        client.get("/api/billing/preview?run_date=2026-01-10", headers=headers).json()["due_subscriptions"]
        == 0
    )
