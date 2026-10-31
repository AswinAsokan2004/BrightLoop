from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, IdMixin, TimestampMixin, pg_enum
from app.models.customer import Customer
from app.models.enums import BillingRunStatus, InvoiceState, PaymentMethod, PaymentStatus


class NumberSequence(IdMixin, Base):
    __tablename__ = "number_sequences"
    __table_args__ = (UniqueConstraint("code", "year", name="uq_number_sequences_code_year"),)

    code: Mapped[str] = mapped_column(String(30))
    prefix: Mapped[str] = mapped_column(String(10))
    year: Mapped[int]
    next_number: Mapped[int] = mapped_column(server_default="1")


class BillingRun(IdMixin, Base):
    __tablename__ = "billing_runs"

    run_date: Mapped[date]
    status: Mapped[BillingRunStatus] = mapped_column(
        pg_enum(BillingRunStatus, "billing_run_status"), server_default=BillingRunStatus.running.value
    )
    subscriptions_processed: Mapped[int] = mapped_column(server_default="0")
    invoices_created: Mapped[int] = mapped_column(server_default="0")
    errors_count: Mapped[int] = mapped_column(server_default="0")
    error_log: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    finished_at: Mapped[datetime | None]


class Invoice(IdMixin, TimestampMixin, Base):
    __tablename__ = "invoices"
    __table_args__ = (
        # Guarantees nothing is billed twice
        UniqueConstraint("subscription_id", "period_start", name="uq_invoices_subscription_id_period_start"),
        Index("ix_invoices_state_due_date", "state", "due_date"),
    )

    number: Mapped[str] = mapped_column(String(30), unique=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    billing_run_id: Mapped[int | None] = mapped_column(ForeignKey("billing_runs.id"))
    state: Mapped[InvoiceState] = mapped_column(
        pg_enum(InvoiceState, "invoice_state"), server_default=InvoiceState.draft.value, index=True
    )
    currency: Mapped[str] = mapped_column(String(3))
    invoice_date: Mapped[date] = mapped_column(index=True)
    due_date: Mapped[date]
    period_start: Mapped[date]
    period_end: Mapped[date]
    subtotal: Mapped[Decimal] = mapped_column(server_default="0")
    discount_total: Mapped[Decimal] = mapped_column(server_default="0")
    untaxed_total: Mapped[Decimal] = mapped_column(server_default="0")
    tax_total: Mapped[Decimal] = mapped_column(server_default="0")
    total: Mapped[Decimal] = mapped_column(server_default="0")
    amount_paid: Mapped[Decimal] = mapped_column(server_default="0")
    amount_due: Mapped[Decimal] = mapped_column(server_default="0")
    confirmed_at: Mapped[datetime | None]
    sent_at: Mapped[datetime | None]
    paid_at: Mapped[datetime | None]
    cancelled_at: Mapped[datetime | None]
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    customer: Mapped[Customer] = relationship()
    lines: Mapped[list[InvoiceLine]] = relationship(cascade="all, delete-orphan", order_by="InvoiceLine.id")
    payments: Mapped[list[Payment]] = relationship(order_by="Payment.id")

    @property
    def is_overdue(self) -> bool:
        return (
            self.state == InvoiceState.confirmed
            and self.amount_due > 0
            and self.due_date < date.today()
        )


class InvoiceLine(IdMixin, Base):
    __tablename__ = "invoice_lines"

    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"))
    description: Mapped[str] = mapped_column(String(255))  # snapshot
    quantity: Mapped[int]
    unit_price: Mapped[Decimal]  # snapshot
    discount_amount: Mapped[Decimal] = mapped_column(server_default="0")
    untaxed_amount: Mapped[Decimal]
    tax_amount: Mapped[Decimal] = mapped_column(server_default="0")
    total_amount: Mapped[Decimal]

    taxes: Mapped[list[InvoiceLineTax]] = relationship(cascade="all, delete-orphan", order_by="InvoiceLineTax.id")


class InvoiceLineTax(IdMixin, Base):
    __tablename__ = "invoice_line_taxes"

    invoice_line_id: Mapped[int] = mapped_column(
        ForeignKey("invoice_lines.id", ondelete="CASCADE"), index=True
    )
    tax_id: Mapped[int] = mapped_column(ForeignKey("taxes.id"))
    tax_name: Mapped[str] = mapped_column(String(80))  # snapshot
    rate: Mapped[Decimal] = mapped_column(Numeric(8, 3))  # snapshot
    amount: Mapped[Decimal]


class CreditNote(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "credit_notes"

    number: Mapped[str] = mapped_column(String(30), unique=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    amount: Mapped[Decimal]
    reason: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class Payment(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "payments"

    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    method: Mapped[PaymentMethod] = mapped_column(pg_enum(PaymentMethod, "payment_method"))
    amount: Mapped[Decimal]
    payment_date: Mapped[date] = mapped_column(index=True)
    reference: Mapped[str | None] = mapped_column(String(120))
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[PaymentStatus] = mapped_column(
        pg_enum(PaymentStatus, "payment_status"), server_default=PaymentStatus.completed.value
    )
    gateway: Mapped[str | None] = mapped_column(String(30))
    gateway_payment_id: Mapped[str | None] = mapped_column(String(120), unique=True)
    recorded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class InvoiceReminder(IdMixin, Base):
    __tablename__ = "invoice_reminders"
    __table_args__ = (UniqueConstraint("invoice_id", "level", name="uq_invoice_reminders_invoice_id_level"),)

    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"))
    level: Mapped[int]
    channel: Mapped[str] = mapped_column(String(20), server_default="email")
    sent_at: Mapped[datetime] = mapped_column(server_default=func.now())
