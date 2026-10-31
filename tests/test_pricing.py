from decimal import Decimal

from app.models.enums import DiscountScope, DiscountType, TaxType
from app.services.pricing import DiscountRule, LineInput, TaxRule, price_lines

GST = TaxRule(1, "GST 18%", TaxType.percent, Decimal("18"))
CRM, STORAGE = 1, 2


def test_brightloop_sample_invoice():
    """5 seats x 1760 (Odoo variant), 10% volume discount, GST 18% -> 9345.60."""
    volume = DiscountRule(1, DiscountType.percent, Decimal("10"), DiscountScope.product,
                          min_quantity=5, product_ids=frozenset({CRM}))
    result = price_lines([LineInput(CRM, 5, Decimal("1760"), (GST,))], [volume])

    assert result.subtotal == Decimal("8800.00")
    assert result.discount_total == Decimal("880.00")
    assert result.untaxed_total == Decimal("7920.00")
    assert result.tax_total == Decimal("1425.60")
    assert result.total == Decimal("9345.60")
    assert result.discounts == {1: Decimal("880.00")}


def test_min_quantity_not_met_skips_discount():
    volume = DiscountRule(1, DiscountType.percent, Decimal("10"), DiscountScope.product,
                          min_quantity=5, product_ids=frozenset({CRM}))
    result = price_lines([LineInput(CRM, 4, Decimal("1760"))], [volume])
    assert result.discount_total == Decimal("0.00")
    assert result.discounts == {}


def test_product_discount_only_touches_matching_lines():
    rule = DiscountRule(1, DiscountType.percent, Decimal("50"), DiscountScope.product,
                        product_ids=frozenset({STORAGE}))
    result = price_lines([LineInput(CRM, 1, Decimal("1000")), LineInput(STORAGE, 1, Decimal("300"))], [rule])
    assert [line.discount for line in result.lines] == [Decimal("0.00"), Decimal("150.00")]


def test_fixed_subscription_discount_is_spread_and_sums_exactly():
    rule = DiscountRule(1, DiscountType.fixed, Decimal("100"), DiscountScope.subscription)
    result = price_lines(
        [LineInput(CRM, 1, Decimal("1")), LineInput(STORAGE, 1, Decimal("1")), LineInput(3, 1, Decimal("1"))],
        [rule],
    )
    # Capped at the 3.00 order value, and the split adds up to the cent
    assert result.discount_total == Decimal("3.00")
    assert sum(line.discount for line in result.lines) == Decimal("3.00")


def test_discounts_never_push_a_line_below_zero():
    big = DiscountRule(1, DiscountType.percent, Decimal("80"), DiscountScope.subscription)
    bigger = DiscountRule(2, DiscountType.percent, Decimal("80"), DiscountScope.subscription)
    result = price_lines([LineInput(CRM, 1, Decimal("100"))], [big, bigger])
    assert result.lines[0].discount == Decimal("100.00")
    assert result.total == Decimal("0.00")


def test_min_purchase_amount():
    rule = DiscountRule(1, DiscountType.fixed, Decimal("50"), DiscountScope.subscription,
                        min_purchase_amount=Decimal("1000"))
    assert price_lines([LineInput(CRM, 1, Decimal("999"))], [rule]).discount_total == 0
    assert price_lines([LineInput(CRM, 1, Decimal("1000"))], [rule]).discount_total == Decimal("50.00")


def test_inclusive_tax_is_extracted_from_price():
    inclusive = TaxRule(2, "GST 18% incl.", TaxType.percent, Decimal("18"), is_inclusive=True)
    result = price_lines([LineInput(CRM, 1, Decimal("118"), (inclusive,))])
    assert result.untaxed_total == Decimal("100.00")
    assert result.tax_total == Decimal("18.00")
    assert result.total == Decimal("118.00")


def test_fixed_tax_is_per_unit():
    cess = TaxRule(3, "Cess", TaxType.fixed, Decimal("2.5"))
    result = price_lines([LineInput(CRM, 4, Decimal("10"), (cess,))])
    assert result.tax_total == Decimal("10.00")
