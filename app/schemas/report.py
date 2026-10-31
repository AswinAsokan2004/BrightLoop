from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import SubscriptionState


class SummaryReport(BaseModel):
    date_from: date | None
    date_to: date | None
    active_subscriptions: int
    subscriptions_by_state: dict[SubscriptionState, int]
    mrr: Decimal
    arr: Decimal
    invoiced_total: Decimal
    revenue_collected: Decimal
    outstanding_amount: Decimal
    outstanding_count: int
    overdue_amount: Decimal
    overdue_count: int


class MonthlyRevenue(BaseModel):
    month: date
    invoiced: Decimal
    collected: Decimal
