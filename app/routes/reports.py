from datetime import date

from fastapi import APIRouter

from app.routes.deps import DbSession, StaffUser
from app.schemas.report import MonthlyRevenue, SummaryReport
from app.services.report import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/summary", response_model=SummaryReport)
def summary(
    _: StaffUser,
    db: DbSession,
    date_from: date | None = None,
    date_to: date | None = None,
    customer_id: int | None = None,
    plan_id: int | None = None,
):
    """Active subscriptions, MRR/ARR, revenue, outstanding and overdue amounts. Filters are optional."""
    return ReportService(db).summary(date_from, date_to, customer_id, plan_id)


@router.get("/revenue-by-month", response_model=list[MonthlyRevenue])
def revenue_by_month(
    _: StaffUser,
    db: DbSession,
    date_from: date | None = None,
    date_to: date | None = None,
    customer_id: int | None = None,
    plan_id: int | None = None,
):
    return ReportService(db).revenue_by_month(date_from, date_to, customer_id, plan_id)
