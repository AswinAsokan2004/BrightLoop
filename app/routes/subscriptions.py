from datetime import date

from fastapi import APIRouter, status

from app.models.enums import SubscriptionState
from app.routes.deps import DbSession, Paging, StaffUser
from app.schemas.common import Page, to_page
from app.schemas.invoice import InvoiceRead
from app.schemas.subscription import (
    RenewRequest,
    StateChangeRequest,
    SubscriptionCreate,
    SubscriptionFromTemplate,
    SubscriptionRead,
    SubscriptionSummary,
    SubscriptionUpdate,
)
from app.services.billing import BillingService
from app.services.subscription import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("", response_model=Page[SubscriptionSummary])
def list_subscriptions(
    _: StaffUser,
    db: DbSession,
    paging: Paging,
    state: SubscriptionState | None = None,
    customer_id: int | None = None,
    plan_id: int | None = None,
    q: str | None = None,
    expiring_before: date | None = None,
):
    items, total = SubscriptionService(db).list(paging, state, customer_id, plan_id, q, expiring_before)
    return to_page(SubscriptionSummary, items, total, paging)


@router.post("", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
def create_subscription(data: SubscriptionCreate, user: StaffUser, db: DbSession):
    return SubscriptionService(db).create(data, user)


@router.post("/from-template", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
def create_from_template(data: SubscriptionFromTemplate, user: StaffUser, db: DbSession):
    """Build a quotation from a template: plan and lines pre-filled, valid for the template's days."""
    return SubscriptionService(db).create_from_template(data, user)


@router.get("/{subscription_id}", response_model=SubscriptionRead)
def get_subscription(subscription_id: int, _: StaffUser, db: DbSession):
    return SubscriptionService(db).get(subscription_id)


@router.patch("/{subscription_id}", response_model=SubscriptionRead)
def update_subscription(subscription_id: int, data: SubscriptionUpdate, _: StaffUser, db: DbSession):
    return SubscriptionService(db).update(subscription_id, data)


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(subscription_id: int, _: StaffUser, db: DbSession) -> None:
    SubscriptionService(db).delete(subscription_id)


@router.post("/{subscription_id}/state", response_model=SubscriptionRead)
def change_state(subscription_id: int, data: StateChangeRequest, user: StaffUser, db: DbSession):
    """Draft -> Quotation -> Confirmed -> Active -> Closed, plus Paused <-> Active. Every move is logged."""
    return SubscriptionService(db).change_state(subscription_id, data.state, user, data.reason)


@router.post("/{subscription_id}/renew", response_model=SubscriptionRead)
def renew(subscription_id: int, data: RenewRequest, user: StaffUser, db: DbSession):
    return SubscriptionService(db).renew(subscription_id, data.new_expiry_date, user)


@router.post("/{subscription_id}/invoices", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def invoice_now(subscription_id: int, user: StaffUser, db: DbSession):
    """Bill the next period now instead of waiting for the billing run."""
    return BillingService(db).invoice_now(subscription_id, user)
