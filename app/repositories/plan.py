from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Plan, QuotationTemplate
from app.models.enums import BillingPeriod
from app.repositories.base import BaseRepository


class PlanRepository(BaseRepository[Plan]):
    model = Plan

    def list(
        self,
        *,
        active: bool | None,
        billing_period: BillingPeriod | None,
        page: int,
        size: int,
    ) -> tuple[list[Plan], int]:
        stmt = select(Plan).order_by(Plan.name, Plan.id)
        if active is not None:
            stmt = stmt.where(Plan.active == active)
        if billing_period:
            stmt = stmt.where(Plan.billing_period == billing_period)
        return self.paginate(stmt, page, size)


class QuotationTemplateRepository(BaseRepository[QuotationTemplate]):
    model = QuotationTemplate

    def get_detail(self, template_id: int) -> QuotationTemplate | None:
        return self.db.scalar(
            select(QuotationTemplate)
            .where(QuotationTemplate.id == template_id)
            .options(selectinload(QuotationTemplate.lines))
        )

    def list(self, *, active: bool | None, page: int, size: int) -> tuple[list[QuotationTemplate], int]:
        stmt = select(QuotationTemplate).order_by(QuotationTemplate.name, QuotationTemplate.id)
        if active is not None:
            stmt = stmt.where(QuotationTemplate.active == active)
        return self.paginate(stmt, page, size, options=(selectinload(QuotationTemplate.lines),))
