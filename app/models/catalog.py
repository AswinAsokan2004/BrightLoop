from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Column, ForeignKey, Numeric, String, Table, Text, UniqueConstraint, false, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, IdMixin, TimestampMixin, pg_enum
from app.models.enums import ProductType, TaxType

product_taxes = Table(
    "product_taxes",
    Base.metadata,
    Column("product_id", ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("tax_id", ForeignKey("taxes.id"), primary_key=True),
)

variant_attribute_values = Table(
    "variant_attribute_values",
    Base.metadata,
    Column("variant_id", ForeignKey("product_variants.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "attribute_value_id",
        ForeignKey("product_attribute_values.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Tax(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "taxes"

    name: Mapped[str] = mapped_column(String(80))
    tax_type: Mapped[TaxType] = mapped_column(
        pg_enum(TaxType, "tax_type"), server_default=TaxType.percent.value
    )
    rate: Mapped[Decimal] = mapped_column(Numeric(8, 3))
    is_inclusive: Mapped[bool] = mapped_column(server_default=false())
    active: Mapped[bool] = mapped_column(server_default=true())


class Product(IdMixin, TimestampMixin, Base):
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(150))
    product_type: Mapped[ProductType] = mapped_column(pg_enum(ProductType, "product_type"))
    sales_price: Mapped[Decimal] = mapped_column(server_default="0")
    cost_price: Mapped[Decimal] = mapped_column(server_default="0")
    notes: Mapped[str | None] = mapped_column(Text)
    is_recurring: Mapped[bool] = mapped_column(server_default=true())
    active: Mapped[bool] = mapped_column(server_default=true())
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    taxes: Mapped[list[Tax]] = relationship(secondary=product_taxes)
    variants: Mapped[list[ProductVariant]] = relationship(
        back_populates="product", order_by="ProductVariant.id"
    )


class ProductAttribute(IdMixin, Base):
    __tablename__ = "product_attributes"

    name: Mapped[str] = mapped_column(String(80), unique=True)

    values: Mapped[list[ProductAttributeValue]] = relationship(
        back_populates="attribute", cascade="all, delete-orphan", order_by="ProductAttributeValue.id"
    )


class ProductAttributeValue(IdMixin, Base):
    __tablename__ = "product_attribute_values"
    __table_args__ = (
        UniqueConstraint("attribute_id", "value", name="uq_product_attribute_values_attribute_value"),
    )

    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("product_attributes.id", ondelete="CASCADE")
    )
    value: Mapped[str] = mapped_column(String(80))
    extra_price: Mapped[Decimal] = mapped_column(server_default="0")

    attribute: Mapped[ProductAttribute] = relationship(back_populates="values")


class ProductVariant(IdMixin, Base):
    __tablename__ = "product_variants"

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    sku: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    # Cached sum of the attribute values' extra prices
    extra_price: Mapped[Decimal] = mapped_column(server_default="0")
    active: Mapped[bool] = mapped_column(server_default=true())

    product: Mapped[Product] = relationship(back_populates="variants")
    attribute_values: Mapped[list[ProductAttributeValue]] = relationship(
        secondary=variant_attribute_values
    )

    @property
    def unit_price(self) -> Decimal:
        return self.product.sales_price + self.extra_price
