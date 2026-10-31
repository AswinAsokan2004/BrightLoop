from datetime import date
from typing import Literal
from app.schemas.billing_operations import BillingFailure, BillingPreview, BillingRunInvoice
from app.services.billing_operations import BillingOperationsService

from fastapi import APIRouter

from app.routes.deps import DbSession, Paging, StaffUser
from app.schemas.common import Page, to_page
from app.schemas.invoice import BillingRunRead, BillingRunRequest
from app.services.billing import BillingService

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.post("/run", response_model=BillingRunRead)
def run_billing(data: BillingRunRequest, user: StaffUser, db: DbSession):
    """Invoice every active subscription that is due. Safe to run more than once a day."""
    return BillingService(db).run(data.run_date, user.id)


@router.get("/runs", response_model=Page[BillingRunRead])
def list_runs(_: StaffUser, db: DbSession, paging: Paging):
    items, total = BillingService(db).list_runs(paging)
    return to_page(BillingRunRead, items, total, paging)


@router.get("/runs/{run_id}", response_model=BillingRunRead)
def get_run(run_id: int, _: StaffUser, db: DbSession):
    return BillingService(db).get_run(run_id)


@router.get("/preview", response_model=BillingPreview)
def preview_billing(
    _: StaffUser, db: DbSession, paging: Paging, run_date: date, kind: Literal["due", "closing"] = "due"
):
    """Read-only candidates; the worker rechecks state and period uniqueness when billing."""
    return BillingOperationsService(db).preview(run_date, kind, paging)


@router.get("/runs/{run_id}/invoices", response_model=Page[BillingRunInvoice])
def run_invoices(run_id: int, _: StaffUser, db: DbSession, paging: Paging):
    return BillingOperationsService(db).invoices(run_id, paging)


@router.get("/runs/{run_id}/failures", response_model=Page[BillingFailure])
def run_failures(run_id: int, _: StaffUser, db: DbSession, paging: Paging):
    return BillingOperationsService(db).failures(run_id, paging)
