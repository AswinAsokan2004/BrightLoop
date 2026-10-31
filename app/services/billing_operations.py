"""Read-only operational context around the existing billing engine."""

import re
from datetime import date, timedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from app.models import Customer, Invoice, Subscription
from app.repositories.subscription import SubscriptionRepository
from app.schemas.billing_operations import (
    BillingFailure,
    BillingPreview,
    BillingPreviewItem,
    BillingRunInvoice,
)
from app.schemas.common import Page, PageParams
from app.schemas.invoice import InvoiceSummary
from app.services.billing import BillingService
from app.services.periods import count_period_starts, next_period_start


class BillingOperationsService:
    def __init__(self, db: Session):
        self.db = db

    def preview(self, run_date: date, kind: str, paging: PageParams) -> BillingPreview:
        due = SubscriptionRepository.due_statement(run_date)
        closing = SubscriptionRepository.auto_close_statement(run_date)
        due_count = self.db.scalar(select(func.count()).select_from(due.subquery()))
        closing_count = self.db.scalar(select(func.count()).select_from(closing.subquery()))
        stmt = due if kind == "due" else closing
        subscriptions = self.db.scalars(
            stmt.options(selectinload(Subscription.customer), selectinload(Subscription.plan))
            .order_by(Subscription.id)
            .limit(paging.size)
            .offset((paging.page - 1) * paging.size)
        ).all()
        items = []
        for sub in subscriptions:
            start = sub.next_invoice_date
            limit = min(run_date, sub.expiry_date) if sub.expiry_date else run_date
            # Paused subscriptions can auto-close but must never be billed by the preview.
            periods = (
                count_period_starts(
                    sub.billing_anchor, start, limit, sub.plan.billing_period, sub.plan.billing_interval
                )
                if start and sub.state.value == "active"
                else 0
            )
            end = (
                next_period_start(
                    sub.billing_anchor, start, sub.plan.billing_period, sub.plan.billing_interval
                )
                - timedelta(days=1)
                if periods
                else None
            )
            if end and sub.expiry_date:
                end = min(end, sub.expiry_date)
            items.append(
                BillingPreviewItem(
                    id=sub.id,
                    number=sub.number,
                    customer_name=sub.customer_name,
                    plan_name=sub.plan.name,
                    state=sub.state,
                    currency=sub.currency,
                    next_invoice_date=start,
                    expiry_date=sub.expiry_date,
                    billing_period=sub.plan.billing_period,
                    billing_interval=sub.plan.billing_interval,
                    first_period_end=end,
                    due_periods=periods,
                )
            )
        return BillingPreview(
            run_date=run_date,
            due_subscriptions=due_count,
            auto_close_subscriptions=closing_count,
            items=items,
            total=due_count if kind == "due" else closing_count,
            page=paging.page,
            size=paging.size,
        )

    def invoices(self, run_id: int, paging: PageParams) -> Page[BillingRunInvoice]:
        BillingService(self.db).get_run(run_id)
        total = self.db.scalar(
            select(func.count()).select_from(Invoice).where(Invoice.billing_run_id == run_id)
        )
        rows = self.db.execute(
            select(Invoice, Customer.name, Subscription.number)
            .join(Customer, Customer.id == Invoice.customer_id)
            .join(Subscription, Subscription.id == Invoice.subscription_id)
            .where(Invoice.billing_run_id == run_id)
            .order_by(Invoice.id)
            .limit(paging.size)
            .offset((paging.page - 1) * paging.size)
        ).all()
        return Page[BillingRunInvoice](
            items=[
                BillingRunInvoice(
                    **InvoiceSummary.model_validate(inv).model_dump(),
                    customer_name=name,
                    subscription_number=number,
                )
                for inv, name, number in rows
            ],
            total=total,
            page=paging.page,
            size=paging.size,
        )

    def failures(self, run_id: int, paging: PageParams) -> Page[BillingFailure]:
        run = BillingService(self.db).get_run(run_id)
        # Match complete entries; exception messages may themselves span several lines.
        entries = re.split(r"(?m)(?=^Subscription \d+: )", run.error_log or "")
        entries = [entry.strip() for entry in entries if entry.strip()]
        page_entries = entries[(paging.page - 1) * paging.size : paging.page * paging.size]
        parsed = []
        for entry in page_entries:
            match = re.match(r"Subscription (\d+): (.*)", entry, re.S)
            parsed.append((int(match[1]), match[2]) if match else (None, entry))
        ids = [sid for sid, _ in parsed if sid is not None]
        context = (
            {
                sid: (number, name)
                for sid, number, name in self.db.execute(
                    select(Subscription.id, Subscription.number, Customer.name)
                    .join(Customer, Customer.id == Subscription.customer_id)
                    .where(Subscription.id.in_(ids))
                )
            }
            if ids
            else {}
        )
        items = [
            BillingFailure(
                subscription_id=sid,
                subscription_number=context.get(sid, (None, None))[0],
                customer_name=context.get(sid, (None, None))[1],
                message=message,
            )
            for sid, message in parsed
        ]
        return Page[BillingFailure](items=items, total=len(entries), page=paging.page, size=paging.size)
