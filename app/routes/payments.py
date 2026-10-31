from datetime import date

from fastapi import APIRouter

from app.models.enums import PaymentMethod
from app.routes.deps import DbSession, Paging, StaffUser
from app.schemas.common import Page, to_page
from app.schemas.payment import PaymentRead
from app.services.payment import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("", response_model=Page[PaymentRead])
def list_payments(
    _: StaffUser,
    db: DbSession,
    paging: Paging,
    invoice_id: int | None = None,
    customer_id: int | None = None,
    method: PaymentMethod | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    items, total = PaymentService(db).list(paging, invoice_id, customer_id, method, date_from, date_to)
    return to_page(PaymentRead, items, total, paging)
