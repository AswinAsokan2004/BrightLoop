from fastapi import APIRouter

from app.routes import (
    auth,
    billing,
    catalog,
    customers,
    discounts,
    invoices,
    payments,
    plans,
    portal,
    reports,
    subscriptions,
    users,
)

api_router = APIRouter(prefix="/api")
for module in (
    auth,
    users,
    customers,
    catalog,
    plans,
    subscriptions,
    discounts,
    billing,
    invoices,
    payments,
    reports,
    portal,
):
    api_router.include_router(module.router)
