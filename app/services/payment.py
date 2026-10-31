from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.security import utcnow
from app.models import Payment, User
from app.models.enums import InvoiceState, PaymentMethod, PaymentStatus
from app.repositories.billing import InvoiceRepository
from app.repositories.payment import PaymentRepository
from app.schemas.common import PageParams
from app.schemas.payment import PaymentCreate


class PaymentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.payments = PaymentRepository(db)
        self.invoices = InvoiceRepository(db)

    def record(self, invoice_id: int, data: PaymentCreate, user: User) -> Payment:
        """Record a full or partial payment. The invoice becomes Paid when nothing is left due."""
        invoice = self.invoices.lock(invoice_id)  # serialise concurrent payments on one invoice
        if invoice is None:
            raise NotFoundError("Invoice not found")
        if invoice.state == InvoiceState.draft:
            raise BadRequestError("Confirm the invoice before recording payments")
        if invoice.state == InvoiceState.cancelled:
            raise BadRequestError("Cannot record a payment on a cancelled invoice")
        if invoice.state == InvoiceState.paid:
            raise BadRequestError("This invoice is already fully paid")
        if data.amount > invoice.amount_due:
            raise BadRequestError(f"Amount is more than the outstanding balance of {invoice.amount_due}")

        payment = self.payments.add(
            Payment(
                invoice_id=invoice.id,
                customer_id=invoice.customer_id,
                method=data.method,
                amount=data.amount,
                payment_date=data.payment_date,
                reference=data.reference,
                note=data.note,
                status=PaymentStatus.completed,
                recorded_by=user.id,
            )
        )
        invoice.amount_paid += data.amount
        invoice.amount_due -= data.amount
        if invoice.amount_due == 0:
            invoice.state = InvoiceState.paid
            invoice.paid_at = utcnow()
        self.db.commit()
        return payment

    def list(
        self,
        params: PageParams,
        invoice_id: int | None = None,
        customer_id: int | None = None,
        method: PaymentMethod | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[Payment], int]:
        return self.payments.list(
            invoice_id=invoice_id,
            customer_id=customer_id,
            method=method,
            date_from=date_from,
            date_to=date_to,
            page=params.page,
            size=params.size,
        )
