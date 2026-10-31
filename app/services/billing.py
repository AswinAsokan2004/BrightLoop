"""Billing engine: turns due subscriptions into invoices.

Guarantees
- Nothing billed twice: unique (subscription_id, period_start) on invoices, a row lock per
  subscription (SKIP LOCKED, so parallel runs split the work), and each invoice is created in a
  savepoint. Running the job twice is harmless.
- Nothing skipped: each subscription loops until next_invoice_date is past the run date, so a
  run after three days of downtime creates all three missed invoices.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.security import utcnow
from app.models import (
    BillingRun,
    DiscountUsage,
    Invoice,
    InvoiceLine,
    InvoiceLineTax,
    Subscription,
    SubscriptionLine,
    SubscriptionStateLog,
    User,
)
from app.models.enums import BillingRunStatus, InvoiceState, SubscriptionState
from app.repositories.billing import BillingRunRepository, InvoiceRepository, SequenceRepository
from app.repositories.discount import DiscountRepository
from app.repositories.subscription import SubscriptionRepository
from app.schemas.common import PageParams
from app.services.periods import next_period_start
from app.services.pricing import LineInput, discount_rule, price_lines, tax_rule

logger = logging.getLogger(__name__)


class BillingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.subscriptions = SubscriptionRepository(db)
        self.invoices = InvoiceRepository(db)
        self.discounts = DiscountRepository(db)
        self.sequences = SequenceRepository(db)
        self.runs = BillingRunRepository(db)

    # --- Billing runs --------------------------------------------------------

    def run(self, run_date: date | None = None, user_id: int | None = None) -> BillingRun:
        run_date = run_date or date.today()
        run = self.runs.add(BillingRun(run_date=run_date, status=BillingRunStatus.running))
        self.db.commit()
        run_id = run.id

        processed = created = 0
        errors: list[str] = []
        for subscription_id in self.subscriptions.due_ids(run_date):
            try:
                created += self._bill_subscription(subscription_id, run_date, run_id, user_id)
                self.db.commit()  # one transaction per subscription
                processed += 1
            except Exception as exc:  # one bad subscription must not stop the whole run
                self.db.rollback()
                logger.exception("Billing failed for subscription %s", subscription_id)
                errors.append(f"Subscription {subscription_id}: {exc}")
            self.db.expunge_all()  # keep memory flat over thousands of subscriptions

        self._close_expired(run_date, user_id)

        run = self.runs.get(run_id)
        run.status = BillingRunStatus.failed if errors and not processed else BillingRunStatus.completed
        run.subscriptions_processed = processed
        run.invoices_created = created
        run.errors_count = len(errors)
        run.error_log = "\n".join(errors) or None
        run.finished_at = utcnow()
        self.db.commit()
        return run

    def list_runs(self, params: PageParams) -> tuple[list[BillingRun], int]:
        return self.runs.list(page=params.page, size=params.size)

    def get_run(self, run_id: int) -> BillingRun:
        run = self.runs.get(run_id)
        if run is None:
            raise NotFoundError("Billing run not found")
        return run

    def invoice_now(self, subscription_id: int, user: User) -> Invoice:
        """Bill the subscription's next period immediately, without waiting for billing day."""
        subscription = self.subscriptions.lock(subscription_id)
        if subscription is None:
            raise NotFoundError("Subscription not found")
        if subscription.state != SubscriptionState.active:
            raise BadRequestError("Only active subscriptions can be invoiced")
        if subscription.next_invoice_date is None:
            raise BadRequestError("Nothing left to bill: the subscription is past its expiry date")

        period_start = subscription.next_invoice_date
        invoice = self._bill_next_period(subscription, None, user.id)
        self.db.commit()
        if invoice is None:
            raise ConflictError(f"The period starting {period_start} was already invoiced or is past expiry")
        return self.invoices.get_detail(invoice.id)

    # --- Internals -----------------------------------------------------------

    def _bill_subscription(self, subscription_id: int, run_date: date, run_id: int, user_id: int | None) -> int:
        subscription = self.subscriptions.lock(subscription_id, skip_locked=True)
        if subscription is None or subscription.state != SubscriptionState.active:
            return 0  # another worker has it, or it changed state since we listed it

        created = 0
        while subscription.next_invoice_date is not None and subscription.next_invoice_date <= run_date:
            if self._bill_next_period(subscription, run_id, user_id) is not None:
                created += 1
        return created

    def _bill_next_period(self, subscription: Subscription, run_id: int | None, user_id: int | None) -> Invoice | None:
        """Invoice the period starting at next_invoice_date, then advance it by one period."""
        period_start = subscription.next_invoice_date
        if subscription.expiry_date and period_start > subscription.expiry_date:
            subscription.next_invoice_date = None  # contract over; renew() restarts billing
            return None

        plan = subscription.plan
        next_start = next_period_start(
            subscription.billing_anchor, period_start, plan.billing_period, plan.billing_interval
        )
        period_end = next_start - timedelta(days=1)
        if subscription.expiry_date:
            period_end = min(period_end, subscription.expiry_date)

        invoice = None
        if self.invoices.get_by_period(subscription.id, period_start) is None:
            try:
                with self.db.begin_nested():
                    invoice = self._create_invoice(subscription, period_start, period_end, run_id, user_id)
            except IntegrityError:
                invoice = None  # a concurrent run billed this period first

        subscription.last_invoiced_date = period_start
        subscription.next_invoice_date = next_start
        return invoice

    def _create_invoice(
        self,
        subscription: Subscription,
        period_start: date,
        period_end: date,
        run_id: int | None,
        user_id: int | None,
    ) -> Invoice:
        lines = [
            LineInput(line.product_id, line.quantity, line.unit_price, tuple(tax_rule(t) for t in line.taxes))
            for line in subscription.lines
        ]

        # Discounts apply on their own while valid, and stop when expired or used up
        rules = [discount_rule(d) for d in self.discounts.find_applicable(period_start)]
        preview = price_lines(lines, rules)
        claimed = [r for r in rules if r.id in preview.discounts and self.discounts.claim(r.id)]
        result = price_lines(lines, claimed)
        for rule in claimed:
            if rule.id not in result.discounts:
                self.discounts.release(rule.id)

        invoice = Invoice(
            number=self.sequences.next_number("invoice", "INV", period_start.year),
            subscription_id=subscription.id,
            customer_id=subscription.customer_id,
            billing_run_id=run_id,
            state=InvoiceState.draft,
            currency=subscription.currency,
            invoice_date=period_start,
            due_date=period_start + timedelta(days=subscription.payment_term.due_days),
            period_start=period_start,
            period_end=period_end,
            subtotal=result.subtotal,
            discount_total=result.discount_total,
            untaxed_total=result.untaxed_total,
            tax_total=result.tax_total,
            total=result.total,
            amount_paid=Decimal("0"),
            amount_due=result.total,
            created_by=user_id,
            # Snapshot prices, names and tax rates: later catalog changes never alter this invoice
            lines=[
                InvoiceLine(
                    product_id=line.product_id,
                    variant_id=line.variant_id,
                    description=_describe(line, period_start, period_end),
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    discount_amount=priced.discount,
                    untaxed_amount=priced.untaxed,
                    tax_amount=priced.tax,
                    total_amount=priced.total,
                    taxes=[
                        InvoiceLineTax(tax_id=t.tax.id, tax_name=t.tax.name, rate=t.tax.rate, amount=t.amount)
                        for t in priced.taxes
                    ],
                )
                for line, priced in zip(subscription.lines, result.lines)
            ],
        )
        self.invoices.add(invoice)

        for discount_id, amount in result.discounts.items():
            self.discounts.add_usage(
                DiscountUsage(
                    discount_id=discount_id,
                    subscription_id=subscription.id,
                    invoice_id=invoice.id,
                    amount=amount,
                )
            )
        self.db.flush()
        return invoice

    def _close_expired(self, run_date: date, user_id: int | None) -> None:
        """Plans with auto_close end their subscriptions on their own after the expiry date."""
        for subscription_id in self.subscriptions.expired_auto_close_ids(run_date):
            subscription = self.subscriptions.lock(subscription_id, skip_locked=True)
            if subscription is None:
                continue
            subscription.state_logs.append(
                SubscriptionStateLog(
                    from_state=subscription.state,
                    to_state=SubscriptionState.closed,
                    changed_by=user_id,
                    reason="Closed automatically at expiry",
                )
            )
            subscription.state = SubscriptionState.closed
            subscription.closed_at = utcnow()
            subscription.close_reason = "Closed automatically at expiry"
            subscription.next_invoice_date = None
        self.db.commit()


def _describe(line: SubscriptionLine, period_start: date, period_end: date) -> str:
    base = line.description or f"Product {line.product_id}"
    return f"{base} ({period_start:%d %b %Y} - {period_end:%d %b %Y})"[:255]
