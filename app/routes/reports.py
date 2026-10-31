from datetime import date
from typing import Literal

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from app.models import Customer, Plan
from app.schemas.finance import FinanceReport
from app.services.finance import FinanceService

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


@router.get("/finance", response_model=FinanceReport)
def finance(
    _: StaffUser,
    db: DbSession,
    date_from: date | None = None,
    date_to: date | None = None,
    customer_id: int | None = Query(None, ge=1),
    plan_id: int | None = Query(None, ge=1),
    currency: str | None = Query(None, pattern=r"^[A-Z]{3}$"),
    invoice_view: Literal["all", "billed", "outstanding", "overdue"] = "overdue",
    invoice_page: int = Query(1, ge=1),
    payment_page: int = Query(1, ge=1),
    subscription_page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
):
    return FinanceService(db).report(
        date_from,
        date_to,
        customer_id,
        plan_id,
        currency,
        invoice_view,
        invoice_page,
        payment_page,
        subscription_page,
        size,
    )


@router.get("/options")
def finance_options(
    _: StaffUser,
    db: DbSession,
    kind: Literal["customer", "plan"],
    q: str = Query("", max_length=150),
    page: int = Query(1, ge=1),
):
    model = Customer if kind == "customer" else Plan
    stmt = select(model.id, model.name).where(func.lower(model.name).contains(q.lower(), autoescape=True))
    rows = db.execute(stmt.order_by(model.name, model.id).limit(21).offset((page - 1) * 20)).mappings().all()
    return {"items": [dict(row) for row in rows[:20]], "has_more": len(rows) > 20}
