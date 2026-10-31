from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import Plan, QuotationTemplate, QuotationTemplateLine, User
from app.models.enums import BillingPeriod
from app.repositories.plan import PlanRepository, QuotationTemplateRepository
from app.schemas.common import PageParams
from app.schemas.plan import (
    PlanCreate,
    PlanUpdate,
    QuotationTemplateCreate,
    QuotationTemplateUpdate,
    TemplateLineIn,
)
from app.services.catalog import CatalogService
from app.services.common import apply_updates


class PlanService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.plans = PlanRepository(db)
        self.templates = QuotationTemplateRepository(db)
        self.catalog = CatalogService(db)

    # --- Plans ---------------------------------------------------------------

    def list_plans(
        self, active: bool | None, billing_period: BillingPeriod | None, params: PageParams
    ) -> tuple[list[Plan], int]:
        return self.plans.list(active=active, billing_period=billing_period, page=params.page, size=params.size)

    def get_plan(self, plan_id: int) -> Plan:
        plan = self.plans.get(plan_id)
        if plan is None:
            raise NotFoundError("Plan not found")
        return plan

    def create_plan(self, data: PlanCreate, user: User) -> Plan:
        plan = self.plans.add(Plan(**data.model_dump(), created_by=user.id))
        self.db.commit()
        return plan

    def update_plan(self, plan_id: int, data: PlanUpdate) -> Plan:
        plan = self.get_plan(plan_id)
        apply_updates(plan, data)
        if plan.end_date and plan.end_date < plan.start_date:
            raise BadRequestError("end_date must be on or after start_date")
        self.db.commit()
        return plan

    # --- Quotation templates -------------------------------------------------

    def list_templates(self, active: bool | None, params: PageParams) -> tuple[list[QuotationTemplate], int]:
        return self.templates.list(active=active, page=params.page, size=params.size)

    def get_template(self, template_id: int) -> QuotationTemplate:
        template = self.templates.get_detail(template_id)
        if template is None:
            raise NotFoundError("Quotation template not found")
        return template

    def create_template(self, data: QuotationTemplateCreate, user: User) -> QuotationTemplate:
        self.get_plan(data.plan_id)
        template = self.templates.add(
            QuotationTemplate(
                **data.model_dump(exclude={"lines"}),
                lines=[self._build_line(line) for line in data.lines],
                created_by=user.id,
            )
        )
        self.db.commit()
        return self.get_template(template.id)

    def update_template(self, template_id: int, data: QuotationTemplateUpdate) -> QuotationTemplate:
        template = self.get_template(template_id)
        if data.plan_id is not None:
            self.get_plan(data.plan_id)
        apply_updates(template, data, exclude={"lines"})
        if data.lines is not None:
            template.lines = [self._build_line(line) for line in data.lines]
        self.db.commit()
        return self.get_template(template_id)

    def delete_template(self, template_id: int) -> None:
        template = self.get_template(template_id)
        try:
            self.templates.delete(template)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("Template is referenced by subscriptions; deactivate it instead") from exc

    def _build_line(self, line: TemplateLineIn) -> QuotationTemplateLine:
        _, _, default_price = self.catalog.resolve_item(line.product_id, line.variant_id)
        return QuotationTemplateLine(
            product_id=line.product_id,
            variant_id=line.variant_id,
            quantity=line.quantity,
            unit_price=line.unit_price if line.unit_price is not None else default_price,
            sequence=line.sequence,
        )
