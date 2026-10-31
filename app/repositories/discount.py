from __future__ import annotations

from datetime import date

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import selectinload

from app.models import Discount, DiscountUsage
from app.repositories.base import BaseRepository


class DiscountRepository(BaseRepository[Discount]):
    model = Discount

    def get_detail(self, discount_id: int) -> Discount | None:
        return self.db.scalar(
            select(Discount).where(Discount.id == discount_id).options(selectinload(Discount.products))
        )

    def list(self, *, active: bool | None, page: int, size: int) -> tuple[list[Discount], int]:
        stmt = select(Discount).order_by(Discount.id.desc())
        if active is not None:
            stmt = stmt.where(Discount.active == active)
        return self.paginate(stmt, page, size, options=(selectinload(Discount.products),))

    def find_applicable(self, on_date: date) -> list[Discount]:
        """Active rules valid on the date that still have uses left."""
        return list(
            self.db.scalars(
                select(Discount)
                .where(
                    Discount.active.is_(True),
                    Discount.start_date <= on_date,
                    or_(Discount.end_date.is_(None), Discount.end_date >= on_date),
                    or_(Discount.usage_limit.is_(None), Discount.used_count < Discount.usage_limit),
                )
                .options(selectinload(Discount.products))
                .order_by(Discount.id)
            )
        )

    def claim(self, discount_id: int) -> bool:
        """Atomically take one use. False if another invoice took the last one first."""
        claimed = self.db.execute(
            update(Discount)
            .where(
                Discount.id == discount_id,
                or_(Discount.usage_limit.is_(None), Discount.used_count < Discount.usage_limit),
            )
            .values(used_count=Discount.used_count + 1)
            .returning(Discount.id)
            .execution_options(synchronize_session=False)
        ).scalar()
        return claimed is not None

    def release(self, discount_id: int) -> None:
        self.db.execute(
            update(Discount)
            .where(Discount.id == discount_id)
            .values(used_count=func.greatest(Discount.used_count - 1, 0))
            .execution_options(synchronize_session=False)
        )

    def add_usage(self, usage: DiscountUsage) -> None:
        self.db.add(usage)

    def usages_for_invoice(self, invoice_id: int) -> list[DiscountUsage]:
        return list(self.db.scalars(select(DiscountUsage).where(DiscountUsage.invoice_id == invoice_id)))

    def delete_usages_for_invoice(self, invoice_id: int) -> None:
        self.db.execute(delete(DiscountUsage).where(DiscountUsage.invoice_id == invoice_id))
