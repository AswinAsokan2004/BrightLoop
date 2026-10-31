"""Billing period arithmetic.

Periods are always counted from a fixed anchor date (start date or trial end), so a
subscription that starts on 31 Jan bills on 28/29 Feb, then 31 Mar, not 28 Mar.
"""

from datetime import date

from dateutil.relativedelta import relativedelta

from app.models.enums import BillingPeriod


def add_periods(anchor: date, period: BillingPeriod, count: int) -> date:
    match period:
        case BillingPeriod.daily:
            return anchor + relativedelta(days=count)
        case BillingPeriod.weekly:
            return anchor + relativedelta(weeks=count)
        case BillingPeriod.monthly:
            return anchor + relativedelta(months=count)
        case BillingPeriod.yearly:
            return anchor + relativedelta(years=count)


def _units_between(anchor: date, day: date, period: BillingPeriod) -> int:
    match period:
        case BillingPeriod.daily:
            return (day - anchor).days
        case BillingPeriod.weekly:
            return (day - anchor).days // 7
        case BillingPeriod.monthly:
            return (day.year - anchor.year) * 12 + day.month - anchor.month
        case BillingPeriod.yearly:
            return day.year - anchor.year


def next_period_start(anchor: date, current: date, period: BillingPeriod, interval: int = 1) -> date:
    """First date on the schedule anchor + k * interval periods that falls after `current`."""
    k = max(_units_between(anchor, current, period) // interval, 0)
    while k > 0 and add_periods(anchor, period, k * interval) > current:
        k -= 1
    while add_periods(anchor, period, k * interval) <= current:
        k += 1
    return add_periods(anchor, period, k * interval)


def first_period_on_or_after(anchor: date, day: date, period: BillingPeriod, interval: int = 1) -> date:
    if day <= anchor:
        return anchor
    return next_period_start(anchor, day - relativedelta(days=1), period, interval)
