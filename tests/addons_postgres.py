"""Checks add-on writes versus billing against an isolated PostgreSQL database."""

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
from threading import Barrier
from fastapi.testclient import TestClient
from app.main import app
from tests.conftest import TEST_PASSWORD


def main():
    assert re.fullmatch(r"brightloop_test_[0-9a-f]{32}", os.environ["POSTGRES_DB"])
    with TestClient(app) as client:

        def login(email, password):
            response = client.post("/api/auth/login", json={"email": email, "password": password})
            assert response.status_code == 200, response.text
            return {"Authorization": "Bearer " + response.json()["access_token"]}

        admin = login("admin@brightloop.com", TEST_PASSWORD)
        signup = client.post(
            "/api/auth/signup",
            json={"name": "Add-on Owner", "email": "addon-owner@example.com", "password": TEST_PASSWORD},
        )
        assert signup.status_code == 201, signup.text
        owner = login("addon-owner@example.com", TEST_PASSWORD)
        cid = client.get("/api/portal/profile", headers=owner).json()["id"]

        def call(path, body, headers=admin, method="POST", status=201):
            response = client.request(method, "/api" + path, headers=headers, json=body)
            assert response.status_code == status, response.text
            return response.json()

        plan = call(
            "/plans",
            {
                "name": "Concurrent add-ons",
                "code": "ADDON-PG",
                "price": "100.00",
                "billing_period": "monthly",
                "start_date": "2020-01-01",
            },
        )
        product = call(
            "/products",
            {"name": "Base service", "product_type": "service", "sales_price": "100.00", "tax_ids": []},
        )
        addon = call(
            "/products",
            {"name": "Concurrent storage", "product_type": "addon", "sales_price": "20.00", "tax_ids": []},
        )
        sub = call(
            "/subscriptions",
            {
                "customer_id": cid,
                "plan_id": plan["id"],
                "payment_term_id": 1,
                "start_date": date.today().isoformat(),
                "expiry_date": (date.today() + timedelta(days=365)).isoformat(),
                "lines": [{"product_id": product["id"], "quantity": 1}],
            },
        )
        for state in ["quotation", "confirmed", "active"]:
            call(f"/subscriptions/{sub['id']}/state", {"state": state}, status=200)
        original = call(f"/subscriptions/{sub['id']}/invoices", None)
        base = f"/portal/subscriptions/{sub['id']}"
        choices = [[{"product_id": addon["id"], "quantity": quantity}] for quantity in [1, 2]]
        quotes = [
            call(base + "/addons/preview", {"items": items}, headers=owner, status=200) for items in choices
        ]
        barrier = Barrier(2)

        def apply(index):
            barrier.wait(timeout=10)
            return client.put(
                "/api" + base + "/addons",
                headers=owner,
                json={"items": choices[index], "fingerprint": quotes[index]["fingerprint"]},
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(apply, [0, 1]))
        assert sorted(response.status_code for response in responses) == [200, 409], [
            (r.status_code, r.text) for r in responses
        ]
        workspace = client.get("/api" + base + "/addons", headers=owner).json()
        assert len(workspace["items"]) == 1
        current_quantity = workspace["items"][0]["quantity"]
        assert current_quantity in [1, 2]
        assert client.get("/api" + base + "/addon-history", headers=owner).json()["total"] == 1
        update = [{"product_id": addon["id"], "quantity": 3}]
        quote = call(base + "/addons/preview", {"items": update}, headers=owner, status=200)
        barrier = Barrier(2)

        def bill():
            barrier.wait(timeout=10)
            return client.post(f"/api/subscriptions/{sub['id']}/invoices", headers=admin)

        def change():
            barrier.wait(timeout=10)
            return client.put(
                "/api" + base + "/addons",
                headers=owner,
                json={"items": update, "fingerprint": quote["fingerprint"]},
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            billing = pool.submit(bill)
            changing = pool.submit(change)
            invoice_response = billing.result(timeout=30)
            change_response = changing.result(timeout=30)
        assert invoice_response.status_code == 201, invoice_response.text
        assert change_response.status_code in [200, 409], change_response.text
        expected = Decimal(160 if change_response.status_code == 200 else 100 + 20 * current_quantity)
        assert Decimal(invoice_response.json()["total"]) == expected
        assert client.get(f"/api/invoices/{original['id']}", headers=admin).json()["total"] == "100.00"
        assert client.get("/api" + base + "/addon-history", headers=owner).json()["total"] == (
            2 if change_response.status_code == 200 else 1
        )
        assert client.get("/api" + base + "/addons", headers=owner).json()["items"][0]["quantity"] == (
            3 if change_response.status_code == 200 else current_quantity
        )
    print(json.dumps({"passed": "addons-concurrency"}))


if __name__ == "__main__":
    main()
