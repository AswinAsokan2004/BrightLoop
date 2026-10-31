from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.security import utcnow
from app.models import Subscription, SubscriptionLine, SubscriptionStateLog, User
from app.models.enums import SubscriptionState as S
from app.repositories.billing import SequenceRepository
from app.repositories.customer import CustomerRepository, PaymentTermRepository
from app.repositories.discount import DiscountRepository
from app.repositories.plan import PlanRepository, QuotationTemplateRepository
from app.repositories.subscription import SubscriptionRepository
from app.schemas.common import PageParams
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionFromTemplate,
    SubscriptionLineIn,
    SubscriptionUpdate,
)
from app.services.catalog import CatalogService
from app.services.common import apply_updates
from app.services.periods import first_period_on_or_after, next_period_start
from app.services.pricing import LineInput, discount_rule, price_lines, tax_rule

# The only moves allowed. Anything else (e.g. draft -> closed) is rejected.
ALLOWED_TRANSITIONS: dict[S, set[S]] = {
    S.draft: {S.quotation},
    S.quotation: {S.draft, S.confirmed, S.closed},
    S.confirmed: {S.active, S.closed},
    S.active: {S.paused, S.closed},
    S.paused: {S.active, S.closed},
    S.closed: set(),
}
EDITABLE_STATES = {S.draft, S.quotation}
DEFAULT_QUOTATION_VALIDITY_DAYS = 30


class SubscriptionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.subscriptions = SubscriptionRepository(db)
        self.customers = CustomerRepository(db)
        self.payment_terms = PaymentTermRepository(db)
        self.plans = PlanRepository(db)
        self.templates = QuotationTemplateRepository(db)
        self.discounts = DiscountRepository(db)
        self.sequences = SequenceRepository(db)
        self.catalog = CatalogService(db)

    # --- Queries -------------------------------------------------------------

    def get(self, subscription_id: int, customer_id: int | None = None) -> Subscription:
        """customer_id restricts the lookup to that customer's own subscriptions (portal)."""
        subscription = self.subscriptions.get_detail(subscription_id, customer_id)
        if subscription is None:
            raise NotFoundError("Subscription not found")
        return subscription

    def list(
        self,
        params: PageParams,
        state: S | None = None,
        customer_id: int | None = None,
        plan_id: int | None = None,
        q: str | None = None,
        expiring_before: date | None = None,
    ) -> tuple[list[Subscription], int]:
        return self.subscriptions.list(
            state=state,
            customer_id=customer_id,
            plan_id=plan_id,
            q=q,
            expiring_before=expiring_before,
            page=params.page,
            size=params.size,
        )

    # --- Create / edit -------------------------------------------------------

    def create(self, data: SubscriptionCreate, user: User) -> Subscription:
        self._validate_header(data.customer_id, data.plan_id, data.payment_term_id, data.start_date, data.expiry_date)
        subscription = Subscription(
            number=self.sequences.next_number("subscription", "SUB", date.today().year),
            customer_id=data.customer_id,
            plan_id=data.plan_id,
            payment_term_id=data.payment_term_id,
            salesperson_id=data.salesperson_id or user.id,
            currency=data.currency.upper(),
            start_date=data.start_date,
            expiry_date=data.expiry_date,
            notes=data.notes,
            state=S.draft,
            lines=[self._build_line(line) for line in data.lines],
        )
        self.subscriptions.add(subscription)
        self._log(subscription, None, S.draft, user.id)
        self._recalculate(subscription)
        self.db.commit()
        return self.get(subscription.id)

    def create_from_template(self, data: SubscriptionFromTemplate, user: User) -> Subscription:
        """Start from a quotation template: plan and lines pre-filled, sent straight out as a quotation."""
        template = self.templates.get_detail(data.template_id)
        if template is None or not template.active:
            raise NotFoundError("Quotation template not found or inactive")
        self._validate_header(data.customer_id, template.plan_id, data.payment_term_id, data.start_date, data.expiry_date)

        subscription = Subscription(
            number=self.sequences.next_number("subscription", "SUB", date.today().year),
            customer_id=data.customer_id,
            plan_id=template.plan_id,
            quotation_template_id=template.id,
            payment_term_id=data.payment_term_id,
            salesperson_id=data.salesperson_id or user.id,
            currency=data.currency.upper(),
            start_date=data.start_date,
            expiry_date=data.expiry_date,
            notes=template.notes,
            state=S.quotation,
            quotation_valid_until=date.today() + timedelta(days=template.validity_days),
            lines=[
                self._build_line(
                    SubscriptionLineIn(
                        product_id=line.product_id,
                        variant_id=line.variant_id,
                        quantity=line.quantity,
                        unit_price=line.unit_price,
                    )
                )
                for line in template.lines
            ],
        )
        self.subscriptions.add(subscription)
        self._log(subscription, None, S.quotation, user.id, f"Created from template '{template.name}'")
        self._recalculate(subscription)
        self.db.commit()
        return self.get(subscription.id)

    def update(self, subscription_id: int, data: SubscriptionUpdate) -> Subscription:
        subscription = self.get(subscription_id)
        if subscription.state not in EDITABLE_STATES:
            raise BadRequestError("Only draft or quotation subscriptions can be edited")

        apply_updates(subscription, data, exclude={"lines"})
        self._validate_header(
            subscription.customer_id,
            subscription.plan_id,
            subscription.payment_term_id,
            subscription.start_date,
            subscription.expiry_date,
        )
        if data.lines is not None:
            subscription.lines = [self._build_line(line) for line in data.lines]
        self.db.flush()
        self._recalculate(subscription)
        self.db.commit()
        return self.get(subscription_id)

    def delete(self, subscription_id: int) -> None:
        subscription = self.get(subscription_id)
        if subscription.state != S.draft:
            raise BadRequestError("Only draft subscriptions can be deleted; close it instead")
        self.subscriptions.delete(subscription)
        self.db.commit()

    # --- Lifecycle -----------------------------------------------------------

    def change_state(
        self,
        subscription_id: int,
        to_state: S,
        user: User,
        reason: str | None = None,
        customer_id: int | None = None,
    ) -> Subscription:
        subscription = self.get(subscription_id, customer_id)
        from_state = subscription.state
        if to_state not in ALLOWED_TRANSITIONS[from_state]:
            raise BadRequestError(f"Cannot move a subscription from {from_state} to {to_state}")

        plan = subscription.plan
        today = date.today()

        match to_state:
            case S.quotation:
                if not subscription.lines:
                    raise BadRequestError("Add at least one line before sending a quotation")
                template = subscription.quotation_template
                validity = template.validity_days if template else DEFAULT_QUOTATION_VALIDITY_DAYS
                subscription.quotation_valid_until = today + timedelta(days=validity)

            case S.draft:
                subscription.quotation_valid_until = None

            case S.confirmed:
                if subscription.quotation_valid_until and subscription.quotation_valid_until < today:
                    raise BadRequestError(
                        f"Quotation expired on {subscription.quotation_valid_until}; move it back to draft and resend"
                    )
                quantity = sum(line.quantity for line in subscription.lines)
                if quantity < plan.min_quantity:
                    raise BadRequestError(f"Plan '{plan.name}' needs a quantity of at least {plan.min_quantity}")
                if not plan.is_available_on(subscription.start_date):
                    raise BadRequestError(f"Plan '{plan.name}' is not available on {subscription.start_date}")

            case S.active if from_state == S.confirmed:
                if plan.trial_days and subscription.trial_end_date is None:
                    subscription.trial_end_date = subscription.start_date + timedelta(days=plan.trial_days)
                subscription.next_invoice_date = subscription.billing_anchor

            case S.active:  # resume from pause: no charge for the paused time
                subscription.paused_at = None
                if subscription.next_invoice_date and subscription.next_invoice_date < today:
                    subscription.next_invoice_date = first_period_on_or_after(
                        subscription.billing_anchor, today, plan.billing_period, plan.billing_interval
                    )

            case S.paused:
                if not plan.pausable:
                    raise BadRequestError(f"Plan '{plan.name}' does not allow pausing")
                subscription.paused_at = utcnow()

            case S.closed:
                expired = subscription.expiry_date is not None and subscription.expiry_date < today
                if from_state in (S.active, S.paused) and not plan.closable and not expired:
                    raise BadRequestError(f"Plan '{plan.name}' cannot be closed before its expiry date")
                subscription.closed_at = utcnow()
                subscription.close_reason = reason
                subscription.next_invoice_date = None

        subscription.state = to_state
        self._log(subscription, from_state, to_state, user.id, reason)
        self.db.commit()
        return self.get(subscription_id)

    def renew(self, subscription_id: int, new_expiry_date: date, user: User) -> Subscription:
        subscription = self.get(subscription_id)
        plan = subscription.plan
        if not plan.renewable:
            raise BadRequestError(f"Plan '{plan.name}' is not renewable")
        if subscription.state not in (S.active, S.paused):
            raise BadRequestError("Only active or paused subscriptions can be renewed")
        if subscription.expiry_date is None:
            raise BadRequestError("Subscription has no expiry date to extend")
        if new_expiry_date <= subscription.expiry_date:
            raise BadRequestError("The new expiry date must be after the current one")

        subscription.expiry_date = new_expiry_date
        if subscription.state == S.active and subscription.next_invoice_date is None:
            # Billing stopped at the old expiry; pick up from the next unbilled period
            last = subscription.last_invoiced_date
            subscription.next_invoice_date = (
                next_period_start(subscription.billing_anchor, last, plan.billing_period, plan.billing_interval)
                if last
                else subscription.billing_anchor
            )
        self._log(subscription, subscription.state, subscription.state, user.id, f"Renewed until {new_expiry_date}")
        self.db.commit()
        return self.get(subscription_id)

    # --- Helpers -------------------------------------------------------------

    def _validate_header(
        self, customer_id: int, plan_id: int, payment_term_id: int, start_date: date, expiry_date: date | None
    ) -> None:
        if self.customers.get(customer_id) is None:
            raise BadRequestError(f"Customer {customer_id} not found")
        if self.payment_terms.get(payment_term_id) is None:
            raise BadRequestError(f"Payment term {payment_term_id} not found")
        plan = self.plans.get(plan_id)
        if plan is None:
            raise BadRequestError(f"Plan {plan_id} not found")
        if not plan.is_available_on(start_date):
            raise BadRequestError(f"Plan '{plan.name}' is not available on {start_date}")
        if expiry_date and expiry_date < start_date:
            raise BadRequestError("expiry_date must be on or after start_date")

    def _build_line(self, line: SubscriptionLineIn) -> SubscriptionLine:
        product, variant, default_price = self.catalog.resolve_item(line.product_id, line.variant_id)
        taxes = self.catalog.load_taxes(line.tax_ids) if line.tax_ids is not None else list(product.taxes)
        return SubscriptionLine(
            product_id=product.id,
            variant_id=variant.id if variant else None,
            description=line.description or (variant.name if variant else product.name),
            quantity=line.quantity,
            unit_price=line.unit_price if line.unit_price is not None else default_price,
            taxes=taxes,
            untaxed_amount=0,
            total_amount=0,
        )

    def _recalculate(self, subscription: Subscription) -> None:
        """Preview of the recurring amount with today's discounts. Invoices re-price at billing time."""
        lines = [
            LineInput(line.product_id, line.quantity, line.unit_price, tuple(tax_rule(t) for t in line.taxes))
            for line in subscription.lines
        ]
        rules = [discount_rule(d) for d in self.discounts.find_applicable(date.today())]
        result = price_lines(lines, rules)

        for line, priced in zip(subscription.lines, result.lines):
            line.discount_amount = priced.discount
            line.untaxed_amount = priced.untaxed
            line.tax_amount = priced.tax
            line.total_amount = priced.total
        subscription.recurring_untaxed = result.untaxed_total
        subscription.recurring_tax = result.tax_total
        subscription.recurring_total = result.total

    @staticmethod
    def _log(subscription: Subscription, from_state: S | None, to_state: S, user_id: int | None,
             reason: str | None = None) -> None:
        subscription.state_logs.append(
            SubscriptionStateLog(from_state=from_state, to_state=to_state, changed_by=user_id, reason=reason)
        )
