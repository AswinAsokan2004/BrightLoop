"""Isolated PostgreSQL finance load check; invoked only by the disposable DB fixture."""

import json
import time
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.core.database import SessionLocal
from app.main import app
from app.models import Invoice, Payment, Subscription
from app.models.enums import InvoiceState, PaymentMethod, PaymentStatus, SubscriptionState
from tests.conftest import TEST_PASSWORD


def main():
    with SessionLocal() as db:
        subscription = dict(db.execute(select(Subscription.__table__).limit(1)).mappings().one())
        invoice = dict(db.execute(select(Invoice.__table__).limit(1)).mappings().one())
        subscription.pop("id")
        invoice.pop("id")
        for start in range(0, 3000, 300):
            subs = [
                {
                    **subscription,
                    "number": f"PERF-SUB-{i}",
                    "state": SubscriptionState.active,
                    "currency": "INR",
                    "recurring_untaxed": Decimal("100"),
                    "next_invoice_date": date.today(),
                    "expiry_date": date.today() + timedelta(days=365),
                }
                for i in range(start, start + 300)
            ]
            ids = db.execute(Subscription.__table__.insert().returning(Subscription.id), subs).scalars().all()
            invoices = [
                {
                    **invoice,
                    "number": f"PERF-INV-{start+i}",
                    "subscription_id": sid,
                    "customer_id": subscription["customer_id"],
                    "currency": "INR",
                    "state": InvoiceState.confirmed,
                    "invoice_date": date.today(),
                    "due_date": date.today() - timedelta(days=1),
                    "total": Decimal("100"),
                    "amount_due": Decimal("90"),
                    "amount_paid": Decimal("10"),
                }
                for i, sid in enumerate(ids)
            ]
            invoice_ids = (
                db.execute(Invoice.__table__.insert().returning(Invoice.id), invoices).scalars().all()
            )
            db.execute(
                Payment.__table__.insert(),
                [
                    dict(
                        invoice_id=i,
                        customer_id=subscription["customer_id"],
                        method=PaymentMethod.bank_transfer,
                        amount=Decimal("10"),
                        payment_date=date.today(),
                        status=PaymentStatus.completed,
                    )
                    for i in invoice_ids
                ],
            )
        db.commit()
    with TestClient(app) as client:
        login = client.post(
            "/api/auth/login", json={"email": "admin@brightloop.com", "password": TEST_PASSWORD}
        )
        assert login.status_code == 200, login.text
        headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        durations = []
        for query in [
            "currency=INR",
            "currency=INR&invoice_page=200&payment_page=200&subscription_page=200",
            f"currency=INR&customer_id={subscription['customer_id']}&plan_id={subscription['plan_id']}",
        ]:
            start = time.perf_counter()
            response = client.get("/api/reports/finance?" + query, headers=headers)
            elapsed = time.perf_counter() - start
            assert response.status_code == 200, response.text
            data = response.json()
            assert data["active_subscriptions"] >= 3000
            assert data["invoice_count"] >= 3000 and data["payment_count"] >= 3000
            assert len(data["invoices"]) == len(data["payments"]) == len(data["subscriptions"]) == 10
            assert elapsed < 2, f"Finance endpoint took {elapsed:.3f}s with 3000 records per domain"
            durations.append(round(elapsed, 4))
        billing_durations = []
        for page in [1, 200]:
            start = time.perf_counter()
            response = client.get(
                f"/api/billing/preview?run_date={date.today().isoformat()}&page={page}&size=10",
                headers=headers,
            )
            elapsed = time.perf_counter() - start
            assert response.status_code == 200, response.text
            assert response.json()["due_subscriptions"] >= 3000
            assert len(response.json()["items"]) == 10
            assert elapsed < 2, f"Billing preview took {elapsed:.3f}s with 3000 subscriptions"
            billing_durations.append(round(elapsed, 4))
    print(
        json.dumps({"records_per_domain": 3000, "seconds": durations, "billing_seconds": billing_durations})
    )


if __name__ == "__main__":
    main()
