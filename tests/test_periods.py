from datetime import date

from app.models.enums import BillingPeriod
from app.services.periods import first_period_on_or_after, next_period_start

M, Y, W, D = BillingPeriod.monthly, BillingPeriod.yearly, BillingPeriod.weekly, BillingPeriod.daily


def test_month_end_anchor_does_not_drift():
    anchor = date(2026, 1, 31)
    feb = next_period_start(anchor, anchor, M)
    assert feb == date(2026, 2, 28)
    assert next_period_start(anchor, feb, M) == date(2026, 3, 31)


def test_leap_year():
    assert next_period_start(date(2028, 1, 31), date(2028, 1, 31), M) == date(2028, 2, 29)
    assert next_period_start(date(2028, 2, 29), date(2028, 2, 29), Y) == date(2029, 2, 28)


def test_interval_quarterly():
    anchor = date(2026, 1, 15)
    assert next_period_start(anchor, anchor, M, interval=3) == date(2026, 4, 15)
    assert next_period_start(anchor, date(2026, 4, 15), M, interval=3) == date(2026, 7, 15)


def test_weekly_and_daily():
    anchor = date(2026, 10, 1)
    assert next_period_start(anchor, anchor, W) == date(2026, 10, 8)
    assert next_period_start(anchor, date(2026, 10, 5), D) == date(2026, 10, 6)


def test_catch_up_from_any_day_in_a_period():
    anchor = date(2026, 1, 10)
    assert next_period_start(anchor, date(2026, 5, 20), M) == date(2026, 6, 10)


def test_first_period_on_or_after():
    anchor = date(2026, 1, 10)
    assert first_period_on_or_after(anchor, date(2026, 3, 10), M) == date(2026, 3, 10)
    assert first_period_on_or_after(anchor, date(2026, 3, 11), M) == date(2026, 4, 10)
    assert first_period_on_or_after(anchor, date(2025, 12, 1), M) == anchor


def test_preview_period_counts_match_worker_schedule_boundaries():
    from app.services.periods import count_period_starts

    cases = [
        (date(2026, 1, 31), date(2026, 1, 31), date(2026, 3, 31), M, 1, 3),
        (date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 30), M, 1, 1),
        (date(2028, 2, 29), date(2028, 2, 29), date(2030, 2, 28), Y, 1, 3),
        (date(2026, 1, 15), date(2026, 1, 15), date(2026, 7, 15), M, 3, 3),
        (date(2026, 1, 1), date(2026, 1, 1), date(2026, 1, 14), W, 2, 1),
        (date(2026, 1, 1), date(2026, 1, 1), date(2026, 1, 3), D, 1, 3),
        (date(2026, 1, 1), date(2026, 1, 4), date(2026, 1, 3), D, 1, 0),
    ]
    for anchor, current, through, period, interval, expected in cases:
        assert count_period_starts(anchor, current, through, period, interval) == expected
