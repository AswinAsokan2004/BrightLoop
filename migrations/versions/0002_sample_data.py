"""sample data

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-31

Scenario: Northwind Corp takes 5 seats of Brightloop CRM (Odoo brand: 1200 + 560 = 1760),
gets a 10% volume discount, GST 18%, and pays part of October's invoice.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables with an identity "id" column whose sequence must move past the seeded ids
SEEDED_ID_TABLES = [
    "payment_terms",
    "customers",
    "users",
    "taxes",
    "products",
    "product_attributes",
    "product_attribute_values",
    "product_variants",
    "plans",
    "quotation_templates",
    "quotation_template_lines",
    "discounts",
    "subscriptions",
    "subscription_lines",
    "subscription_state_logs",
    "billing_runs",
    "invoices",
    "invoice_lines",
    "invoice_line_taxes",
    "discount_usages",
    "payments",
    "number_sequences",
]

SEEDED_TABLES = SEEDED_ID_TABLES + [
    "variant_attribute_values",
    "product_taxes",
    "discount_products",
    "subscription_line_taxes",
]


def upgrade() -> None:
    op.execute("""
        INSERT INTO payment_terms (id, name, due_days) VALUES
            (1, 'Immediate', 0),
            (2, 'Net 15', 15),
            (3, 'Net 30', 30)
    """)

    op.execute("""
        INSERT INTO customers (id, name, company_name, email, city, country) VALUES
            (1, 'Kumar Retail', 'Kumar Retail', 'billing@kumarretail.com', 'Kochi', 'IN'),
            (2, 'Northwind Corp', 'Northwind Corporation Pvt Ltd', 'accounts@northwind.com', 'Bengaluru', 'IN')
    """)

    op.execute("""
        INSERT INTO users (id, name, email, password_hash, role, customer_id, created_by) VALUES
            (1, 'Riya Menon', 'admin@brightloop.com', '$2b$12$hashedpasswordadmin', 'admin', NULL, NULL),
            (2, 'Arjun Nair', 'arjun@brightloop.com', '$2b$12$hashedpasswordstaff', 'staff', NULL, 1),
            (3, 'Northwind Accounts', 'accounts@northwind.com', '$2b$12$hashedpasswordcust', 'customer', 2, NULL)
    """)

    op.execute("""
        INSERT INTO taxes (id, name, tax_type, rate) VALUES
            (1, 'GST 18%', 'percent', 18)
    """)

    op.execute("""
        INSERT INTO products (id, name, product_type, sales_price, cost_price, notes, created_by) VALUES
            (1, 'Brightloop CRM', 'service', 1200, 400, 'Core CRM, priced per seat', 1),
            (2, 'Extra Storage Add-on', 'addon', 300, 50, '100 GB extra storage', 1)
    """)

    op.execute("INSERT INTO product_attributes (id, name) VALUES (1, 'Brand')")

    op.execute("""
        INSERT INTO product_attribute_values (id, attribute_id, value, extra_price) VALUES
            (1, 1, 'Odoo', 560),
            (2, 1, 'Generic', 0)
    """)

    op.execute("""
        INSERT INTO product_variants (id, product_id, sku, name, extra_price) VALUES
            (1, 1, 'CRM-ODOO', 'Brightloop CRM (Odoo)', 560),
            (2, 1, 'CRM-GEN', 'Brightloop CRM (Generic)', 0)
    """)

    op.execute("""
        INSERT INTO variant_attribute_values (variant_id, attribute_value_id) VALUES
            (1, 1),
            (2, 2)
    """)

    op.execute("""
        INSERT INTO product_taxes (product_id, tax_id) VALUES
            (1, 1),
            (2, 1)
    """)

    op.execute("""
        INSERT INTO plans (id, name, code, price, billing_period, min_quantity, start_date,
                           auto_close, closable, pausable, renewable, created_by) VALUES
            (1, 'Monthly Standard', 'MONTHLY-STD', 1200, 'monthly', 1, '2026-01-01', false, true, true, true, 1),
            (2, 'Yearly Enterprise', 'YEARLY-ENT', 12000, 'yearly', 5, '2026-01-01', true, false, false, true, 1)
    """)

    op.execute("""
        INSERT INTO quotation_templates (id, name, plan_id, validity_days, created_by) VALUES
            (1, 'Enterprise CRM - Monthly', 1, 30, 2)
    """)

    op.execute("""
        INSERT INTO quotation_template_lines (id, template_id, product_id, variant_id, quantity, unit_price) VALUES
            (1, 1, 1, 1, 5, 1760)
    """)

    op.execute("""
        INSERT INTO discounts (id, name, discount_type, value, scope, min_quantity, start_date, end_date,
                               usage_limit, used_count, created_by) VALUES
            (1, 'Volume 10% (5+ seats)', 'percent', 10, 'product', 5, '2026-01-01', '2026-12-31', 100, 1, 1)
    """)

    op.execute("INSERT INTO discount_products (discount_id, product_id) VALUES (1, 1)")

    op.execute("""
        INSERT INTO subscriptions (id, number, customer_id, plan_id, quotation_template_id, salesperson_id,
                                   payment_term_id, state, currency, start_date, expiry_date,
                                   next_invoice_date, last_invoiced_date,
                                   recurring_untaxed, recurring_tax, recurring_total) VALUES
            (1, 'SUB/2026/00001', 2, 1, 1, 2, 3, 'active', 'INR', '2026-10-01', '2027-09-30',
             '2026-11-01', '2026-10-01', 7920, 1425.60, 9345.60)
    """)

    op.execute("""
        INSERT INTO subscription_lines (id, subscription_id, product_id, variant_id, description, quantity,
                                        unit_price, discount_amount, untaxed_amount, tax_amount, total_amount) VALUES
            (1, 1, 1, 1, 'Brightloop CRM (Odoo)', 5, 1760, 880, 7920, 1425.60, 9345.60)
    """)

    op.execute("INSERT INTO subscription_line_taxes (subscription_line_id, tax_id) VALUES (1, 1)")

    op.execute("""
        INSERT INTO subscription_state_logs (id, subscription_id, from_state, to_state, changed_by, created_at) VALUES
            (1, 1, NULL, 'draft', 2, '2026-09-20'),
            (2, 1, 'draft', 'quotation', 2, '2026-09-21'),
            (3, 1, 'quotation', 'confirmed', 2, '2026-09-28'),
            (4, 1, 'confirmed', 'active', 2, '2026-10-01')
    """)

    op.execute("""
        INSERT INTO billing_runs (id, run_date, status, subscriptions_processed, invoices_created, errors_count) VALUES
            (1, '2026-10-01', 'completed', 1, 1, 0)
    """)

    op.execute("""
        INSERT INTO invoices (id, number, subscription_id, customer_id, billing_run_id, state, currency,
                              invoice_date, due_date, period_start, period_end, subtotal, discount_total,
                              untaxed_total, tax_total, total, amount_paid, amount_due) VALUES
            (1, 'INV/2026/00001', 1, 2, 1, 'confirmed', 'INR', '2026-10-01', '2026-10-31',
             '2026-10-01', '2026-10-31', 8800, 880, 7920, 1425.60, 9345.60, 5000, 4345.60)
    """)

    op.execute("""
        INSERT INTO invoice_lines (id, invoice_id, product_id, variant_id, description, quantity, unit_price,
                                   discount_amount, untaxed_amount, tax_amount, total_amount) VALUES
            (1, 1, 1, 1, 'Brightloop CRM (Odoo) - Oct 2026', 5, 1760, 880, 7920, 1425.60, 9345.60)
    """)

    op.execute("""
        INSERT INTO invoice_line_taxes (id, invoice_line_id, tax_id, tax_name, rate, amount) VALUES
            (1, 1, 1, 'GST 18%', 18, 1425.60)
    """)

    op.execute("""
        INSERT INTO discount_usages (id, discount_id, subscription_id, invoice_id, amount) VALUES
            (1, 1, 1, 1, 880)
    """)

    op.execute("""
        INSERT INTO payments (id, invoice_id, customer_id, method, amount, payment_date, reference, note,
                              status, recorded_by) VALUES
            (1, 1, 2, 'bank_transfer', 5000, '2026-10-15', 'NEFT-NW-88213',
             'Partial payment, balance next week', 'completed', 2)
    """)

    op.execute("""
        INSERT INTO number_sequences (id, code, prefix, year, next_number) VALUES
            (1, 'subscription', 'SUB', 2026, 2),
            (2, 'invoice', 'INV', 2026, 2),
            (3, 'credit_note', 'CN', 2026, 1)
    """)

    # Explicit ids don't advance identity sequences; move them past the seeded rows
    for table in SEEDED_ID_TABLES:
        op.execute(
            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), (SELECT MAX(id) FROM {table}))"
        )


def downgrade() -> None:
    op.execute(f"TRUNCATE {', '.join(SEEDED_TABLES)} RESTART IDENTITY CASCADE")
