from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import BillingRunStatus, InvoiceState
from app.schemas.common import ORMModel
from app.schemas.payment import PaymentRead


class InvoiceLineTaxRead(ORMModel):
    tax_id: int
    tax_name: str
    rate: Decimal
    amount: Decimal


class InvoiceLineRead(ORMModel):
    id: int
    product_id: int
    variant_id: int | None
    description: str
    quantity: int
    unit_price: Decimal
    discount_amount: Decimal
    untaxed_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    taxes: list[InvoiceLineTaxRead]


class InvoiceSummary(ORMModel):
    id: int
    number: str
    subscription_id: int
    customer_id: int
    state: InvoiceState
    currency: str
    invoice_date: date
    due_date: date
    period_start: date
    period_end: date
    total: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    is_overdue: bool


class InvoiceRead(InvoiceSummary):
    billing_run_id: int | None
    subtotal: Decimal
    discount_total: Decimal
    untaxed_total: Decimal
    tax_total: Decimal
    confirmed_at: datetime | None
    sent_at: datetime | None
    paid_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    lines: list[InvoiceLineRead]
    payments: list[PaymentRead]


class BillingRunRequest(BaseModel):
    run_date: date | None = None


class BillingRunRead(ORMModel):
    id: int
    run_date: date
    status: BillingRunStatus
    subscriptions_processed: int
    invoices_created: int
    errors_count: int
    error_log: str | None
    started_at: datetime
    finished_at: datetime | None
