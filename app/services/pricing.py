"""Pure pricing maths shared by subscriptions (preview) and invoices (final).

Calculation order, applied to every line:
  1. subtotal = quantity x unit price   (unit price = product price + variant extras)
  2. minus discounts                    -> untaxed amount
  3. taxes on the discounted amount     -> tax amount
  4. total = untaxed + tax;  document totals are sums of the lines
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.models.enums import DiscountScope, DiscountType, TaxType

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
HUNDRED = Decimal(100)


def money(value: Decimal | int) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class TaxRule:
    id: int
    name: str
    tax_type: TaxType
    rate: Decimal
    is_inclusive: bool = False


@dataclass(frozen=True)
class DiscountRule:
    id: int
    discount_type: DiscountType
    value: Decimal
    scope: DiscountScope
    min_purchase_amount: Decimal = ZERO
    min_quantity: int = 0
    product_ids: frozenset[int] = frozenset()


@dataclass(frozen=True)
class LineInput:
    product_id: int
    quantity: int
    unit_price: Decimal
    taxes: tuple[TaxRule, ...] = ()


@dataclass(frozen=True)
class LineTax:
    tax: TaxRule
    amount: Decimal


@dataclass
class LineResult:
    subtotal: Decimal
    discount: Decimal
    untaxed: Decimal
    tax: Decimal
    total: Decimal
    taxes: list[LineTax] = field(default_factory=list)


@dataclass
class PricingResult:
    lines: list[LineResult]
    discounts: dict[int, Decimal]  # discount id -> amount it took off
    subtotal: Decimal
    discount_total: Decimal
    untaxed_total: Decimal
    tax_total: Decimal
    total: Decimal


def tax_rule(tax: Any) -> TaxRule:
    return TaxRule(tax.id, tax.name, tax.tax_type, tax.rate, tax.is_inclusive)


def discount_rule(discount: Any) -> DiscountRule:
    return DiscountRule(
        id=discount.id,
        discount_type=discount.discount_type,
        value=discount.value,
        scope=discount.scope,
        min_purchase_amount=discount.min_purchase_amount or ZERO,
        min_quantity=discount.min_quantity or 0,
        product_ids=frozenset(p.id for p in discount.products),
    )


def allocate_discounts(
    lines: Sequence[LineInput], rules: Sequence[DiscountRule]
) -> tuple[list[Decimal], dict[int, Decimal]]:
    """Return the discount for each line and the total each rule applied."""
    gross = [money(line.quantity * line.unit_price) for line in lines]
    per_line = [ZERO for _ in lines]
    applied: dict[int, Decimal] = {}

    for rule in rules:
        targets = [
            i for i, line in enumerate(lines)
            if rule.scope == DiscountScope.subscription or line.product_id in rule.product_ids
        ]
        base = sum((gross[i] for i in targets), ZERO)
        quantity = sum(lines[i].quantity for i in targets)
        if base <= 0 or quantity < rule.min_quantity or base < rule.min_purchase_amount:
            continue

        if rule.discount_type == DiscountType.percent:
            amounts = [money(gross[i] * rule.value / HUNDRED) for i in targets]
        else:
            amounts = _spread(min(money(rule.value), base), [gross[i] for i in targets])

        # Never discount a line below zero when several rules stack
        amounts = [min(amount, gross[i] - per_line[i]) for amount, i in zip(amounts, targets)]
        total = sum(amounts, ZERO)
        if total <= 0:
            continue
        for amount, i in zip(amounts, targets):
            per_line[i] += amount
        applied[rule.id] = total

    return per_line, applied


def _spread(amount: Decimal, weights: list[Decimal]) -> list[Decimal]:
    """Split a fixed amount across lines in proportion to their value; rounding goes to the last line."""
    total_weight = sum(weights, ZERO)
    shares = [money(amount * weight / total_weight) for weight in weights[:-1]]
    shares.append(amount - sum(shares, ZERO))
    return shares


def compute_taxes(untaxed: Decimal, quantity: int, taxes: Sequence[TaxRule]) -> tuple[Decimal, list[LineTax]]:
    """Return (net amount, taxes). Inclusive percent taxes are extracted from the price."""
    inclusive = [t for t in taxes if t.is_inclusive and t.tax_type == TaxType.percent]
    inclusive_rate = sum((t.rate for t in inclusive), Decimal(0))
    net = money(untaxed * HUNDRED / (HUNDRED + inclusive_rate)) if inclusive_rate else untaxed

    result = []
    for tax in taxes:
        if tax.tax_type == TaxType.fixed:
            amount = money(tax.rate * quantity)
        else:
            amount = money(net * tax.rate / HUNDRED)
        result.append(LineTax(tax, amount))

    if inclusive:
        # Keep net + inclusive taxes exactly equal to the original price
        net = untaxed - sum((lt.amount for lt in result if lt.tax in inclusive), ZERO)
    return net, result


def price_lines(lines: Sequence[LineInput], rules: Sequence[DiscountRule] = ()) -> PricingResult:
    line_discounts, applied = allocate_discounts(lines, rules)

    results = []
    for line, discount in zip(lines, line_discounts):
        subtotal = money(line.quantity * line.unit_price)
        untaxed, taxes = compute_taxes(subtotal - discount, line.quantity, line.taxes)
        tax = sum((t.amount for t in taxes), ZERO)
        results.append(LineResult(subtotal, discount, untaxed, tax, untaxed + tax, taxes))

    return PricingResult(
        lines=results,
        discounts=applied,
        subtotal=sum((r.subtotal for r in results), ZERO),
        discount_total=sum((r.discount for r in results), ZERO),
        untaxed_total=sum((r.untaxed for r in results), ZERO),
        tax_total=sum((r.tax for r in results), ZERO),
        total=sum((r.total for r in results), ZERO),
    )
