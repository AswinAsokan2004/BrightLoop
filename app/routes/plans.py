from fastapi import APIRouter, status

from app.models.enums import BillingPeriod
from app.routes.deps import AdminUser, DbSession, Paging, StaffUser
from app.schemas.common import Page, to_page
from app.schemas.plan import (
    PlanCreate,
    PlanRead,
    PlanUpdate,
    QuotationTemplateCreate,
    QuotationTemplateRead,
    QuotationTemplateUpdate,
)
from app.services.plan import PlanService

router = APIRouter(tags=["Plans & quotation templates"])

# --- Plans ---------------------------------------------------------------------


@router.get("/plans", response_model=Page[PlanRead])
def list_plans(
    _: StaffUser,
    db: DbSession,
    paging: Paging,
    active: bool | None = None,
    billing_period: BillingPeriod | None = None,
):
    items, total = PlanService(db).list_plans(active, billing_period, paging)
    return to_page(PlanRead, items, total, paging)


@router.post("/plans", response_model=PlanRead, status_code=status.HTTP_201_CREATED)
def create_plan(data: PlanCreate, admin: AdminUser, db: DbSession):
    return PlanService(db).create_plan(data, admin)


@router.get("/plans/{plan_id}", response_model=PlanRead)
def get_plan(plan_id: int, _: StaffUser, db: DbSession):
    return PlanService(db).get_plan(plan_id)


@router.patch("/plans/{plan_id}", response_model=PlanRead)
def update_plan(plan_id: int, data: PlanUpdate, _: AdminUser, db: DbSession):
    return PlanService(db).update_plan(plan_id, data)


# --- Quotation templates -------------------------------------------------------


@router.get("/quotation-templates", response_model=Page[QuotationTemplateRead])
def list_templates(_: StaffUser, db: DbSession, paging: Paging, active: bool | None = None):
    items, total = PlanService(db).list_templates(active, paging)
    return to_page(QuotationTemplateRead, items, total, paging)


@router.post("/quotation-templates", response_model=QuotationTemplateRead, status_code=status.HTTP_201_CREATED)
def create_template(data: QuotationTemplateCreate, user: StaffUser, db: DbSession):
    return PlanService(db).create_template(data, user)


@router.get("/quotation-templates/{template_id}", response_model=QuotationTemplateRead)
def get_template(template_id: int, _: StaffUser, db: DbSession):
    return PlanService(db).get_template(template_id)


@router.patch("/quotation-templates/{template_id}", response_model=QuotationTemplateRead)
def update_template(template_id: int, data: QuotationTemplateUpdate, _: StaffUser, db: DbSession):
    return PlanService(db).update_template(template_id, data)


@router.delete("/quotation-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: int, _: AdminUser, db: DbSession) -> None:
    PlanService(db).delete_template(template_id)
