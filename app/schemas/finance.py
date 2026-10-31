from datetime import date
from decimal import Decimal
from pydantic import BaseModel


class FinanceInvoice(BaseModel):
    id: int
    number: str
    customer_name: str
    invoice_date: date
    due_date: date
    state: str
    total: Decimal
    amount_due: Decimal


class FinancePayment(BaseModel):
    id: int
    invoice_id: int
    invoice_number: str
    customer_name: str
    payment_date: date
    method: str
    amount: Decimal
    reference: str | None


class FinanceSubscription(BaseModel):
    id: int
    number: str
    customer_name: str
    plan_name: str
    recurring_untaxed: Decimal


class FinanceMonth(BaseModel):
    month: date
    invoiced: Decimal
    collected: Decimal


class FinanceReport(BaseModel):
    currency: str
    currencies: list[str]
    active_subscriptions: int
    mrr: Decimal
    invoiced_total: Decimal
    revenue_collected: Decimal
    outstanding_amount: Decimal
    outstanding_count: int
    overdue_amount: Decimal
    overdue_count: int
    invoices: list[FinanceInvoice]
    invoice_count: int
    payments: list[FinancePayment]
    payment_count: int
    subscriptions: list[FinanceSubscription]
    monthly: list[FinanceMonth]
