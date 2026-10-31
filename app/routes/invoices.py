from datetime import date

from fastapi import APIRouter, BackgroundTasks, status
from fastapi.responses import HTMLResponse

from app.core.email import send_email
from app.models.enums import InvoiceState
from app.routes.deps import DbSession, Paging, StaffUser
from app.schemas.common import Page, to_page
from app.schemas.invoice import InvoiceRead, InvoiceSummary
from app.schemas.payment import PaymentCreate, PaymentRead
from app.services.invoice import InvoiceService
from app.services.payment import PaymentService

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get("", response_model=Page[InvoiceSummary])
def list_invoices(
    _: StaffUser,
    db: DbSession,
    paging: Paging,
    state: InvoiceState | None = None,
    customer_id: int | None = None,
    subscription_id: int | None = None,
    plan_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    overdue: bool = False,
    outstanding: bool = False,
    q: str | None = None,
):
    """`outstanding=true`: confirmed and not fully paid. `overdue=true`: outstanding and past the due date."""
    items, total = InvoiceService(db).list(
        paging, state, customer_id, subscription_id, plan_id, date_from, date_to, overdue, outstanding, q
    )
    return to_page(InvoiceSummary, items, total, paging)


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(invoice_id: int, _: StaffUser, db: DbSession):
    return InvoiceService(db).get(invoice_id)


@router.post("/{invoice_id}/confirm", response_model=InvoiceRead)
def confirm_invoice(invoice_id: int, _: StaffUser, db: DbSession):
    return InvoiceService(db).confirm(invoice_id)


@router.post("/{invoice_id}/cancel", response_model=InvoiceRead)
def cancel_invoice(invoice_id: int, _: StaffUser, db: DbSession):
    return InvoiceService(db).cancel(invoice_id)


@router.post("/{invoice_id}/send", response_model=InvoiceRead)
def send_invoice(invoice_id: int, _: StaffUser, db: DbSession, background: BackgroundTasks):
    invoice, email = InvoiceService(db).send(invoice_id)
    background.add_task(send_email, email)
    return invoice


@router.get("/{invoice_id}/print", response_class=HTMLResponse)
def print_invoice(invoice_id: int, _: StaffUser, db: DbSession):
    return InvoiceService(db).render_html(invoice_id)


@router.post("/{invoice_id}/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def record_payment(invoice_id: int, data: PaymentCreate, user: StaffUser, db: DbSession):
    """Full or partial payment. The invoice moves to Paid once nothing is left due."""
    return PaymentService(db).record(invoice_id, data, user)
