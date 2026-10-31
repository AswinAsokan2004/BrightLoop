from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import Discount, Product, User
from app.models.enums import DiscountScope, DiscountType
from app.repositories.catalog import ProductRepository
from app.repositories.discount import DiscountRepository
from app.schemas.common import PageParams
from app.schemas.discount import DiscountCreate, DiscountUpdate
from app.services.common import apply_updates


class DiscountService:
    """Admin-managed discount rules. They are applied automatically by the billing engine."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.discounts = DiscountRepository(db)
        self.products = ProductRepository(db)

    def list(self, active: bool | None, params: PageParams) -> tuple[list[Discount], int]:
        return self.discounts.list(active=active, page=params.page, size=params.size)

    def get(self, discount_id: int) -> Discount:
        discount = self.discounts.get_detail(discount_id)
        if discount is None:
            raise NotFoundError("Discount not found")
        return discount

    def create(self, data: DiscountCreate, admin: User) -> Discount:
        discount = self.discounts.add(
            Discount(
                **data.model_dump(exclude={"product_ids"}),
                products=self._load_products(data.product_ids),
                created_by=admin.id,
            )
        )
        self.db.commit()
        return self.get(discount.id)

    def update(self, discount_id: int, data: DiscountUpdate) -> Discount:
        discount = self.get(discount_id)
        apply_updates(discount, data, exclude={"product_ids"})
        if data.product_ids is not None:
            discount.products = self._load_products(data.product_ids)

        if discount.discount_type == DiscountType.percent and discount.value > 100:
            raise BadRequestError("A percentage discount cannot exceed 100")
        if discount.end_date and discount.end_date < discount.start_date:
            raise BadRequestError("end_date must be on or after start_date")
        if discount.scope == DiscountScope.product and not discount.products:
            raise BadRequestError("Product-scoped discounts need at least one product")
        self.db.commit()
        return self.get(discount_id)

    def delete(self, discount_id: int) -> None:
        discount = self.get(discount_id)
        try:
            self.discounts.delete(discount)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("Discount has already been used on invoices; deactivate it instead") from exc

    def _load_products(self, product_ids: Sequence[int]) -> list[Product]:
        products = self.products.get_many(product_ids)
        missing = set(product_ids) - {p.id for p in products}
        if missing:
            raise BadRequestError(f"Unknown product ids: {sorted(missing)}")
        return products
