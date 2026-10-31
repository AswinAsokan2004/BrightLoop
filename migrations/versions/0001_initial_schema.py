"""initial schema: subscription management system

Revision ID: 0001
Revises:
Create Date: 2026-10-31

Conventions
- Money: Numeric(12, 2), never float
- Invoice lines SNAPSHOT prices and taxes, so later catalog changes never alter old invoices
- unique(subscription_id, period_start) on invoices prevents double billing
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Enums (created explicitly, so tables that share one don't re-create it)
# ---------------------------------------------------------------------------

user_role = postgresql.ENUM("admin", "staff", "customer", name="user_role", create_type=False)
product_type = postgresql.ENUM("service", "goods", "addon", name="product_type", create_type=False)
billing_period = postgresql.ENUM(
    "daily", "weekly", "monthly", "yearly", name="billing_period", create_type=False
)
subscription_state = postgresql.ENUM(
    "draft", "quotation", "confirmed", "active", "paused", "closed",
    name="subscription_state", create_type=False,
)
invoice_state = postgresql.ENUM(
    "draft", "confirmed", "paid", "cancelled", name="invoice_state", create_type=False
)
tax_type = postgresql.ENUM("percent", "fixed", name="tax_type", create_type=False)
discount_type = postgresql.ENUM("percent", "fixed", name="discount_type", create_type=False)
discount_scope = postgresql.ENUM("product", "subscription", name="discount_scope", create_type=False)
payment_method = postgresql.ENUM(
    "cash", "bank_transfer", "card", "upi", "cheque", "online_gateway",
    name="payment_method", create_type=False,
)
payment_status = postgresql.ENUM(
    "pending", "completed", "failed", "refunded", name="payment_status", create_type=False
)
billing_run_status = postgresql.ENUM(
    "running", "completed", "failed", name="billing_run_status", create_type=False
)

ENUMS = [
    user_role,
    product_type,
    billing_period,
    subscription_state,
    invoice_state,
    tax_type,
    discount_type,
    discount_scope,
    payment_method,
    payment_status,
    billing_run_status,
]


# ---------------------------------------------------------------------------
# Column helpers
# ---------------------------------------------------------------------------

def id_column() -> sa.Column:
    return sa.Column("id", sa.Integer, sa.Identity(), primary_key=True)


def money(name: str, nullable: bool = False, default: str | None = None, **kw) -> sa.Column:
    return sa.Column(
        name,
        sa.Numeric(12, 2),
        nullable=nullable,
        server_default=sa.text(default) if default is not None else None,
        **kw,
    )


def flag(name: str, default: bool) -> sa.Column:
    return sa.Column(
        name, sa.Boolean, nullable=False, server_default=sa.true() if default else sa.false()
    )


def fk(name: str, target: str, nullable: bool = True, ondelete: str | None = None, **kw) -> sa.Column:
    return sa.Column(
        name, sa.Integer, sa.ForeignKey(target, ondelete=ondelete), nullable=nullable, **kw
    )


def timestamp(name: str, nullable: bool = True) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable)


def created_at() -> sa.Column:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


def updated_at() -> sa.Column:
    return sa.Column(
        "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


# Creation order respects foreign keys; downgrade drops in reverse.
TABLES = [
    "customers",
    "payment_terms",
    "users",
    "password_reset_tokens",
    "refresh_tokens",
    "products",
    "product_attributes",
    "product_attribute_values",
    "product_variants",
    "variant_attribute_values",
    "taxes",
    "product_taxes",
    "plans",
    "quotation_templates",
    "quotation_template_lines",
    "subscriptions",
    "subscription_lines",
    "subscription_line_taxes",
    "subscription_state_logs",
    "discounts",
    "discount_products",
    "number_sequences",
    "billing_runs",
    "invoices",
    "invoice_lines",
    "invoice_line_taxes",
    "discount_usages",
    "credit_notes",
    "payments",
    "invoice_reminders",
    "notifications",
    "audit_logs",
]


def upgrade() -> None:
    bind = op.get_bind()
    for enum in ENUMS:
        enum.create(bind, checkfirst=True)

    # -----------------------------------------------------------------------
    # CUSTOMERS
    # -----------------------------------------------------------------------

    op.create_table(
        "customers",
        id_column(),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("company_name", sa.String(150)),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(30)),
        sa.Column("address_line1", sa.String(255)),
        sa.Column("address_line2", sa.String(255)),
        sa.Column("city", sa.String(100)),
        sa.Column("state", sa.String(100)),
        sa.Column("postal_code", sa.String(20)),
        sa.Column("country", sa.String(2)),
        sa.Column("tax_id", sa.String(50), comment="GSTIN / VAT number"),
        created_at(),
        updated_at(),
    )
    op.create_index("ix_customers_email", "customers", ["email"])
    op.create_index("ix_customers_name", "customers", ["name"])

    op.create_table(
        "payment_terms",
        id_column(),
        sa.Column("name", sa.String(50), nullable=False, unique=True,
                  comment="e.g. Immediate, Net 15, Net 30"),
        sa.Column("due_days", sa.Integer, nullable=False, server_default="0"),
    )

    # -----------------------------------------------------------------------
    # AUTH & USERS
    # -----------------------------------------------------------------------

    op.create_table(
        "users",
        id_column(),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True,
                  comment="One account per email"),
        sa.Column("password_hash", sa.String(255), nullable=False,
                  comment="bcrypt/argon2. Rule: >8 chars, upper, lower, special"),
        sa.Column("role", user_role, nullable=False, server_default="customer"),
        fk("customer_id", "customers.id", comment="Set only when role = customer"),
        flag("is_active", True),
        timestamp("email_verified_at"),
        timestamp("last_login_at"),
        fk("created_by", "users.id", comment="Admin who created this staff account"),
        created_at(),
        updated_at(),
    )
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_customer_id", "users", ["customer_id"])

    op.create_table(
        "password_reset_tokens",
        id_column(),
        fk("user_id", "users.id", nullable=False, ondelete="CASCADE"),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True,
                  comment="Store hash only, never the raw token"),
        timestamp("expires_at", nullable=False),
        timestamp("used_at", nullable=True),
        created_at(),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])

    op.create_table(
        "refresh_tokens",
        id_column(),
        fk("user_id", "users.id", nullable=False, ondelete="CASCADE"),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("user_agent", sa.String(255)),
        sa.Column("ip_address", sa.String(45)),
        timestamp("expires_at", nullable=False),
        timestamp("revoked_at"),
        created_at(),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    # -----------------------------------------------------------------------
    # PRODUCT CATALOG & VARIANTS
    # -----------------------------------------------------------------------

    op.create_table(
        "products",
        id_column(),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("product_type", product_type, nullable=False),
        money("sales_price", default="0"),
        money("cost_price", default="0"),
        sa.Column("notes", sa.Text),
        flag("is_recurring", True),
        flag("active", True),
        fk("created_by", "users.id"),
        created_at(),
        updated_at(),
    )

    op.create_table(
        "product_attributes",
        id_column(),
        sa.Column("name", sa.String(80), nullable=False, unique=True,
                  comment="e.g. Brand, Edition, Region"),
    )

    op.create_table(
        "product_attribute_values",
        id_column(),
        fk("attribute_id", "product_attributes.id", nullable=False, ondelete="CASCADE"),
        sa.Column("value", sa.String(80), nullable=False, comment="e.g. Odoo"),
        money("extra_price", default="0", comment="e.g. +560 for Odoo brand"),
        sa.UniqueConstraint("attribute_id", "value", name="uq_product_attribute_values_attribute_value"),
    )

    op.create_table(
        "product_variants",
        id_column(),
        fk("product_id", "products.id", nullable=False, ondelete="CASCADE"),
        sa.Column("sku", sa.String(60), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        money("extra_price", default="0",
              comment="Cached sum of attribute value extras. Unit price = product.sales_price + extra_price"),
        flag("active", True),
    )
    op.create_index("ix_product_variants_product_id", "product_variants", ["product_id"])

    op.create_table(
        "variant_attribute_values",
        fk("variant_id", "product_variants.id", nullable=False, ondelete="CASCADE"),
        fk("attribute_value_id", "product_attribute_values.id", nullable=False, ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("variant_id", "attribute_value_id"),
    )

    # -----------------------------------------------------------------------
    # TAXES
    # -----------------------------------------------------------------------

    op.create_table(
        "taxes",
        id_column(),
        sa.Column("name", sa.String(80), nullable=False, comment="e.g. GST 18%"),
        sa.Column("tax_type", tax_type, nullable=False, server_default="percent"),
        sa.Column("rate", sa.Numeric(8, 3), nullable=False, comment="Percent value or fixed amount"),
        flag("is_inclusive", False),
        flag("active", True),
        created_at(),
    )

    op.create_table(
        "product_taxes",
        fk("product_id", "products.id", nullable=False, ondelete="CASCADE"),
        fk("tax_id", "taxes.id", nullable=False),
        sa.PrimaryKeyConstraint("product_id", "tax_id"),
    )

    # -----------------------------------------------------------------------
    # PLANS
    # -----------------------------------------------------------------------

    op.create_table(
        "plans",
        id_column(),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("code", sa.String(40), nullable=False, unique=True),
        money("price", comment="Base recurring price per period"),
        sa.Column("billing_period", billing_period, nullable=False),
        sa.Column("billing_interval", sa.Integer, nullable=False, server_default="1",
                  comment="Every N periods, e.g. 3 x monthly = quarterly"),
        sa.Column("min_quantity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("start_date", sa.Date, nullable=False, comment="Available from"),
        sa.Column("end_date", sa.Date, comment="Available until"),
        flag("auto_close", False),
        flag("closable", True),
        flag("pausable", False),
        flag("renewable", True),
        sa.Column("trial_days", sa.Integer, nullable=False, server_default="0",
                  comment="Advanced: free trial"),
        flag("active", True),
        fk("created_by", "users.id"),
        created_at(),
    )

    # -----------------------------------------------------------------------
    # QUOTATION TEMPLATES
    # -----------------------------------------------------------------------

    op.create_table(
        "quotation_templates",
        id_column(),
        sa.Column("name", sa.String(150), nullable=False),
        fk("plan_id", "plans.id", nullable=False),
        sa.Column("validity_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column("notes", sa.Text),
        flag("active", True),
        fk("created_by", "users.id"),
        created_at(),
    )

    op.create_table(
        "quotation_template_lines",
        id_column(),
        fk("template_id", "quotation_templates.id", nullable=False, ondelete="CASCADE"),
        fk("product_id", "products.id", nullable=False),
        fk("variant_id", "product_variants.id"),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="1"),
        money("unit_price"),
        sa.Column("sequence", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("ix_quotation_template_lines_template_id", "quotation_template_lines", ["template_id"])

    # -----------------------------------------------------------------------
    # SUBSCRIPTIONS
    # -----------------------------------------------------------------------

    op.create_table(
        "subscriptions",
        id_column(),
        sa.Column("number", sa.String(30), nullable=False, unique=True, comment="e.g. SUB/2026/00001"),
        fk("customer_id", "customers.id", nullable=False),
        fk("plan_id", "plans.id", nullable=False),
        fk("quotation_template_id", "quotation_templates.id"),
        fk("salesperson_id", "users.id"),
        fk("payment_term_id", "payment_terms.id", nullable=False),
        sa.Column("state", subscription_state, nullable=False, server_default="draft"),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("quotation_valid_until", sa.Date,
                  comment="created date + template.validity_days"),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("expiry_date", sa.Date),
        sa.Column("trial_end_date", sa.Date),
        sa.Column("next_invoice_date", sa.Date,
                  comment="Billing engine picks rows where this <= today AND state = active"),
        sa.Column("last_invoiced_date", sa.Date),
        timestamp("paused_at"),
        timestamp("closed_at"),
        sa.Column("close_reason", sa.String(255)),
        money("recurring_untaxed", default="0"),
        money("recurring_tax", default="0"),
        money("recurring_total", default="0"),
        sa.Column("notes", sa.Text),
        created_at(),
        updated_at(),
    )
    op.create_index("ix_subscriptions_state", "subscriptions", ["state"])
    op.create_index("ix_subscriptions_customer_id", "subscriptions", ["customer_id"])
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"])
    op.create_index("ix_subscriptions_state_next_invoice_date", "subscriptions",
                    ["state", "next_invoice_date"])  # billing run lookup
    op.create_index("ix_subscriptions_expiry_date", "subscriptions", ["expiry_date"])

    op.create_table(
        "subscription_lines",
        id_column(),
        fk("subscription_id", "subscriptions.id", nullable=False, ondelete="CASCADE"),
        fk("product_id", "products.id", nullable=False),
        fk("variant_id", "product_variants.id"),
        sa.Column("description", sa.String(255)),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="1"),
        money("unit_price"),
        money("discount_amount", default="0"),
        money("untaxed_amount", comment="qty * unit_price - discount"),
        money("tax_amount", default="0"),
        money("total_amount"),
    )
    op.create_index("ix_subscription_lines_subscription_id", "subscription_lines", ["subscription_id"])

    op.create_table(
        "subscription_line_taxes",
        fk("subscription_line_id", "subscription_lines.id", nullable=False, ondelete="CASCADE"),
        fk("tax_id", "taxes.id", nullable=False),
        sa.PrimaryKeyConstraint("subscription_line_id", "tax_id"),
    )

    op.create_table(
        "subscription_state_logs",
        id_column(),
        fk("subscription_id", "subscriptions.id", nullable=False, ondelete="CASCADE"),
        sa.Column("from_state", subscription_state),
        sa.Column("to_state", subscription_state, nullable=False),
        fk("changed_by", "users.id"),
        sa.Column("reason", sa.String(255)),
        created_at(),
    )
    op.create_index("ix_subscription_state_logs_subscription_id", "subscription_state_logs",
                    ["subscription_id"])

    # -----------------------------------------------------------------------
    # DISCOUNTS
    # -----------------------------------------------------------------------

    op.create_table(
        "discounts",
        id_column(),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("code", sa.String(40), unique=True, comment="Optional coupon code (advanced)"),
        sa.Column("discount_type", discount_type, nullable=False),
        money("value", comment="Percent or fixed amount"),
        sa.Column("scope", discount_scope, nullable=False),
        money("min_purchase_amount", nullable=True, default="0"),
        sa.Column("min_quantity", sa.Integer, server_default="0"),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date),
        sa.Column("usage_limit", sa.Integer, comment="NULL = unlimited"),
        sa.Column("used_count", sa.Integer, nullable=False, server_default="0",
                  comment="Increment atomically: WHERE used_count < usage_limit"),
        flag("active", True),
        fk("created_by", "users.id", nullable=False, comment="Admin only"),
        created_at(),
    )
    op.create_index("ix_discounts_active_start_date_end_date", "discounts",
                    ["active", "start_date", "end_date"])

    op.create_table(
        "discount_products",
        fk("discount_id", "discounts.id", nullable=False, ondelete="CASCADE"),
        fk("product_id", "products.id", nullable=False, ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("discount_id", "product_id"),
    )

    # -----------------------------------------------------------------------
    # BILLING & INVOICES
    # -----------------------------------------------------------------------

    op.create_table(
        "number_sequences",
        id_column(),
        sa.Column("code", sa.String(30), nullable=False,
                  comment="subscription | invoice | credit_note"),
        sa.Column("prefix", sa.String(10), nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("next_number", sa.Integer, nullable=False, server_default="1"),
        sa.UniqueConstraint("code", "year", name="uq_number_sequences_code_year"),
    )

    op.create_table(
        "billing_runs",
        id_column(),
        sa.Column("run_date", sa.Date, nullable=False),
        sa.Column("status", billing_run_status, nullable=False, server_default="running"),
        sa.Column("subscriptions_processed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("invoices_created", sa.Integer, nullable=False, server_default="0"),
        sa.Column("errors_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_log", sa.Text),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        timestamp("finished_at"),
    )

    op.create_table(
        "invoices",
        id_column(),
        sa.Column("number", sa.String(30), nullable=False, unique=True, comment="e.g. INV/2026/00001"),
        fk("subscription_id", "subscriptions.id", nullable=False),
        fk("customer_id", "customers.id", nullable=False),
        fk("billing_run_id", "billing_runs.id"),
        sa.Column("state", invoice_state, nullable=False, server_default="draft"),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("invoice_date", sa.Date, nullable=False),
        sa.Column("due_date", sa.Date, nullable=False,
                  comment="invoice_date + payment_terms.due_days"),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        money("subtotal", default="0", comment="Before discounts"),
        money("discount_total", default="0"),
        money("untaxed_total", default="0"),
        money("tax_total", default="0"),
        money("total", default="0"),
        money("amount_paid", default="0"),
        money("amount_due", default="0",
              comment="Overdue = due_date < today AND amount_due > 0 AND state = confirmed"),
        timestamp("confirmed_at"),
        timestamp("sent_at"),
        timestamp("paid_at"),
        timestamp("cancelled_at"),
        fk("created_by", "users.id"),
        created_at(),
        updated_at(),
        # Guarantees nothing is billed twice
        sa.UniqueConstraint("subscription_id", "period_start",
                            name="uq_invoices_subscription_id_period_start"),
    )
    op.create_index("ix_invoices_customer_id", "invoices", ["customer_id"])
    op.create_index("ix_invoices_state", "invoices", ["state"])
    op.create_index("ix_invoices_state_due_date", "invoices", ["state", "due_date"])  # overdue queries
    op.create_index("ix_invoices_invoice_date", "invoices", ["invoice_date"])

    op.create_table(
        "invoice_lines",
        id_column(),
        fk("invoice_id", "invoices.id", nullable=False, ondelete="CASCADE"),
        fk("product_id", "products.id", nullable=False),
        fk("variant_id", "product_variants.id"),
        sa.Column("description", sa.String(255), nullable=False,
                  comment="Snapshot of product/variant name"),
        sa.Column("quantity", sa.Integer, nullable=False),
        money("unit_price", comment="Snapshot at invoice time"),
        money("discount_amount", default="0"),
        money("untaxed_amount"),
        money("tax_amount", default="0"),
        money("total_amount"),
    )
    op.create_index("ix_invoice_lines_invoice_id", "invoice_lines", ["invoice_id"])

    op.create_table(
        "invoice_line_taxes",
        id_column(),
        fk("invoice_line_id", "invoice_lines.id", nullable=False, ondelete="CASCADE"),
        fk("tax_id", "taxes.id", nullable=False),
        sa.Column("tax_name", sa.String(80), nullable=False, comment="Snapshot"),
        sa.Column("rate", sa.Numeric(8, 3), nullable=False, comment="Snapshot"),
        money("amount"),
    )
    op.create_index("ix_invoice_line_taxes_invoice_line_id", "invoice_line_taxes", ["invoice_line_id"])

    op.create_table(
        "discount_usages",
        id_column(),
        fk("discount_id", "discounts.id", nullable=False),
        fk("subscription_id", "subscriptions.id", nullable=False),
        fk("invoice_id", "invoices.id", nullable=False),
        money("amount"),
        created_at(),
        sa.UniqueConstraint("discount_id", "invoice_id", name="uq_discount_usages_discount_id_invoice_id"),
    )

    op.create_table(
        "credit_notes",
        id_column(),
        sa.Column("number", sa.String(30), nullable=False, unique=True),
        fk("invoice_id", "invoices.id", nullable=False),
        money("amount"),
        sa.Column("reason", sa.String(255)),
        fk("created_by", "users.id"),
        created_at(),
    )
    op.create_index("ix_credit_notes_invoice_id", "credit_notes", ["invoice_id"])

    # -----------------------------------------------------------------------
    # PAYMENTS & DUNNING
    # -----------------------------------------------------------------------

    op.create_table(
        "payments",
        id_column(),
        fk("invoice_id", "invoices.id", nullable=False),
        fk("customer_id", "customers.id", nullable=False),
        sa.Column("method", payment_method, nullable=False),
        money("amount"),
        sa.Column("payment_date", sa.Date, nullable=False),
        sa.Column("reference", sa.String(120), comment="Bank ref / cheque no."),
        sa.Column("note", sa.Text),
        sa.Column("status", payment_status, nullable=False, server_default="completed"),
        sa.Column("gateway", sa.String(30), comment="stripe | razorpay (advanced)"),
        sa.Column("gateway_payment_id", sa.String(120), unique=True,
                  comment="Idempotency for webhooks"),
        fk("recorded_by", "users.id"),
        created_at(),
    )
    op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"])
    op.create_index("ix_payments_customer_id", "payments", ["customer_id"])
    op.create_index("ix_payments_payment_date", "payments", ["payment_date"])

    op.create_table(
        "invoice_reminders",
        id_column(),
        fk("invoice_id", "invoices.id", nullable=False, ondelete="CASCADE"),
        sa.Column("level", sa.Integer, nullable=False,
                  comment="1 = 3 days overdue, 2 = 7 days, 3 = 14 days"),
        sa.Column("channel", sa.String(20), nullable=False, server_default="email"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("invoice_id", "level", name="uq_invoice_reminders_invoice_id_level"),
    )

    # -----------------------------------------------------------------------
    # NOTIFICATIONS & AUDIT
    # -----------------------------------------------------------------------

    op.create_table(
        "notifications",
        id_column(),
        fk("user_id", "users.id", nullable=False, ondelete="CASCADE"),
        sa.Column("type", sa.String(50), nullable=False,
                  comment="renewal_due | invoice_overdue | payment_received ..."),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("body", sa.Text),
        sa.Column("link", sa.String(255)),
        timestamp("read_at"),
        created_at(),
    )
    op.create_index("ix_notifications_user_id_read_at", "notifications", ["user_id", "read_at"])

    op.create_table(
        "audit_logs",
        id_column(),
        fk("user_id", "users.id"),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer, nullable=False),
        sa.Column("action", sa.String(30), nullable=False,
                  comment="create | update | delete | state_change"),
        sa.Column("old_values", postgresql.JSONB),
        sa.Column("new_values", postgresql.JSONB),
        sa.Column("ip_address", sa.String(45)),
        created_at(),
    )
    op.create_index("ix_audit_logs_entity_type_entity_id", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)

    bind = op.get_bind()
    for enum in reversed(ENUMS):
        enum.drop(bind, checkfirst=True)
