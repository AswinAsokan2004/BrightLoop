"""Customer changes apply to the next unbilled period; invoiced snapshots never change."""

import hashlib
import json
from datetime import date
from decimal import Decimal
from sqlalchemy import exists, func, literal, select, union_all
from sqlalchemy.orm import Session, selectinload
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import (
    Product,
    ProductVariant,
    Subscription,
    SubscriptionAddonChange,
    SubscriptionLine,
    Tax,
    User,
)
from app.models.catalog import product_taxes
from app.models.enums import ProductType, SubscriptionState
from app.repositories.discount import DiscountRepository
from app.repositories.subscription import SubscriptionRepository
from app.schemas.addons import (
    AddonApply,
    AddonChangeRead,
    AddonItem,
    AddonOffer,
    AddonQuote,
    AddonRequest,
    AddonWorkspace,
)
from app.schemas.catalog import TaxRead
from app.schemas.common import Page, PageParams
from app.services.pricing import LineInput, discount_rule, price_lines, tax_rule
from app.services.subscription import SubscriptionService


class AddonService:
    def __init__(self, db: Session):
        self.db = db
        self.subscriptions = SubscriptionRepository(db)

    def owned(self, subscription_id, customer_id):
        sub = self.subscriptions.get_detail(subscription_id, customer_id)
        if sub is None:
            raise NotFoundError("Subscription not found")
        return sub

    @staticmethod
    def reason(sub):
        if sub.state != SubscriptionState.active:
            return (
                "Resume or activate this subscription before changing add-ons."
                if sub.state == SubscriptionState.paused
                else "Add-ons can only be changed on active subscriptions."
            )
        if sub.expiry_date and sub.expiry_date < date.today():
            return "This contract has expired. Contact your team to renew it before changing add-ons."
        if sub.next_invoice_date is None or (sub.expiry_date and sub.next_invoice_date > sub.expiry_date):
            return "There is no remaining unbilled period. Contact your team to renew this subscription."
        return None

    @staticmethod
    def snapshot(lines):
        return [
            AddonItem(
                product_id=line.product_id,
                variant_id=line.variant_id,
                name=line.product.name,
                variant_name=line.variant.name if line.variant else None,
                quantity=line.quantity,
                unit_price=line.unit_price,
            )
            for line in sorted(lines, key=lambda row: (row.product_id, row.variant_id or 0))
        ]

    def workspace(self, subscription_id, customer_id):
        sub = self.owned(subscription_id, customer_id)
        reason = self.reason(sub)
        return AddonWorkspace(
            eligible=reason is None,
            reason=reason,
            currency=sub.currency,
            effective_date=sub.next_invoice_date,
            items=self.snapshot([line for line in sub.lines if line.is_addon]),
        )

    def options(self, subscription_id, customer_id, q, paging):
        sub = self.owned(subscription_id, customer_id)
        if reason := self.reason(sub):
            raise BadRequestError(reason)
        base = select(
            Product.id.label("product_id"),
            literal(None).cast(ProductVariant.id.type).label("variant_id"),
            Product.name.label("name"),
            literal(None).cast(ProductVariant.name.type).label("variant_name"),
            Product.sales_price.label("unit_price"),
        )
        variants = (
            select(
                Product.id.label("product_id"),
                ProductVariant.id.label("variant_id"),
                Product.name.label("name"),
                ProductVariant.name.label("variant_name"),
                (Product.sales_price + ProductVariant.extra_price).label("unit_price"),
            )
            .join(ProductVariant, ProductVariant.product_id == Product.id)
            .where(ProductVariant.active.is_(True))
        )
        conditions = [
            Product.product_type == ProductType.addon,
            Product.active.is_(True),
            Product.is_recurring.is_(True),
        ]
        offers = union_all(base.where(*conditions), variants.where(*conditions)).subquery()
        # An add-on already included in the base agreement cannot be added a second time.
        contracted = exists(
            select(SubscriptionLine.id).where(
                SubscriptionLine.subscription_id == sub.id,
                SubscriptionLine.is_addon.is_(False),
                SubscriptionLine.product_id == offers.c.product_id,
                func.coalesce(SubscriptionLine.variant_id, 0) == func.coalesce(offers.c.variant_id, 0),
            )
        )
        stmt = select(offers).where(~contracted)
        if q:
            stmt = stmt.where(
                (func.lower(offers.c.name).contains(q.lower(), autoescape=True))
                | (func.lower(func.coalesce(offers.c.variant_name, "")).contains(q.lower(), autoescape=True))
            )
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = (
            self.db.execute(
                stmt.order_by(offers.c.name, offers.c.product_id, func.coalesce(offers.c.variant_id, 0))
                .limit(paging.size)
                .offset((paging.page - 1) * paging.size)
            )
            .mappings()
            .all()
        )
        ids = {row["product_id"] for row in rows}
        taxes = {pid: [] for pid in ids}
        if ids:
            for pid, tax in self.db.execute(
                select(product_taxes.c.product_id, Tax)
                .join(Tax, Tax.id == product_taxes.c.tax_id)
                .where(product_taxes.c.product_id.in_(ids), Tax.active.is_(True))
            ):
                taxes[pid].append(TaxRead.model_validate(tax))
        return Page[AddonOffer](
            items=[AddonOffer(**row, taxes=taxes[row["product_id"]]) for row in rows],
            total=total,
            page=paging.page,
            size=paging.size,
        )

    def prepare(self, sub, data):
        if reason := self.reason(sub):
            raise BadRequestError(reason)
        base = [line for line in sub.lines if not line.is_addon]
        current = [line for line in sub.lines if line.is_addon]
        base_keys = {(line.product_id, line.variant_id) for line in base}
        old = {(line.product_id, line.variant_id): line for line in current}
        # Load catalog context in batches rather than one query per selected add-on.
        new_items = [item for item in data.items if (item.product_id, item.variant_id) not in old]
        products = (
            {
                product.id: product
                for product in self.db.scalars(
                    select(Product)
                    .where(Product.id.in_({item.product_id for item in new_items}))
                    .options(selectinload(Product.taxes))
                )
            }
            if new_items
            else {}
        )
        variant_ids = {item.variant_id for item in new_items if item.variant_id is not None}
        variants = (
            {
                variant.id: variant
                for variant in self.db.scalars(
                    select(ProductVariant).where(ProductVariant.id.in_(variant_ids))
                )
            }
            if variant_ids
            else {}
        )
        proposed = []
        for item in sorted(data.items, key=lambda row: (row.product_id, row.variant_id or 0)):
            key = (item.product_id, item.variant_id)
            if key in base_keys:
                raise BadRequestError("This item is already included in the base contract")
            existing = old.get(key)
            if existing:
                product, variant = existing.product, existing.variant
                if item.quantity != existing.quantity and (
                    not product.active
                    or not product.is_recurring
                    or product.product_type != ProductType.addon
                    or (variant and not variant.active)
                ):
                    raise BadRequestError(
                        "This add-on is no longer available. Keep its current quantity or remove it."
                    )
                price = existing.unit_price
                taxes = list(existing.taxes)
                description = existing.description
            else:
                product = products.get(item.product_id)
                if (
                    product is None
                    or not product.active
                    or not product.is_recurring
                    or product.product_type != ProductType.addon
                ):
                    raise BadRequestError("Choose an active recurring add-on product")
                variant = variants.get(item.variant_id) if item.variant_id else None
                if item.variant_id and (
                    variant is None or variant.product_id != product.id or not variant.active
                ):
                    raise BadRequestError("Choose an active variant belonging to this add-on")
                price = product.sales_price + (variant.extra_price if variant else Decimal(0))
                taxes = [tax for tax in product.taxes if tax.active]
                description = variant.name if variant else product.name
            proposed.append(
                SubscriptionLine(
                    product_id=product.id,
                    variant_id=variant.id if variant else None,
                    product=product,
                    variant=variant,
                    description=description,
                    quantity=item.quantity,
                    unit_price=price,
                    taxes=taxes,
                    is_addon=True,
                    untaxed_amount=0,
                    total_amount=0,
                )
            )
        if sum(line.quantity for line in base + proposed) < sub.plan.min_quantity:
            raise BadRequestError(f"The plan requires a minimum total quantity of {sub.plan.min_quantity}")
        if [
            (l.product_id, l.variant_id, l.quantity)
            for l in sorted(current, key=lambda row: (row.product_id, row.variant_id or 0))
        ] == [(l.product_id, l.variant_id, l.quantity) for l in proposed]:
            raise BadRequestError("No add-on changes to review")
        rules = [
            discount_rule(rule) for rule in DiscountRepository(self.db).find_applicable(sub.next_invoice_date)
        ]

        def price(lines):
            return price_lines(
                [
                    LineInput(l.product_id, l.quantity, l.unit_price, tuple(tax_rule(t) for t in l.taxes))
                    for l in lines
                ],
                rules,
            )

        before = price(base + current)
        after = price(base + proposed)
        if max(after.total, after.subtotal, after.tax_total) > Decimal("9999999999.99"):
            raise BadRequestError("The proposed subscription amount exceeds the supported billing limit")
        before_items = self.snapshot(current)
        after_items = self.snapshot(proposed)
        context = {
            "subscription_id": sub.id,
            "state": sub.state,
            "next_invoice_date": sub.next_invoice_date,
            "expiry": sub.expiry_date,
            "currency": sub.currency,
            "billing_anchor": sub.billing_anchor,
            "payment_term_id": sub.payment_term_id,
            "plan": (sub.plan_id, sub.plan.billing_period, sub.plan.billing_interval, sub.plan.min_quantity),
            "before": [i.model_dump() for i in before_items],
            "after": [i.model_dump() for i in after_items],
            "lines": [
                (
                    l.id,
                    l.quantity,
                    l.unit_price,
                    [(t.id, t.rate, t.tax_type, t.is_inclusive) for t in l.taxes],
                )
                for l in sub.lines
            ],
            "pricing_before": vars(before),
            "pricing_after": vars(after),
        }
        fingerprint = hashlib.sha256(json.dumps(context, default=str, sort_keys=True).encode()).hexdigest()
        quote = AddonQuote(
            currency=sub.currency,
            effective_date=sub.next_invoice_date,
            fingerprint=fingerprint,
            before_items=before_items,
            after_items=after_items,
            before_total=before.total,
            after_total=after.total,
            delta=after.total - before.total,
            subtotal=after.subtotal,
            discount_total=after.discount_total,
            tax_total=after.tax_total,
        )
        return quote, base, proposed, after

    def preview(self, subscription_id, customer_id, data):
        return self.prepare(self.owned(subscription_id, customer_id), data)[0]

    def apply(self, subscription_id, customer_id, data: AddonApply, user: User):
        self.owned(subscription_id, customer_id)
        sub = self.subscriptions.lock(subscription_id)
        quote, base, proposed, priced = self.prepare(sub, data)
        if quote.fingerprint != data.fingerprint:
            raise ConflictError(
                "The subscription or pricing changed. Review a fresh add-on preview before confirming."
            )
        sub.lines = base + proposed
        for line, result in zip(sub.lines, priced.lines):
            line.discount_amount = result.discount
            line.untaxed_amount = result.untaxed
            line.tax_amount = result.tax
            line.total_amount = result.total
        sub.recurring_untaxed = priced.untaxed_total
        sub.recurring_tax = priced.tax_total
        sub.recurring_total = priced.total
        self.db.add(
            SubscriptionAddonChange(
                subscription_id=sub.id,
                changed_by=user.id,
                effective_date=quote.effective_date,
                before_items=[i.model_dump(mode="json") for i in quote.before_items],
                after_items=[i.model_dump(mode="json") for i in quote.after_items],
                before_total=quote.before_total,
                after_total=quote.after_total,
            )
        )
        SubscriptionService._log(
            sub,
            sub.state,
            sub.state,
            user.id,
            f"Add-ons updated for next unbilled period {quote.effective_date}; no proration",
        )
        self.db.commit()
        return self.workspace(subscription_id, customer_id)

    def history(self, subscription_id, customer_id, paging):
        self.owned(subscription_id, customer_id)
        stmt = select(SubscriptionAddonChange).where(
            SubscriptionAddonChange.subscription_id == subscription_id
        )
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = self.db.scalars(
            stmt.options(selectinload(SubscriptionAddonChange.changed_by_user))
            .order_by(SubscriptionAddonChange.id.desc())
            .limit(paging.size)
            .offset((paging.page - 1) * paging.size)
        ).all()
        return Page[AddonChangeRead](
            items=[AddonChangeRead.model_validate(row) for row in rows],
            total=total,
            page=paging.page,
            size=paging.size,
        )
