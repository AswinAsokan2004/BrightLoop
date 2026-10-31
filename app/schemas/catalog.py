from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import ProductType, TaxType
from app.schemas.common import Money, ORMModel


# --- Taxes -------------------------------------------------------------------


class TaxCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    tax_type: TaxType = TaxType.percent
    rate: Decimal = Field(ge=0, max_digits=8, decimal_places=3, description="Percent, or fixed amount per unit")
    is_inclusive: bool = False

    @model_validator(mode="after")
    def check_rate(self) -> "TaxCreate":
        if self.tax_type == TaxType.percent and self.rate > 100:
            raise ValueError("A percent tax rate cannot exceed 100")
        return self


class TaxUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=80)
    rate: Decimal | None = Field(None, ge=0, max_digits=8, decimal_places=3)
    is_inclusive: bool | None = None
    active: bool | None = None


class TaxRead(ORMModel):
    id: int
    name: str
    tax_type: TaxType
    rate: Decimal
    is_inclusive: bool
    active: bool


# --- Attributes & variants ----------------------------------------------------


class AttributeValueCreate(BaseModel):
    value: str = Field(min_length=1, max_length=80, examples=["Odoo"])
    extra_price: Money = Field(Decimal("0"), examples=["560.00"])


class AttributeValueUpdate(BaseModel):
    value: str | None = Field(None, min_length=1, max_length=80)
    extra_price: Money | None = None


class AttributeValueRead(ORMModel):
    id: int
    attribute_id: int
    value: str
    extra_price: Decimal


class AttributeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80, examples=["Brand"])
    values: list[AttributeValueCreate] = []


class AttributeRead(ORMModel):
    id: int
    name: str
    values: list[AttributeValueRead]


class VariantCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=60)
    name: str | None = Field(None, max_length=200, description="Defaults to 'Product (Value, ...)'")
    attribute_value_ids: list[int] = Field(min_length=1)


class VariantUpdate(BaseModel):
    sku: str | None = Field(None, min_length=1, max_length=60)
    name: str | None = Field(None, min_length=1, max_length=200)
    active: bool | None = None


class VariantRead(ORMModel):
    id: int
    product_id: int
    sku: str
    name: str
    extra_price: Decimal
    unit_price: Decimal
    active: bool
    attribute_values: list[AttributeValueRead]


# --- Products ----------------------------------------------------------------


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    product_type: ProductType
    sales_price: Money = Decimal("0")
    cost_price: Money = Decimal("0")
    notes: str | None = None
    is_recurring: bool = True
    tax_ids: list[int] = []


class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=150)
    product_type: ProductType | None = None
    sales_price: Money | None = None
    cost_price: Money | None = None
    notes: str | None = None
    is_recurring: bool | None = None
    active: bool | None = None
    tax_ids: list[int] | None = None


class ProductRead(ORMModel):
    id: int
    name: str
    product_type: ProductType
    sales_price: Decimal
    cost_price: Decimal
    notes: str | None
    is_recurring: bool
    active: bool
    created_at: datetime
    updated_at: datetime
    taxes: list[TaxRead]
    variants: list[VariantRead]
