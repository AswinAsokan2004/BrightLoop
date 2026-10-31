from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Column, ForeignKey, Index, String, Table, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, IdMixin, pg_enum
from app.models.catalog import Product
from app.models.enums import DiscountScope, DiscountType

discount_products = Table(
    "discount_products",
    Base.metadata,
    Column("discount_id", ForeignKey("discounts.id", ondelete="CASCADE"), primary_key=True),
    Column("product_id", ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
)


class Discount(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "discounts"
    __table_args__ = (
        Index("ix_discounts_active_start_date_end_date", "active", "start_date", "end_date"),
    )

    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str | None] = mapped_column(String(40), unique=True)
    discount_type: Mapped[DiscountType] = mapped_column(pg_enum(DiscountType, "discount_type"))
    value: Mapped[Decimal]
    scope: Mapped[DiscountScope] = mapped_column(pg_enum(DiscountScope, "discount_scope"))
    min_purchase_amount: Mapped[Decimal | None] = mapped_column(server_default="0")
    min_quantity: Mapped[int | None] = mapped_column(server_default="0")
    start_date: Mapped[date]
    end_date: Mapped[date | None]
    usage_limit: Mapped[int | None]
    used_count: Mapped[int] = mapped_column(server_default="0")
    active: Mapped[bool] = mapped_column(server_default=true())
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

    products: Mapped[list[Product]] = relationship(secondary=discount_products)

    @property
    def product_ids(self) -> list[int]:
        return [product.id for product in self.products]


class DiscountUsage(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "discount_usages"
    __table_args__ = (
        UniqueConstraint("discount_id", "invoice_id", name="uq_discount_usages_discount_id_invoice_id"),
    )

    discount_id: Mapped[int] = mapped_column(ForeignKey("discounts.id"))
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"))
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"))
    amount: Mapped[Decimal]
