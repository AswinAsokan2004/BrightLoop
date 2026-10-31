from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import update
from app.core.database import get_db
from app.models import Subscription
from tests.test_api_integration import authenticate
from tests.test_subscription_workspace import create_subscription, invoice_subscription


def setup(client):
    admin, _ = authenticate(client)
    customer, _ = authenticate(client, "customer@example.com", "Customer!Pass123")
    sub = create_subscription(client, admin)
    for state in ["quotation", "confirmed", "active"]:
        assert (
            client.post(
                f"/api/subscriptions/{sub['id']}/state", headers=admin, json={"state": state}
            ).status_code
            == 200
        )
    tax = client.post(
        "/api/taxes", headers=admin, json={"name": "Add-on GST", "tax_type": "percent", "rate": "18"}
    ).json()
    addon = client.post(
        "/api/products",
        headers=admin,
        json={
            "name": "Extra storage",
            "product_type": "addon",
            "sales_price": "20.00",
            "cost_price": "3.00",
            "notes": "Internal margin note",
            "tax_ids": [tax["id"]],
        },
    ).json()
    attr = client.post(
        "/api/attributes",
        headers=admin,
        json={"name": "Storage size", "values": [{"value": "Large", "extra_price": "5.00"}]},
    ).json()
    variant = client.post(
        f"/api/products/{addon['id']}/variants",
        headers=admin,
        json={"sku": "STORAGE-L", "name": "Large storage", "attribute_value_ids": [attr["values"][0]["id"]]},
    ).json()
    return admin, customer, sub, addon, variant


def review(client, customer, sub, items):
    response = client.post(
        f"/api/portal/subscriptions/{sub['id']}/addons/preview", headers=customer, json={"items": items}
    )
    assert response.status_code == 200, response.text
    return response.json()


def save(client, customer, sub, items, quote):
    return client.put(
        f"/api/portal/subscriptions/{sub['id']}/addons",
        headers=customer,
        json={"items": items, "fingerprint": quote["fingerprint"]},
    )


def test_addons_preview_apply_future_billing_and_remove_preserves_invoices(client):
    admin, customer, sub, addon, variant = setup(client)
    old_invoice = client.post(f"/api/subscriptions/{sub['id']}/invoices", headers=admin).json()
    original = client.get(f"/api/invoices/{old_invoice['id']}", headers=admin).json()
    base = f"/api/portal/subscriptions/{sub['id']}"
    available = client.get(base + "/addon-options", headers=customer)
    assert available.status_code == 200, available.text
    assert available.json()["total"] == 2
    assert "cost_price" not in available.text and "Internal margin note" not in available.text
    workspace = client.get(base + "/addons", headers=customer).json()
    assert workspace["eligible"] is True and workspace["items"] == []
    selection = [{"product_id": addon["id"], "variant_id": variant["id"], "quantity": 2}]
    quote = review(client, customer, sub, selection)
    assert Decimal(quote["before_total"]) == 100
    assert Decimal(quote["after_total"]) == 159
    assert Decimal(quote["delta"]) == 59
    assert quote["effective_date"] > old_invoice["period_start"]
    assert client.get(base + "/addon-history", headers=customer).json()["total"] == 0
    assert client.get(base + "/addons", headers=customer).json()["items"] == []
    applied = save(client, customer, sub, selection, quote)
    assert applied.status_code == 200, applied.text
    assert len(applied.json()["items"]) == 1
    assert client.get("/api/invoices", headers=admin).json()["total"] == 1
    detail = client.get(base, headers=customer).json()
    assert len([line for line in detail["lines"] if not line["is_addon"]]) == 1
    assert Decimal(detail["recurring_total"]) == 159
    assert client.get(f"/api/invoices/{old_invoice['id']}", headers=admin).json() == original
    future = client.post(f"/api/subscriptions/{sub['id']}/invoices", headers=admin).json()
    assert Decimal(future["total"]) == 159
    assert len(future["lines"]) == 2
    history = client.get(base + "/addon-history", headers=customer).json()
    assert history["total"] == 1 and history["items"][0]["changed_by_user"]["name"] == "Customer Account"
    assert history["items"][0]["before_items"] == []
    assert history["items"][0]["after_items"][0]["unit_price"] == "25.00"
    remove = review(client, customer, sub, [])
    assert Decimal(remove["after_total"]) == 100
    assert save(client, customer, sub, [], remove).status_code == 200
    assert client.get(base + "/addons", headers=customer).json()["items"] == []
    assert client.get(f"/api/invoices/{future['id']}", headers=admin).json()["total"] == "159.00"
    assert client.get(base + "/addon-history?size=1&page=2", headers=customer).json()["total"] == 2


def test_addons_validate_ownership_product_selection_and_customer_prices(client):
    admin, customer, sub, addon, variant = setup(client)
    base = f"/api/portal/subscriptions/{sub['id']}"
    normal = client.post(
        "/api/products",
        headers=admin,
        json={"name": "Protected service", "product_type": "service", "sales_price": "1.00"},
    ).json()
    oneoff = client.post(
        "/api/products",
        headers=admin,
        json={"name": "One-off addon", "product_type": "addon", "is_recurring": False, "sales_price": "1.00"},
    ).json()
    available = client.get(base + "/addon-options", headers=customer).json()
    assert all(row["product_id"] not in [normal["id"], oneoff["id"]] for row in available["items"])
    invalid = [
        [{"product_id": normal["id"], "quantity": 1}],
        [{"product_id": oneoff["id"], "quantity": 1}],
        [{"product_id": addon["id"], "variant_id": 999999, "quantity": 1}],
        [{"product_id": addon["id"], "quantity": 0}],
        [{"product_id": addon["id"], "quantity": 1, "unit_price": "0.00"}],
        [{"product_id": addon["id"], "quantity": 1, "tax_ids": []}],
        [{"product_id": addon["id"], "quantity": 1}] * 2,
        [{"product_id": 1, "quantity": 1}],
    ]
    for items in invalid:
        assert client.post(base + "/addons/preview", headers=customer, json={"items": items}).status_code in [
            400,
            422,
        ]
    foreign = client.post(
        "/api/customers",
        headers=admin,
        json={"name": "Foreign add-on company", "email": "foreign-addons@example.com"},
    ).json()
    other = create_subscription(client, admin, foreign["id"])
    for path in ["addons", "addon-options", "addon-history"]:
        assert (
            client.get(f"/api/portal/subscriptions/{other['id']}/{path}", headers=customer).status_code == 404
        )
        assert client.get(base + "/" + path, headers=admin).status_code == 403
        assert client.get(base + "/" + path).status_code == 401
    assert (
        client.post(
            f"/api/portal/subscriptions/{other['id']}/addons/preview", headers=customer, json={"items": []}
        ).status_code
        == 404
    )
    assert (
        client.put(
            f"/api/portal/subscriptions/{other['id']}/addons",
            headers=customer,
            json={"items": [], "fingerprint": "0" * 64},
        ).status_code
        == 404
    )
    client.patch(f"/api/products/{addon['id']}", headers=admin, json={"active": False})
    assert client.get(base + "/addon-options", headers=customer).json()["total"] == 0
    assert (
        client.post(
            base + "/addons/preview",
            headers=customer,
            json={"items": [{"product_id": addon["id"], "quantity": 1}]},
        ).status_code
        == 400
    )


def test_addon_quote_detects_price_and_billing_changes(client):
    admin, customer, sub, addon, variant = setup(client)
    items = [{"product_id": addon["id"], "quantity": 1}]
    quote = review(client, customer, sub, items)
    client.patch(f"/api/products/{addon['id']}", headers=admin, json={"sales_price": "30.00"})
    assert save(client, customer, sub, items, quote).status_code == 409
    quote = review(client, customer, sub, items)
    client.patch("/api/plans/1", headers=admin, json={"billing_interval": 2})
    assert save(client, customer, sub, items, quote).status_code == 409
    quote = review(client, customer, sub, items)
    assert client.post(f"/api/subscriptions/{sub['id']}/invoices", headers=admin).status_code == 201
    assert save(client, customer, sub, items, quote).status_code == 409
    quote = review(client, customer, sub, items)
    assert save(client, customer, sub, items, quote).status_code == 200
    client.patch(f"/api/products/{addon['id']}", headers=admin, json={"active": False})
    assert (
        client.post(
            f"/api/portal/subscriptions/{sub['id']}/addons/preview",
            headers=customer,
            json={"items": [{"product_id": addon["id"], "quantity": 2}]},
        ).status_code
        == 400
    )
    quote = review(client, customer, sub, [])
    assert save(client, customer, sub, [], quote).status_code == 200  # inactive items can still be removed
    assert save(client, customer, sub, [], quote).status_code == 400  # duplicate submission has no changes


def test_addons_block_paused_expired_and_exhausted_contracts(client):
    admin, customer, sub, addon, variant = setup(client)
    base = f"/api/portal/subscriptions/{sub['id']}"
    items = [{"product_id": addon["id"], "quantity": 1}]
    client.post(f"/api/subscriptions/{sub['id']}/state", headers=admin, json={"state": "paused"})
    assert client.get(base + "/addons", headers=customer).json()["eligible"] is False
    assert client.post(base + "/addons/preview", headers=customer, json={"items": items}).status_code == 400
    get_session = client.app.dependency_overrides[get_db]
    with next(get_session()) as db:
        db.execute(
            update(Subscription)
            .where(Subscription.id == sub["id"])
            .values(state="active", expiry_date=date.today() - timedelta(days=1))
        )
        db.commit()
    assert client.get(base + "/addons", headers=customer).json()["eligible"] is False
    with next(get_session()) as db:
        db.execute(
            update(Subscription)
            .where(Subscription.id == sub["id"])
            .values(expiry_date=date.today() + timedelta(days=90), next_invoice_date=None)
        )
        db.commit()
    assert client.get(base + "/addons", headers=customer).json()["eligible"] is False


def test_addon_quantities_keep_stored_prices_and_protect_plan_minimum(client):
    admin, customer, sub, addon, variant = setup(client)
    items = [{"product_id": addon["id"], "quantity": 1}]
    assert save(client, customer, sub, items, review(client, customer, sub, items)).status_code == 200
    client.patch(f"/api/products/{addon['id']}", headers=admin, json={"sales_price": "99.00"})
    changed = [{"product_id": addon["id"], "quantity": 2}]
    quote = review(client, customer, sub, changed)
    assert quote["after_items"][0]["unit_price"] == "20.00"
    assert Decimal(quote["after_total"]) == Decimal("147.20")
    assert save(client, customer, sub, changed, quote).status_code == 200
    client.patch("/api/plans/1", headers=admin, json={"min_quantity": 3})
    response = client.post(
        f"/api/portal/subscriptions/{sub['id']}/addons/preview", headers=customer, json={"items": []}
    )
    assert response.status_code == 400 and "minimum total quantity" in response.text
    assert (
        len(client.get(f"/api/portal/subscriptions/{sub['id']}/addons", headers=customer).json()["items"])
        == 1
    )


def test_addon_offers_are_paginated_and_do_not_duplicate_base_contract_items(client):
    from app.models import Product

    admin, customer, sub, addon, variant = setup(client)
    protected = create_subscription(client, admin, lines=[{"product_id": addon["id"], "quantity": 1}])
    for state in ["quotation", "confirmed", "active"]:
        assert (
            client.post(
                f"/api/subscriptions/{protected['id']}/state", headers=admin, json={"state": state}
            ).status_code
            == 200
        )
    base = f"/api/portal/subscriptions/{protected['id']}"
    options = client.get(base + "/addon-options", headers=customer).json()
    assert options["total"] == 1 and options["items"][0]["variant_id"] == variant["id"]
    assert (
        client.post(
            base + "/addons/preview",
            headers=customer,
            json={"items": [{"product_id": addon["id"], "quantity": 1}]},
        ).status_code
        == 400
    )
    get_session = client.app.dependency_overrides[get_db]
    with next(get_session()) as db:
        db.add_all(
            [
                Product(
                    name=f"Paged add-on {i:02d}",
                    product_type="addon",
                    sales_price=Decimal("5.00"),
                    cost_price=Decimal("1.00"),
                )
                for i in range(12)
            ]
        )
        db.commit()
    path = f"/api/portal/subscriptions/{sub['id']}/addon-options?q=Paged%20add-on&size=10"
    first = client.get(path, headers=customer).json()
    second = client.get(path + "&page=2", headers=customer).json()
    assert first["total"] == second["total"] == 12
    assert len(first["items"]) == 10 and len(second["items"]) == 2
    assert {row["product_id"] for row in first["items"]}.isdisjoint(
        row["product_id"] for row in second["items"]
    )
    assert client.get(path.replace("Paged%20add-on", "%25"), headers=customer).json()["items"] == []
