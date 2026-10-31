from enum import StrEnum


class UserRole(StrEnum):
    admin = "admin"
    staff = "staff"
    customer = "customer"


class ProductType(StrEnum):
    service = "service"
    goods = "goods"
    addon = "addon"


class BillingPeriod(StrEnum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


class SubscriptionState(StrEnum):
    draft = "draft"
    quotation = "quotation"
    confirmed = "confirmed"
    active = "active"
    paused = "paused"
    closed = "closed"


class InvoiceState(StrEnum):
    draft = "draft"
    confirmed = "confirmed"
    paid = "paid"
    cancelled = "cancelled"


class TaxType(StrEnum):
    percent = "percent"
    fixed = "fixed"


class DiscountType(StrEnum):
    percent = "percent"
    fixed = "fixed"


class DiscountScope(StrEnum):
    product = "product"
    subscription = "subscription"


class PaymentMethod(StrEnum):
    cash = "cash"
    bank_transfer = "bank_transfer"
    card = "card"
    upi = "upi"
    cheque = "cheque"
    online_gateway = "online_gateway"


class PaymentStatus(StrEnum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"


class BillingRunStatus(StrEnum):
    running = "running"
    completed = "completed"
    failed = "failed"
