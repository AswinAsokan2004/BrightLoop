from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.models import Payment
from app.models.enums import PaymentMethod
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    model = Payment

    def list(
        self,
        *,
        invoice_id: int | None,
        customer_id: int | None,
        method: PaymentMethod | None,
        date_from: date | None,
        date_to: date | None,
        page: int,
        size: int,
    ) -> tuple[list[Payment], int]:
        stmt = select(Payment).order_by(Payment.payment_date.desc(), Payment.id.desc())
        if invoice_id:
            stmt = stmt.where(Payment.invoice_id == invoice_id)
        if customer_id:
            stmt = stmt.where(Payment.customer_id == customer_id)
        if method:
            stmt = stmt.where(Payment.method == method)
        if date_from:
            stmt = stmt.where(Payment.payment_date >= date_from)
        if date_to:
            stmt = stmt.where(Payment.payment_date <= date_to)
        return self.paginate(stmt, page, size)
