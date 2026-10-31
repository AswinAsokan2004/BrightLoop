from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import ForeignKey, String, Text, false, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, IdMixin, pg_enum
from app.models.enums import BillingPeriod


class Plan(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(40), unique=True)
    price: Mapped[Decimal]
    billing_period: Mapped[BillingPeriod] = mapped_column(pg_enum(BillingPeriod, "billing_period"))
    billing_interval: Mapped[int] = mapped_column(server_default="1")
    min_quantity: Mapped[int] = mapped_column(server_default="1")
    start_date: Mapped[date]
    end_date: Mapped[date | None]
    auto_close: Mapped[bool] = mapped_column(server_default=false())
    closable: Mapped[bool] = mapped_column(server_default=true())
    pausable: Mapped[bool] = mapped_column(server_default=false())
    renewable: Mapped[bool] = mapped_column(server_default=true())
    trial_days: Mapped[int] = mapped_column(server_default="0")
    active: Mapped[bool] = mapped_column(server_default=true())
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    def is_available_on(self, day: date) -> bool:
        return self.active and self.start_date <= day and (self.end_date is None or day <= self.end_date)


class QuotationTemplate(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "quotation_templates"

    name: Mapped[str] = mapped_column(String(150))
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    validity_days: Mapped[int] = mapped_column(server_default="30")
    notes: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(server_default=true())
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    plan: Mapped[Plan] = relationship()
    lines: Mapped[list[QuotationTemplateLine]] = relationship(
        cascade="all, delete-orphan",
        order_by="(QuotationTemplateLine.sequence, QuotationTemplateLine.id)",
    )


class QuotationTemplateLine(IdMixin, Base):
    __tablename__ = "quotation_template_lines"

    template_id: Mapped[int] = mapped_column(
        ForeignKey("quotation_templates.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"))
    quantity: Mapped[int] = mapped_column(server_default="1")
    unit_price: Mapped[Decimal]
    sequence: Mapped[int] = mapped_column(server_default="0")
