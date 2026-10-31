from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import DiscountScope, DiscountType
from app.schemas.common import Money, ORMModel, PositiveMoney


class DiscountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str | None = Field(None, min_length=1, max_length=40, description="Optional coupon code")
    discount_type: DiscountType
    value: PositiveMoney = Field(description="Percent (0-100) or fixed amount")
    scope: DiscountScope
    min_purchase_amount: Money = Decimal("0")
    min_quantity: int = Field(0, ge=0)
    start_date: date
    end_date: date | None = None
    usage_limit: int | None = Field(None, ge=1, description="Leave empty for unlimited")
    product_ids: list[int] = Field([], description="Required when scope = product")

    @model_validator(mode="after")
    def check_rule(self) -> "DiscountCreate":
        if self.discount_type == DiscountType.percent and self.value > 100:
            raise ValueError("A percentage discount cannot exceed 100")
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if self.scope == DiscountScope.product and not self.product_ids:
            raise ValueError("Product-scoped discounts need at least one product_id")
        return self


class DiscountUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    code: str | None = Field(None, min_length=1, max_length=40)
    value: PositiveMoney | None = None
    min_purchase_amount: Money | None = None
    min_quantity: int | None = Field(None, ge=0)
    start_date: date | None = None
    end_date: date | None = None
    usage_limit: int | None = Field(None, ge=1)
    active: bool | None = None
    product_ids: list[int] | None = None


class DiscountRead(ORMModel):
    id: int
    name: str
    code: str | None
    discount_type: DiscountType
    value: Decimal
    scope: DiscountScope
    min_purchase_amount: Decimal | None
    min_quantity: int | None
    start_date: date
    end_date: date | None
    usage_limit: int | None
    used_count: int
    active: bool
    created_at: datetime
    product_ids: list[int]
