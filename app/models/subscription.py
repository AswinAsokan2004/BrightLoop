from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Column, ForeignKey, Index, String, Table, Text, false
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, IdMixin, TimestampMixin, pg_enum
from app.models.catalog import Product, ProductVariant, Tax
from app.models.customer import Customer, PaymentTerm
from app.models.enums import SubscriptionState
from app.models.plan import Plan, QuotationTemplate
from app.models.user import User

subscription_line_taxes = Table(
    "subscription_line_taxes",
    Base.metadata,
    Column(
        "subscription_line_id",
        ForeignKey("subscription_lines.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("tax_id", ForeignKey("taxes.id"), primary_key=True),
)


class Subscription(IdMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (Index("ix_subscriptions_state_next_invoice_date", "state", "next_invoice_date"),)

    number: Mapped[str] = mapped_column(String(30), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), index=True)
    quotation_template_id: Mapped[int | None] = mapped_column(ForeignKey("quotation_templates.id"))
    salesperson_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    payment_term_id: Mapped[int] = mapped_column(ForeignKey("payment_terms.id"))
    state: Mapped[SubscriptionState] = mapped_column(
        pg_enum(SubscriptionState, "subscription_state"),
        server_default=SubscriptionState.draft.value,
        index=True,
    )
    currency: Mapped[str] = mapped_column(String(3))
    quotation_valid_until: Mapped[date | None]
    start_date: Mapped[date]
    expiry_date: Mapped[date | None] = mapped_column(index=True)
    trial_end_date: Mapped[date | None]
    next_invoice_date: Mapped[date | None]
    last_invoiced_date: Mapped[date | None]
    paused_at: Mapped[datetime | None]
    closed_at: Mapped[datetime | None]
    close_reason: Mapped[str | None] = mapped_column(String(255))
    recurring_untaxed: Mapped[Decimal] = mapped_column(server_default="0")
    recurring_tax: Mapped[Decimal] = mapped_column(server_default="0")
    recurring_total: Mapped[Decimal] = mapped_column(server_default="0")
    notes: Mapped[str | None] = mapped_column(Text)

    customer: Mapped[Customer] = relationship()
    plan: Mapped[Plan] = relationship()
    payment_term: Mapped[PaymentTerm] = relationship()
    quotation_template: Mapped[QuotationTemplate | None] = relationship()
    salesperson: Mapped[User | None] = relationship(foreign_keys=[salesperson_id])
    lines: Mapped[list[SubscriptionLine]] = relationship(
        cascade="all, delete-orphan", order_by="SubscriptionLine.id"
    )
    state_logs: Mapped[list[SubscriptionStateLog]] = relationship(
        cascade="all, delete-orphan", order_by="SubscriptionStateLog.id"
    )

    @property
    def billing_anchor(self) -> date:
        """Billing periods are counted from the end of the trial, or from the start date."""
        return self.trial_end_date or self.start_date

    @property
    def customer_name(self) -> str:
        return self.customer.company_name or self.customer.name

    @property
    def plan_name(self) -> str:
        return self.plan.name


class SubscriptionLine(IdMixin, Base):
    __tablename__ = "subscription_lines"

    is_addon: Mapped[bool] = mapped_column(server_default=false())

    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"))
    description: Mapped[str | None] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(server_default="1")
    unit_price: Mapped[Decimal]
    discount_amount: Mapped[Decimal] = mapped_column(server_default="0")
    untaxed_amount: Mapped[Decimal]
    tax_amount: Mapped[Decimal] = mapped_column(server_default="0")
    total_amount: Mapped[Decimal]

    product: Mapped[Product] = relationship()
    variant: Mapped[ProductVariant | None] = relationship()
    taxes: Mapped[list[Tax]] = relationship(secondary=subscription_line_taxes)


class SubscriptionStateLog(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "subscription_state_logs"

    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True
    )
    from_state: Mapped[SubscriptionState | None] = mapped_column(
        pg_enum(SubscriptionState, "subscription_state")
    )
    to_state: Mapped[SubscriptionState] = mapped_column(pg_enum(SubscriptionState, "subscription_state"))
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str | None] = mapped_column(String(255))
    changed_by_user: Mapped[User | None] = relationship()


class SubscriptionAddonChange(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "subscription_addon_changes"

    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True
    )
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    effective_date: Mapped[date]
    before_items: Mapped[list] = mapped_column(JSONB)
    after_items: Mapped[list] = mapped_column(JSONB)
    before_total: Mapped[Decimal]
    after_total: Mapped[Decimal]
    changed_by_user: Mapped[User | None] = relationship(foreign_keys=[changed_by])
