from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import BillingPeriod
from app.schemas.common import Money, ORMModel


class PlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=40)
    price: Money
    billing_period: BillingPeriod
    billing_interval: int = Field(1, ge=1, description="Every N periods, e.g. 3 x monthly = quarterly")
    min_quantity: int = Field(1, ge=1)
    start_date: date
    end_date: date | None = None
    auto_close: bool = False
    closable: bool = True
    pausable: bool = False
    renewable: bool = True
    trial_days: int = Field(0, ge=0)

    @model_validator(mode="after")
    def check_dates(self) -> "PlanCreate":
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class PlanUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    price: Money | None = None
    billing_period: BillingPeriod | None = None
    billing_interval: int | None = Field(None, ge=1)
    min_quantity: int | None = Field(None, ge=1)
    start_date: date | None = None
    end_date: date | None = None
    auto_close: bool | None = None
    closable: bool | None = None
    pausable: bool | None = None
    renewable: bool | None = None
    trial_days: int | None = Field(None, ge=0)
    active: bool | None = None


class PlanRead(ORMModel):
    id: int
    name: str
    code: str
    price: Decimal
    billing_period: BillingPeriod
    billing_interval: int
    min_quantity: int
    start_date: date
    end_date: date | None
    auto_close: bool
    closable: bool
    pausable: bool
    renewable: bool
    trial_days: int
    active: bool
    created_at: datetime


class TemplateLineIn(BaseModel):
    product_id: int
    variant_id: int | None = None
    quantity: int = Field(1, ge=1)
    unit_price: Money | None = Field(None, description="Defaults to product price + variant extra")
    sequence: int = 0


class TemplateLineRead(ORMModel):
    id: int
    product_id: int
    variant_id: int | None
    quantity: int
    unit_price: Decimal
    sequence: int


class QuotationTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    plan_id: int
    validity_days: int = Field(30, ge=1)
    notes: str | None = None
    lines: list[TemplateLineIn] = Field(min_length=1)


class QuotationTemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=150)
    plan_id: int | None = None
    validity_days: int | None = Field(None, ge=1)
    notes: str | None = None
    active: bool | None = None
    lines: list[TemplateLineIn] | None = Field(None, min_length=1)


class QuotationTemplateRead(ORMModel):
    id: int
    name: str
    plan_id: int
    validity_days: int
    notes: str | None
    active: bool
    created_at: datetime
    lines: list[TemplateLineRead]
