from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Select, cast, func, select
from sqlalchemy.orm import Session

from app.models import Invoice, Payment, Plan, Subscription
from app.models.enums import BillingPeriod, InvoiceState, PaymentStatus, SubscriptionState

BILLED_STATES = (InvoiceState.confirmed, InvoiceState.paid)


class ReportRepository:
    """Aggregates computed in SQL (COUNT/SUM ... GROUP BY), never by looping over rows in Python."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def subscription_counts(self, customer_id: int | None, plan_id: int | None) -> dict[SubscriptionState, int]:
        stmt = select(Subscription.state, func.count()).group_by(Subscription.state)
        stmt = _filter_subscriptions(stmt, customer_id, plan_id)
        return {state: count for state, count in self.db.execute(stmt)}

    def active_recurring_by_period(
        self, customer_id: int | None, plan_id: int | None
    ) -> list[tuple[BillingPeriod, int, Decimal]]:
        stmt = (
            select(Plan.billing_period, Plan.billing_interval, func.sum(Subscription.recurring_untaxed))
            .join(Plan, Plan.id == Subscription.plan_id)
            .where(Subscription.state == SubscriptionState.active)
            .group_by(Plan.billing_period, Plan.billing_interval)
        )
        stmt = _filter_subscriptions(stmt, customer_id, plan_id)
        return [(period, interval, total) for period, interval, total in self.db.execute(stmt)]

    def invoiced_total(
        self, date_from: date | None, date_to: date | None, customer_id: int | None, plan_id: int | None
    ) -> Decimal:
        stmt = select(func.coalesce(func.sum(Invoice.total), 0)).select_from(Invoice).where(
            Invoice.state.in_(BILLED_STATES)
        )
        stmt = _filter_invoices(stmt, date_from, date_to, customer_id, plan_id)
        return self.db.scalar(stmt)

    def outstanding(
        self,
        date_from: date | None,
        date_to: date | None,
        customer_id: int | None,
        plan_id: int | None,
        overdue_before: date | None = None,
    ) -> tuple[Decimal, int]:
        stmt = (
            select(func.coalesce(func.sum(Invoice.amount_due), 0), func.count())
            .select_from(Invoice)
            .where(Invoice.state == InvoiceState.confirmed, Invoice.amount_due > 0)
        )
        if overdue_before:
            stmt = stmt.where(Invoice.due_date < overdue_before)
        stmt = _filter_invoices(stmt, date_from, date_to, customer_id, plan_id)
        amount, count = self.db.execute(stmt).one()
        return amount, count

    def collected_total(
        self, date_from: date | None, date_to: date | None, customer_id: int | None, plan_id: int | None
    ) -> Decimal:
        stmt = select(func.coalesce(func.sum(Payment.amount), 0)).select_from(Payment)
        stmt = _filter_payments(stmt, date_from, date_to, customer_id, plan_id)
        return self.db.scalar(stmt)

    def invoiced_by_month(
        self, date_from: date | None, date_to: date | None, customer_id: int | None, plan_id: int | None
    ) -> dict[date, Decimal]:
        month = cast(func.date_trunc("month", Invoice.invoice_date), Date)
        stmt = (
            select(month, func.sum(Invoice.total))
            .select_from(Invoice)
            .where(Invoice.state.in_(BILLED_STATES))
            .group_by(month)
        )
        stmt = _filter_invoices(stmt, date_from, date_to, customer_id, plan_id)
        return dict(self.db.execute(stmt).tuples().all())

    def collected_by_month(
        self, date_from: date | None, date_to: date | None, customer_id: int | None, plan_id: int | None
    ) -> dict[date, Decimal]:
        month = cast(func.date_trunc("month", Payment.payment_date), Date)
        stmt = select(month, func.sum(Payment.amount)).select_from(Payment).group_by(month)
        stmt = _filter_payments(stmt, date_from, date_to, customer_id, plan_id)
        return dict(self.db.execute(stmt).tuples().all())


def _filter_subscriptions(stmt: Select, customer_id: int | None, plan_id: int | None) -> Select:
    if customer_id:
        stmt = stmt.where(Subscription.customer_id == customer_id)
    if plan_id:
        stmt = stmt.where(Subscription.plan_id == plan_id)
    return stmt


def _filter_invoices(
    stmt: Select, date_from: date | None, date_to: date | None, customer_id: int | None, plan_id: int | None
) -> Select:
    if date_from:
        stmt = stmt.where(Invoice.invoice_date >= date_from)
    if date_to:
        stmt = stmt.where(Invoice.invoice_date <= date_to)
    if customer_id:
        stmt = stmt.where(Invoice.customer_id == customer_id)
    if plan_id:
        stmt = stmt.join(Subscription, Subscription.id == Invoice.subscription_id).where(
            Subscription.plan_id == plan_id
        )
    return stmt


def _filter_payments(
    stmt: Select, date_from: date | None, date_to: date | None, customer_id: int | None, plan_id: int | None
) -> Select:
    stmt = stmt.where(Payment.status == PaymentStatus.completed)
    if date_from:
        stmt = stmt.where(Payment.payment_date >= date_from)
    if date_to:
        stmt = stmt.where(Payment.payment_date <= date_to)
    if customer_id:
        stmt = stmt.where(Payment.customer_id == customer_id)
    if plan_id:
        stmt = (
            stmt.join(Invoice, Invoice.id == Payment.invoice_id)
            .join(Subscription, Subscription.id == Invoice.subscription_id)
            .where(Subscription.plan_id == plan_id)
        )
    return stmt
