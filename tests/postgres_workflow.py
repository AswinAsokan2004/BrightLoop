"""Subprocess worker for PostgreSQL checks. Refuses to run against application databases."""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier

from fastapi.testclient import TestClient

assert re.fullmatch(r"brightloop_test_[0-9a-f]{32}", os.environ.get("POSTGRES_DB", "")), "Only a disposable PostgreSQL test database is allowed"

from app.main import app
from tests.conftest import TEST_PASSWORD


def exercise(mode):
    with TestClient(app) as client:
        def call(method, path, body=None, expected=200, token=None):
            response = client.request(method, "/api" + path, json=body, headers={"Authorization": "Bearer " + token} if token else {})
            assert response.status_code == expected, f"{method} {path}: {response.status_code} {response.text}"
            return response.json() if response.content else None

        assert client.get("/health").json() == {"status": "ok"}
        call("GET", "/customers", expected=401)
        tokens = call("POST", "/auth/login", {"email": "admin@brightloop.com", "password": TEST_PASSWORD})
        token = tokens["access_token"]
        assert call("GET", "/auth/me", token=token)["role"] == "admin"

        def admin(method, path, body=None, expected=200):
            return call(method, path, body, expected, token)

        customer_user = call("POST", "/auth/signup", {"name": "Portal Test", "email": "portal@example.com", "password": TEST_PASSWORD}, 201)
        customer_id = customer_user["customer_id"]
        customer_token = call("POST", "/auth/login", {"email": "portal@example.com", "password": TEST_PASSWORD})["access_token"]
        plan = admin("POST", "/plans", {
            "name": "Test schedule", "code": "TEST-SCHEDULE", "price": "100.00",
            "billing_period": "daily" if mode == "concurrency" else "monthly", "start_date": "2020-01-01", "pausable": True,
        }, 201)
        term = admin("POST", "/payment-terms", {"name": "Test immediate", "due_days": 0}, 201)
        tax_ids = []
        if mode == "workflow":
            tax_ids = [admin("POST", "/taxes", {"name": "Test GST", "tax_type": "percent", "rate": "18"}, 201)["id"]]
        product = admin("POST", "/products", {"name": "Test product", "product_type": "service", "sales_price": "100.00", "tax_ids": tax_ids}, 201)
        if mode == "workflow":
            admin("POST", "/discounts", {"name": "Test discount", "discount_type": "percent", "scope": "product", "value": "10.00", "product_ids": [product["id"]], "start_date": "2020-01-01"}, 201)
        start = date.today() - timedelta(days=2) if mode == "concurrency" else date.today()
        subscription = admin("POST", "/subscriptions", {
            "customer_id": customer_id, "plan_id": plan["id"], "payment_term_id": term["id"],
            "start_date": start.isoformat(), "currency": "INR", "lines": [{"product_id": product["id"], "quantity": 1}],
        }, 201)
        for state in ["quotation", "confirmed", "active"]:
            admin("POST", f"/subscriptions/{subscription['id']}/state", {"state": state})
        invoice_path = f"/invoices?subscription_id={subscription['id']}"

        if mode == "concurrency":
            barrier = Barrier(4)

            def bill(_):
                barrier.wait(timeout=10)
                return admin("POST", "/billing/run", {"run_date": date.today().isoformat()})

            with ThreadPoolExecutor(max_workers=4) as pool:
                runs = list(pool.map(bill, range(4)))
            assert all(run["errors_count"] == 0 for run in runs), runs
            for run in runs:
                linked = admin("GET", f"/billing/runs/{run['id']}/invoices")
                assert linked["total"] == run["invoices_created"]
                assert admin("GET", f"/billing/runs/{run['id']}/failures")["total"] == 0
            assert admin("GET", f"/billing/preview?run_date={date.today().isoformat()}")["due_subscriptions"] == 0
            invoices = admin("GET", invoice_path)["items"]
            assert len(invoices) == 3
            assert len({invoice["period_start"] for invoice in invoices}) == 3
            assert admin("POST", "/billing/run", {"run_date": date.today().isoformat()})["invoices_created"] == 0
            invoice = invoices[0]
            admin("POST", f"/invoices/{invoice['id']}/confirm")
            payment_barrier = Barrier(2)

            def pay(_):
                payment_barrier.wait(timeout=10)
                return client.post(f"/api/invoices/{invoice['id']}/payments", headers={"Authorization": "Bearer " + token}, json={"method": "bank_transfer", "amount": "60.00", "payment_date": date.today().isoformat()}).status_code

            with ThreadPoolExecutor(max_workers=2) as pool:
                assert sorted(pool.map(pay, range(2))) == [201, 400]
            detail = admin("GET", f"/invoices/{invoice['id']}")
            assert detail["amount_due"] == "40.00"
            assert len(detail["payments"]) == 1
            return

        admin("POST", f"/subscriptions/{subscription['id']}/invoices", expected=201)
        invoice = admin("GET", invoice_path)["items"][0]
        assert invoice["total"] == "106.20"
        admin("POST", f"/invoices/{invoice['id']}/confirm")
        for amount in ["40.00", "66.20"]:
            admin("POST", f"/invoices/{invoice['id']}/payments", {"method": "bank_transfer", "amount": amount, "payment_date": date.today().isoformat()}, 201)
        detail = admin("GET", f"/invoices/{invoice['id']}")
        assert (detail["state"], detail["amount_due"]) == ("paid", "0.00")
        assert len(detail["payments"]) == 2
        printable = client.get(f"/api/invoices/{invoice['id']}/print", headers={"Authorization": "Bearer " + token})
        assert printable.status_code == 200 and invoice["number"] in printable.text
        assert call("GET", f"/portal/invoices/{invoice['id']}", token=customer_token)["state"] == "paid"
        call("GET", "/customers", expected=403, token=customer_token)
        call("GET", "/portal/invoices/1", expected=404, token=customer_token)  # seeded other customer's invoice
        report = admin("GET", f"/reports/summary?customer_id={customer_id}")
        assert report["revenue_collected"] == "106.20"
        monthly = admin("GET", f"/reports/revenue-by-month?customer_id={customer_id}")
        assert monthly[0]["collected"] == "106.20"
        rotated = call("POST", "/auth/refresh", {"refresh_token": tokens["refresh_token"]})
        call("POST", "/auth/refresh", {"refresh_token": tokens["refresh_token"]}, expected=401)
        call("POST", "/auth/logout", {"refresh_token": rotated["refresh_token"]}, expected=204)
        call("POST", "/auth/refresh", {"refresh_token": rotated["refresh_token"]}, expected=401)


if __name__ == "__main__":
    mode = sys.argv[1]
    assert mode in {"workflow", "concurrency"}
    exercise(mode)
    print(json.dumps({"passed": mode}))
