from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import Product, ProductAttribute, ProductAttributeValue, ProductVariant, Tax, User
from app.models.enums import ProductType
from app.repositories.catalog import (
    AttributeRepository,
    AttributeValueRepository,
    ProductRepository,
    TaxRepository,
    VariantRepository,
)
from app.schemas.catalog import (
    AttributeCreate,
    AttributeValueCreate,
    AttributeValueUpdate,
    ProductCreate,
    ProductUpdate,
    TaxCreate,
    TaxUpdate,
    VariantCreate,
    VariantUpdate,
)
from app.schemas.common import PageParams
from app.services.common import apply_updates


class CatalogService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.variants = VariantRepository(db)
        self.attributes = AttributeRepository(db)
        self.attribute_values = AttributeValueRepository(db)
        self.taxes = TaxRepository(db)

    # --- Taxes ---------------------------------------------------------------

    def list_taxes(self, active: bool | None) -> list[Tax]:
        return self.taxes.list(active=active)

    def create_tax(self, data: TaxCreate) -> Tax:
        tax = self.taxes.add(Tax(**data.model_dump()))
        self.db.commit()
        return tax

    def update_tax(self, tax_id: int, data: TaxUpdate) -> Tax:
        tax = self.taxes.get(tax_id)
        if tax is None:
            raise NotFoundError("Tax not found")
        apply_updates(tax, data)
        self.db.commit()
        return tax

    def load_taxes(self, tax_ids: Sequence[int]) -> list[Tax]:
        taxes = self.taxes.get_many(tax_ids)
        missing = set(tax_ids) - {t.id for t in taxes}
        if missing:
            raise BadRequestError(f"Unknown tax ids: {sorted(missing)}")
        return taxes

    # --- Products ------------------------------------------------------------

    def list_products(
        self, q: str | None, product_type: ProductType | None, active: bool | None, params: PageParams
    ) -> tuple[list[Product], int]:
        return self.products.list(
            q=q, product_type=product_type, active=active, page=params.page, size=params.size
        )

    def get_product(self, product_id: int) -> Product:
        product = self.products.get_detail(product_id)
        if product is None:
            raise NotFoundError("Product not found")
        return product

    def create_product(self, data: ProductCreate, user: User) -> Product:
        product = self.products.add(
            Product(
                **data.model_dump(exclude={"tax_ids"}),
                taxes=self.load_taxes(data.tax_ids),
                created_by=user.id,
            )
        )
        self.db.commit()
        return self.get_product(product.id)

    def update_product(self, product_id: int, data: ProductUpdate) -> Product:
        product = self.get_product(product_id)
        apply_updates(product, data, exclude={"tax_ids"})
        if data.tax_ids is not None:
            product.taxes = self.load_taxes(data.tax_ids)
        self.db.commit()
        return self.get_product(product_id)

    def delete_product(self, product_id: int) -> None:
        product = self.get_product(product_id)
        try:
            self.products.delete(product)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("Product is used by subscriptions or invoices; deactivate it instead") from exc

    def resolve_item(
        self, product_id: int, variant_id: int | None
    ) -> tuple[Product, ProductVariant | None, Decimal]:
        """Validate a product (and optional variant) for a line; return its default unit price."""
        product = self.products.get(product_id)
        if product is None or not product.active:
            raise BadRequestError(f"Product {product_id} does not exist or is inactive")
        if variant_id is None:
            return product, None, product.sales_price

        variant = self.variants.get(variant_id)
        if variant is None or variant.product_id != product.id or not variant.active:
            raise BadRequestError(f"Variant {variant_id} is not an active variant of product {product_id}")
        return product, variant, product.sales_price + variant.extra_price

    # --- Attributes ----------------------------------------------------------

    def list_attributes(self) -> list[ProductAttribute]:
        return self.attributes.list()

    def create_attribute(self, data: AttributeCreate) -> ProductAttribute:
        attribute = self.attributes.add(
            ProductAttribute(
                name=data.name,
                values=[ProductAttributeValue(**value.model_dump()) for value in data.values],
            )
        )
        self.db.commit()
        return self.attributes.get_detail(attribute.id)

    def add_attribute_value(self, attribute_id: int, data: AttributeValueCreate) -> ProductAttributeValue:
        if self.attributes.get(attribute_id) is None:
            raise NotFoundError("Attribute not found")
        value = self.attribute_values.add(ProductAttributeValue(attribute_id=attribute_id, **data.model_dump()))
        self.db.commit()
        return value

    def update_attribute_value(self, value_id: int, data: AttributeValueUpdate) -> ProductAttributeValue:
        value = self.attribute_values.get(value_id)
        if value is None:
            raise NotFoundError("Attribute value not found")
        apply_updates(value, data)
        if data.extra_price is not None:
            self.db.flush()
            # Keep each variant's cached extra price in sync
            for variant in self.variants.using_attribute_value(value_id):
                variant.extra_price = sum((v.extra_price for v in variant.attribute_values), Decimal(0))
        self.db.commit()
        return value

    # --- Variants ------------------------------------------------------------

    def create_variant(self, product_id: int, data: VariantCreate) -> ProductVariant:
        product = self.get_product(product_id)
        values = self.attribute_values.get_many(data.attribute_value_ids)
        missing = set(data.attribute_value_ids) - {v.id for v in values}
        if missing:
            raise BadRequestError(f"Unknown attribute value ids: {sorted(missing)}")
        if len({v.attribute_id for v in values}) != len(values):
            raise BadRequestError("Pick at most one value per attribute")

        variant = self.variants.add(
            ProductVariant(
                product_id=product.id,
                sku=data.sku,
                name=data.name or f"{product.name} ({', '.join(v.value for v in values)})",
                extra_price=sum((v.extra_price for v in values), Decimal(0)),
                attribute_values=values,
            )
        )
        self.db.commit()
        return self.variants.get_detail(variant.id)

    def update_variant(self, variant_id: int, data: VariantUpdate) -> ProductVariant:
        variant = self.variants.get_detail(variant_id)
        if variant is None:
            raise NotFoundError("Variant not found")
        apply_updates(variant, data)
        self.db.commit()
        return variant
