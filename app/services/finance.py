"""Bounded finance reads. Money is aggregated in SQL for one currency at a time."""

from datetime import date
from decimal import Decimal
from sqlalchemy import Date, case, cast, func, select, union
from sqlalchemy.orm import Session
from app.core.exceptions import BadRequestError
from app.models import Customer, Invoice, Payment, Plan, Subscription
from app.models.enums import InvoiceState, PaymentStatus, SubscriptionState
from app.schemas.finance import FinanceReport
from app.services.pricing import money
from app.services.report import MONTHLY_FACTOR


class FinanceService:
    def __init__(self, db: Session):
        self.db = db

    def report(
        self,
        date_from=None,
        date_to=None,
        customer_id=None,
        plan_id=None,
        currency=None,
        invoice_view="overdue",
        invoice_page=1,
        payment_page=1,
        subscription_page=1,
        size=10,
    ):
        if date_from and date_to and date_from > date_to:
            raise BadRequestError("From date must be on or before To date")
        sub_filters = []
        inv_filters = []
        if customer_id:
            sub_filters.append(Subscription.customer_id == customer_id)
            inv_filters.append(Invoice.customer_id == customer_id)
        if plan_id:
            sub_filters.append(Subscription.plan_id == plan_id)
            inv_filters.append(Subscription.plan_id == plan_id)
        # Available currencies deliberately ignore dates so an empty date window keeps its currency.
        currency_query = union(
            select(Subscription.currency).where(*sub_filters),
            select(Invoice.currency)
            .join(Subscription, Subscription.id == Invoice.subscription_id)
            .where(*inv_filters),
        )
        currencies = sorted(self.db.scalars(currency_query).all())
        currency = currency or (currencies[0] if currencies else "INR")
        sub_filters.append(Subscription.currency == currency)
        inv_filters.append(Invoice.currency == currency)
        inv_dates = []
        pay_dates = []
        if date_from:
            inv_dates.append(Invoice.invoice_date >= date_from)
            pay_dates.append(Payment.payment_date >= date_from)
        if date_to:
            inv_dates.append(Invoice.invoice_date <= date_to)
            pay_dates.append(Payment.payment_date <= date_to)
        billed = Invoice.state.in_([InvoiceState.confirmed, InvoiceState.paid])
        outstanding = (Invoice.state == InvoiceState.confirmed) & (Invoice.amount_due > 0)
        overdue = outstanding & (Invoice.due_date < date.today())
        zero = Decimal("0.00")
        aggregates = (
            self.db.execute(
                select(
                    func.coalesce(func.sum(case((billed, Invoice.total), else_=0)), 0).label(
                        "invoiced_total"
                    ),
                    func.coalesce(func.sum(case((outstanding, Invoice.amount_due), else_=0)), 0).label(
                        "outstanding_amount"
                    ),
                    func.sum(case((outstanding, 1), else_=0)).label("outstanding_count"),
                    func.coalesce(func.sum(case((overdue, Invoice.amount_due), else_=0)), 0).label(
                        "overdue_amount"
                    ),
                    func.sum(case((overdue, 1), else_=0)).label("overdue_count"),
                )
                .select_from(Invoice)
                .join(Subscription, Subscription.id == Invoice.subscription_id)
                .where(*inv_filters, *inv_dates)
            )
            .mappings()
            .one()
        )
        active = [*sub_filters, Subscription.state == SubscriptionState.active]
        active_count = self.db.scalar(select(func.count()).select_from(Subscription).where(*active))
        recurring = self.db.execute(
            select(Plan.billing_period, Plan.billing_interval, func.sum(Subscription.recurring_untaxed))
            .join(Plan, Plan.id == Subscription.plan_id)
            .where(*active)
            .group_by(Plan.billing_period, Plan.billing_interval)
        )
        mrr = money(
            sum((total * MONTHLY_FACTOR[period] / interval for period, interval, total in recurring), zero)
        )
        inv_base = select(
            Invoice.id,
            Invoice.number,
            Customer.name.label("customer_name"),
            Invoice.invoice_date,
            Invoice.due_date,
            Invoice.state,
            Invoice.total,
            Invoice.amount_due,
        ).join(Customer, Customer.id == Invoice.customer_id)
        inv_base = inv_base.join(Subscription, Subscription.id == Invoice.subscription_id).where(
            *inv_filters, *inv_dates
        )
        if invoice_view == "overdue":
            inv_base = inv_base.where(overdue)
        elif invoice_view == "outstanding":
            inv_base = inv_base.where(outstanding)
        elif invoice_view == "billed":
            inv_base = inv_base.where(billed)
        invoice_count = self.db.scalar(select(func.count()).select_from(inv_base.subquery()))
        invoices = (
            self.db.execute(
                inv_base.order_by(Invoice.due_date, Invoice.id).limit(size).offset((invoice_page - 1) * size)
            )
            .mappings()
            .all()
        )
        payment_filters = [*inv_filters, *pay_dates, Payment.status == PaymentStatus.completed]
        pay_base = select(
            Payment.id,
            Payment.invoice_id,
            Invoice.number.label("invoice_number"),
            Customer.name.label("customer_name"),
            Payment.payment_date,
            Payment.method,
            Payment.amount,
            Payment.reference,
        )
        pay_base = pay_base.join(Invoice, Invoice.id == Payment.invoice_id).join(
            Subscription, Subscription.id == Invoice.subscription_id
        )
        pay_base = pay_base.join(Customer, Customer.id == Payment.customer_id).where(*payment_filters)
        payment_count = self.db.scalar(select(func.count()).select_from(pay_base.subquery()))
        collected = self.db.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .select_from(Payment)
            .join(Invoice, Invoice.id == Payment.invoice_id)
            .join(Subscription, Subscription.id == Invoice.subscription_id)
            .where(*payment_filters)
        )
        payments = (
            self.db.execute(
                pay_base.order_by(Payment.payment_date.desc(), Payment.id.desc())
                .limit(size)
                .offset((payment_page - 1) * size)
            )
            .mappings()
            .all()
        )
        subscriptions = (
            self.db.execute(
                select(
                    Subscription.id,
                    Subscription.number,
                    Customer.name.label("customer_name"),
                    Plan.name.label("plan_name"),
                    Subscription.recurring_untaxed,
                )
                .join(Customer, Customer.id == Subscription.customer_id)
                .join(Plan, Plan.id == Subscription.plan_id)
                .where(*active)
                .order_by(Subscription.id.desc())
                .limit(size)
                .offset((subscription_page - 1) * size)
            )
            .mappings()
            .all()
        )
        inv_month = cast(func.date_trunc("month", Invoice.invoice_date), Date)
        pay_month = cast(func.date_trunc("month", Payment.payment_date), Date)
        monthly_invoices = dict(
            self.db.execute(
                select(inv_month, func.sum(Invoice.total))
                .select_from(Invoice)
                .join(Subscription, Subscription.id == Invoice.subscription_id)
                .where(*inv_filters, *inv_dates, billed)
                .group_by(inv_month)
            ).all()
        )
        monthly_payments = dict(
            self.db.execute(
                select(pay_month, func.sum(Payment.amount))
                .select_from(Payment)
                .join(Invoice, Invoice.id == Payment.invoice_id)
                .join(Subscription, Subscription.id == Invoice.subscription_id)
                .where(*payment_filters)
                .group_by(pay_month)
            ).all()
        )
        return FinanceReport(
            currency=currency,
            currencies=currencies,
            active_subscriptions=active_count,
            mrr=mrr,
            invoiced_total=aggregates["invoiced_total"],
            revenue_collected=collected,
            outstanding_amount=aggregates["outstanding_amount"],
            outstanding_count=aggregates["outstanding_count"] or 0,
            overdue_amount=aggregates["overdue_amount"],
            overdue_count=aggregates["overdue_count"] or 0,
            invoices=invoices,
            invoice_count=invoice_count,
            payments=payments,
            payment_count=payment_count,
            subscriptions=subscriptions,
            monthly=[
                dict(month=m, invoiced=monthly_invoices.get(m, zero), collected=monthly_payments.get(m, zero))
                for m in sorted(monthly_invoices.keys() | monthly_payments.keys())
            ],
        )
