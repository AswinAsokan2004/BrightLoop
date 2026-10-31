"""Import every model so Base.metadata is complete (used by Alembic and relationships)."""

from app.models.audit import AuditLog, Notification
from app.models.base import Base
from app.models.billing import (
    BillingRun,
    CreditNote,
    Invoice,
    InvoiceLine,
    InvoiceLineTax,
    InvoiceReminder,
    NumberSequence,
    Payment,
)
from app.models.catalog import Product, ProductAttribute, ProductAttributeValue, ProductVariant, Tax
from app.models.customer import Customer, PaymentTerm
from app.models.discount import Discount, DiscountUsage
from app.models.plan import Plan, QuotationTemplate, QuotationTemplateLine
from app.models.subscription import Subscription, SubscriptionLine, SubscriptionStateLog
from app.models.user import PasswordResetToken, RefreshToken, User

__all__ = [
    "AuditLog",
    "Base",
    "BillingRun",
    "CreditNote",
    "Customer",
    "Discount",
    "DiscountUsage",
    "Invoice",
    "InvoiceLine",
    "InvoiceLineTax",
    "InvoiceReminder",
    "Notification",
    "NumberSequence",
    "PasswordResetToken",
    "Payment",
    "PaymentTerm",
    "Plan",
    "Product",
    "ProductAttribute",
    "ProductAttributeValue",
    "ProductVariant",
    "QuotationTemplate",
    "QuotationTemplateLine",
    "RefreshToken",
    "Subscription",
    "SubscriptionLine",
    "SubscriptionStateLog",
    "Tax",
    "User",
]
