from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Product, ProductAttribute, ProductAttributeValue, ProductVariant, Tax
from app.models.catalog import variant_attribute_values
from app.models.enums import ProductType
from app.repositories.base import BaseRepository

_PRODUCT_DETAIL = (
    selectinload(Product.taxes),
    selectinload(Product.variants).selectinload(ProductVariant.attribute_values),
)


class ProductRepository(BaseRepository[Product]):
    model = Product

    def get_detail(self, product_id: int) -> Product | None:
        return self.db.scalar(select(Product).where(Product.id == product_id).options(*_PRODUCT_DETAIL))

    def list(
        self,
        *,
        q: str | None,
        product_type: ProductType | None,
        active: bool | None,
        page: int,
        size: int,
    ) -> tuple[list[Product], int]:
        stmt = select(Product).order_by(Product.name, Product.id)
        if q:
            stmt = stmt.where(Product.name.ilike(f"%{q}%"))
        if product_type:
            stmt = stmt.where(Product.product_type == product_type)
        if active is not None:
            stmt = stmt.where(Product.active == active)
        return self.paginate(stmt, page, size, options=_PRODUCT_DETAIL)


class VariantRepository(BaseRepository[ProductVariant]):
    model = ProductVariant

    def get_detail(self, variant_id: int) -> ProductVariant | None:
        return self.db.scalar(
            select(ProductVariant)
            .where(ProductVariant.id == variant_id)
            .options(selectinload(ProductVariant.attribute_values), selectinload(ProductVariant.product))
        )

    def using_attribute_value(self, attribute_value_id: int) -> list[ProductVariant]:
        return list(
            self.db.scalars(
                select(ProductVariant)
                .join(variant_attribute_values)
                .where(variant_attribute_values.c.attribute_value_id == attribute_value_id)
                .options(selectinload(ProductVariant.attribute_values))
            )
        )


class AttributeRepository(BaseRepository[ProductAttribute]):
    model = ProductAttribute

    def get_detail(self, attribute_id: int) -> ProductAttribute | None:
        return self.db.scalar(
            select(ProductAttribute)
            .where(ProductAttribute.id == attribute_id)
            .options(selectinload(ProductAttribute.values))
        )

    def list(self) -> list[ProductAttribute]:
        return list(
            self.db.scalars(
                select(ProductAttribute)
                .order_by(ProductAttribute.name)
                .options(selectinload(ProductAttribute.values))
            )
        )


class AttributeValueRepository(BaseRepository[ProductAttributeValue]):
    model = ProductAttributeValue


class TaxRepository(BaseRepository[Tax]):
    model = Tax

    def list(self, *, active: bool | None) -> list[Tax]:
        stmt = select(Tax).order_by(Tax.name)
        if active is not None:
            stmt = stmt.where(Tax.active == active)
        return list(self.db.scalars(stmt))
