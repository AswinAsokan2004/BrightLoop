"""Customer self-service. Every query is scoped to the logged-in customer's own records."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.core.exceptions import BadRequestError
from app.models.enums import InvoiceState, SubscriptionState
from app.routes.deps import CustomerUser, DbSession, Paging, PortalCustomerId
from app.schemas.common import Page, to_page
from app.schemas.customer import CustomerRead
from app.schemas.invoice import InvoiceRead, InvoiceSummary
from app.schemas.subscription import StateChangeRequest, SubscriptionRead, SubscriptionSummary
from app.services.customer import CustomerService
from app.services.invoice import InvoiceService
from app.services.subscription import SubscriptionService

router = APIRouter(prefix="/portal", tags=["Customer portal"])

# Customers may pause, resume or close their own subscription; plan rules still apply
CUSTOMER_ALLOWED_STATES = {SubscriptionState.paused, SubscriptionState.active, SubscriptionState.closed}


@router.get("/profile", response_model=CustomerRead)
def profile(customer_id: PortalCustomerId, db: DbSession):
    return CustomerService(db).get(customer_id)


@router.get("/subscriptions", response_model=Page[SubscriptionSummary])
def my_subscriptions(
    customer_id: PortalCustomerId, db: DbSession, paging: Paging, state: SubscriptionState | None = None
):
    items, total = SubscriptionService(db).list(paging, state=state, customer_id=customer_id)
    return to_page(SubscriptionSummary, items, total, paging)


@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionRead)
def my_subscription(subscription_id: int, customer_id: PortalCustomerId, db: DbSession):
    return SubscriptionService(db).get(subscription_id, customer_id)


@router.post("/subscriptions/{subscription_id}/state", response_model=SubscriptionRead)
def change_my_subscription(
    subscription_id: int,
    data: StateChangeRequest,
    user: CustomerUser,
    customer_id: PortalCustomerId,
    db: DbSession,
):
    if data.state not in CUSTOMER_ALLOWED_STATES:
        raise BadRequestError("Customers can only pause, resume or close a subscription")
    service = SubscriptionService(db)
    if data.state == SubscriptionState.active and service.get(subscription_id, customer_id).state != SubscriptionState.paused:
        raise BadRequestError("Only a paused subscription can be resumed")
    return service.change_state(subscription_id, data.state, user, data.reason, customer_id=customer_id)


@router.get("/invoices", response_model=Page[InvoiceSummary])
def my_invoices(
    customer_id: PortalCustomerId,
    db: DbSession,
    paging: Paging,
    state: InvoiceState | None = None,
    outstanding: bool = False,
    subscription_id: int | None = None,
):
    items, total = InvoiceService(db).list(paging, state=state, customer_id=customer_id, outstanding=outstanding, subscription_id=subscription_id)
    return to_page(InvoiceSummary, items, total, paging)


@router.get("/invoices/{invoice_id}", response_model=InvoiceRead)
def my_invoice(invoice_id: int, customer_id: PortalCustomerId, db: DbSession):
    return InvoiceService(db).get(invoice_id, customer_id)


@router.get("/invoices/{invoice_id}/print", response_class=HTMLResponse)
def print_my_invoice(invoice_id: int, customer_id: PortalCustomerId, db: DbSession):
    return InvoiceService(db).render_html(invoice_id, customer_id)
