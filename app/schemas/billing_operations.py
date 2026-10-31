from datetime import date
from decimal import Decimal
from pydantic import BaseModel
from app.models.enums import BillingPeriod, SubscriptionState
from app.schemas.invoice import InvoiceSummary


class BillingPreviewItem(BaseModel):
    id: int
    number: str
    customer_name: str
    plan_name: str
    state: SubscriptionState
    currency: str
    next_invoice_date: date | None
    expiry_date: date | None
    billing_period: BillingPeriod
    billing_interval: int
    first_period_end: date | None
    due_periods: int


class BillingPreview(BaseModel):
    run_date: date
    due_subscriptions: int
    auto_close_subscriptions: int
    items: list[BillingPreviewItem]
    total: int
    page: int
    size: int


class BillingRunInvoice(InvoiceSummary):
    customer_name: str
    subscription_number: str


class BillingFailure(BaseModel):
    subscription_id: int | None
    subscription_number: str | None
    customer_name: str | None
    message: str
