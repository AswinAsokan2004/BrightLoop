from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, selectinload

from app.models import BillingRun, Invoice, InvoiceLine, NumberSequence, Subscription
from app.models.enums import InvoiceState
from app.repositories.base import BaseRepository

_INVOICE_DETAIL = (
    selectinload(Invoice.lines).selectinload(InvoiceLine.taxes),
    selectinload(Invoice.payments),
    selectinload(Invoice.customer),
)


class SequenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def next_number(self, code: str, prefix: str, year: int) -> str:
        """Gap-free numbering, e.g. INV/2026/00042. The row lock lasts until the transaction ends."""
        stmt = (
            insert(NumberSequence)
            .values(code=code, prefix=prefix, year=year, next_number=2)
            .on_conflict_do_update(
                index_elements=["code", "year"],
                set_={"next_number": NumberSequence.next_number + 1},
            )
            .returning(NumberSequence.prefix, NumberSequence.next_number - 1)
        )
        row_prefix, number = self.db.execute(stmt).one()
        return f"{row_prefix}/{year}/{number:05d}"


class InvoiceRepository(BaseRepository[Invoice]):
    model = Invoice

    def get_detail(self, invoice_id: int, customer_id: int | None = None) -> Invoice | None:
        stmt = select(Invoice).where(Invoice.id == invoice_id).options(*_INVOICE_DETAIL)
        if customer_id is not None:
            stmt = stmt.where(Invoice.customer_id == customer_id)
        return self.db.scalar(stmt)

    def lock(self, invoice_id: int) -> Invoice | None:
        return self.db.scalar(
            select(Invoice)
            .where(Invoice.id == invoice_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def get_by_period(self, subscription_id: int, period_start: date) -> Invoice | None:
        return self.db.scalar(
            select(Invoice).where(
                Invoice.subscription_id == subscription_id, Invoice.period_start == period_start
            )
        )

    def list(
        self,
        *,
        today: date,
        state: InvoiceState | None = None,
        customer_id: int | None = None,
        subscription_id: int | None = None,
        plan_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        overdue: bool = False,
        outstanding: bool = False,
        q: str | None = None,
        page: int,
        size: int,
    ) -> tuple[list[Invoice], int]:
        stmt = select(Invoice).order_by(Invoice.invoice_date.desc(), Invoice.id.desc())
        if state:
            stmt = stmt.where(Invoice.state == state)
        if customer_id:
            stmt = stmt.where(Invoice.customer_id == customer_id)
        if subscription_id:
            stmt = stmt.where(Invoice.subscription_id == subscription_id)
        if plan_id:
            stmt = stmt.join(Subscription, Subscription.id == Invoice.subscription_id).where(
                Subscription.plan_id == plan_id
            )
        if date_from:
            stmt = stmt.where(Invoice.invoice_date >= date_from)
        if date_to:
            stmt = stmt.where(Invoice.invoice_date <= date_to)
        if outstanding or overdue:
            stmt = stmt.where(Invoice.state == InvoiceState.confirmed, Invoice.amount_due > 0)
        if overdue:
            stmt = stmt.where(Invoice.due_date < today)
        if q:
            stmt = stmt.where(Invoice.number.ilike(f"%{q}%"))
        return self.paginate(stmt, page, size)


class BillingRunRepository(BaseRepository[BillingRun]):
    model = BillingRun

    def list(self, *, page: int, size: int) -> tuple[list[BillingRun], int]:
        return self.paginate(select(BillingRun).order_by(BillingRun.id.desc()), page, size)
