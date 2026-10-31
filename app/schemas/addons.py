from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.catalog import TaxRead
from app.schemas.common import ORMModel
from app.schemas.subscription import NameRead


class AddonSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: int = Field(ge=1)
    variant_id: int | None = Field(None, ge=1)
    quantity: int = Field(ge=1, le=10000)


class AddonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[AddonSelection] = Field(max_length=50)

    @model_validator(mode="after")
    def no_duplicates(self):
        keys = [(i.product_id, i.variant_id) for i in self.items]
        if len(keys) != len(set(keys)):
            raise ValueError("Choose each add-on and variant only once")
        return self


class AddonApply(AddonRequest):
    fingerprint: str = Field(min_length=64, max_length=64)


class AddonItem(BaseModel):
    product_id: int
    variant_id: int | None
    name: str
    variant_name: str | None
    quantity: int
    unit_price: Decimal


class AddonOffer(BaseModel):
    product_id: int
    variant_id: int | None
    name: str
    variant_name: str | None
    unit_price: Decimal
    taxes: list[TaxRead]


class AddonWorkspace(BaseModel):
    eligible: bool
    reason: str | None
    currency: str
    effective_date: date | None
    items: list[AddonItem]


class AddonQuote(BaseModel):
    currency: str
    effective_date: date
    fingerprint: str
    before_items: list[AddonItem]
    after_items: list[AddonItem]
    before_total: Decimal
    after_total: Decimal
    delta: Decimal
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal


class AddonChangeRead(ORMModel):
    id: int
    effective_date: date
    before_items: list[AddonItem]
    after_items: list[AddonItem]
    before_total: Decimal
    after_total: Decimal
    created_at: datetime
    changed_by_user: NameRead | None
