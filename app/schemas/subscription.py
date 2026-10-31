from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import SubscriptionState
from app.schemas.catalog import TaxRead
from app.schemas.common import Money, ORMModel

Currency = Field("INR", min_length=3, max_length=3)


class SubscriptionLineIn(BaseModel):
    product_id: int
    variant_id: int | None = None
    quantity: int = Field(1, ge=1)
    unit_price: Money | None = Field(None, description="Defaults to product price + variant extra")
    description: str | None = Field(None, max_length=255)
    tax_ids: list[int] | None = Field(None, description="Defaults to the product's taxes")


class SubscriptionCreate(BaseModel):
    customer_id: int
    plan_id: int
    payment_term_id: int
    start_date: date
    expiry_date: date | None = None
    currency: str = Currency
    salesperson_id: int | None = None
    notes: str | None = None
    lines: list[SubscriptionLineIn] = Field(min_length=1)


class SubscriptionFromTemplate(BaseModel):
    template_id: int
    customer_id: int
    payment_term_id: int
    start_date: date
    expiry_date: date | None = None
    currency: str = Currency
    salesperson_id: int | None = None


class SubscriptionUpdate(BaseModel):
    plan_id: int | None = None
    payment_term_id: int | None = None
    start_date: date | None = None
    expiry_date: date | None = None
    currency: str | None = Field(None, min_length=3, max_length=3)
    salesperson_id: int | None = None
    notes: str | None = None
    lines: list[SubscriptionLineIn] | None = Field(None, min_length=1)


class StateChangeRequest(BaseModel):
    state: SubscriptionState
    reason: str | None = Field(None, max_length=255)


class RenewRequest(BaseModel):
    new_expiry_date: date


class SubscriptionLineRead(ORMModel):
    id: int
    product_id: int
    variant_id: int | None
    description: str | None
    quantity: int
    unit_price: Decimal
    discount_amount: Decimal
    untaxed_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    taxes: list[TaxRead]


class StateLogRead(ORMModel):
    id: int
    from_state: SubscriptionState | None
    to_state: SubscriptionState
    changed_by: int | None
    reason: str | None
    created_at: datetime


class SubscriptionSummary(ORMModel):
    id: int
    number: str
    customer_id: int
    plan_id: int
    state: SubscriptionState
    currency: str
    start_date: date
    expiry_date: date | None
    next_invoice_date: date | None
    recurring_total: Decimal
    created_at: datetime


class SubscriptionRead(SubscriptionSummary):
    quotation_template_id: int | None
    salesperson_id: int | None
    payment_term_id: int
    quotation_valid_until: date | None
    trial_end_date: date | None
    last_invoiced_date: date | None
    paused_at: datetime | None
    closed_at: datetime | None
    close_reason: str | None
    recurring_untaxed: Decimal
    recurring_tax: Decimal
    notes: str | None
    updated_at: datetime
    lines: list[SubscriptionLineRead]
    state_logs: list[StateLogRead]
