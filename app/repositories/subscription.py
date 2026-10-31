from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Plan, Subscription, SubscriptionLine
from app.models.enums import SubscriptionState
from app.repositories.base import BaseRepository

_DETAIL = (
    selectinload(Subscription.lines).selectinload(SubscriptionLine.taxes),
    selectinload(Subscription.state_logs),
    selectinload(Subscription.plan),
)


class SubscriptionRepository(BaseRepository[Subscription]):
    model = Subscription

    def get_detail(self, subscription_id: int, customer_id: int | None = None) -> Subscription | None:
        stmt = select(Subscription).where(Subscription.id == subscription_id).options(*_DETAIL)
        if customer_id is not None:
            stmt = stmt.where(Subscription.customer_id == customer_id)
        return self.db.scalar(stmt)

    def lock(self, subscription_id: int, *, skip_locked: bool = False) -> Subscription | None:
        """SELECT ... FOR UPDATE, so two billing workers never process the same subscription."""
        return self.db.scalar(
            select(Subscription)
            .where(Subscription.id == subscription_id)
            .with_for_update(skip_locked=skip_locked)
            .options(*_DETAIL, selectinload(Subscription.payment_term))
            .execution_options(populate_existing=True)
        )

    def list(
        self,
        *,
        state: SubscriptionState | None,
        customer_id: int | None,
        plan_id: int | None,
        q: str | None,
        expiring_before: date | None,
        page: int,
        size: int,
    ) -> tuple[list[Subscription], int]:
        stmt = select(Subscription).order_by(Subscription.id.desc())
        if state:
            stmt = stmt.where(Subscription.state == state)
        if customer_id:
            stmt = stmt.where(Subscription.customer_id == customer_id)
        if plan_id:
            stmt = stmt.where(Subscription.plan_id == plan_id)
        if q:
            stmt = stmt.where(Subscription.number.ilike(f"%{q}%"))
        if expiring_before:
            stmt = stmt.where(Subscription.expiry_date <= expiring_before)
        return self.paginate(stmt, page, size)

    def due_ids(self, run_date: date) -> list[int]:
        """Uses the (state, next_invoice_date) index."""
        return list(
            self.db.scalars(
                select(Subscription.id)
                .where(
                    Subscription.state == SubscriptionState.active,
                    Subscription.next_invoice_date <= run_date,
                )
                .order_by(Subscription.id)
            )
        )

    def expired_auto_close_ids(self, run_date: date) -> list[int]:
        return list(
            self.db.scalars(
                select(Subscription.id)
                .join(Plan, Plan.id == Subscription.plan_id)
                .where(
                    Subscription.state.in_([SubscriptionState.active, SubscriptionState.paused]),
                    Subscription.expiry_date < run_date,
                    Plan.auto_close.is_(True),
                )
                .order_by(Subscription.id)
            )
        )
