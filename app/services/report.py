from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.enums import BillingPeriod, SubscriptionState
from app.repositories.report import ReportRepository
from app.schemas.report import MonthlyRevenue, SummaryReport
from app.services.pricing import money

# How many times a period fits in one month, for MRR
MONTHLY_FACTOR = {
    BillingPeriod.daily: Decimal(365) / 12,
    BillingPeriod.weekly: Decimal(52) / 12,
    BillingPeriod.monthly: Decimal(1),
    BillingPeriod.yearly: Decimal(1) / 12,
}


class ReportService:
    def __init__(self, db: Session) -> None:
        self.reports = ReportRepository(db)

    def summary(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
        customer_id: int | None = None,
        plan_id: int | None = None,
    ) -> SummaryReport:
        """One place for the finance lead: active subscriptions, revenue, outstanding and overdue."""
        counts = self.reports.subscription_counts(customer_id, plan_id)
        mrr = money(
            sum(
                (total * MONTHLY_FACTOR[period] / interval
                 for period, interval, total in self.reports.active_recurring_by_period(customer_id, plan_id)),
                Decimal(0),
            )
        )
        outstanding_amount, outstanding_count = self.reports.outstanding(date_from, date_to, customer_id, plan_id)
        overdue_amount, overdue_count = self.reports.outstanding(
            date_from, date_to, customer_id, plan_id, overdue_before=date.today()
        )

        return SummaryReport(
            date_from=date_from,
            date_to=date_to,
            active_subscriptions=counts.get(SubscriptionState.active, 0),
            subscriptions_by_state={state: counts.get(state, 0) for state in SubscriptionState},
            mrr=mrr,
            arr=mrr * 12,
            invoiced_total=self.reports.invoiced_total(date_from, date_to, customer_id, plan_id),
            revenue_collected=self.reports.collected_total(date_from, date_to, customer_id, plan_id),
            outstanding_amount=outstanding_amount,
            outstanding_count=outstanding_count,
            overdue_amount=overdue_amount,
            overdue_count=overdue_count,
        )

    def revenue_by_month(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
        customer_id: int | None = None,
        plan_id: int | None = None,
    ) -> list[MonthlyRevenue]:
        invoiced = self.reports.invoiced_by_month(date_from, date_to, customer_id, plan_id)
        collected = self.reports.collected_by_month(date_from, date_to, customer_id, plan_id)
        return [
            MonthlyRevenue(
                month=month,
                invoiced=invoiced.get(month, Decimal("0.00")),
                collected=collected.get(month, Decimal("0.00")),
            )
            for month in sorted(invoiced.keys() | collected.keys())
        ]
