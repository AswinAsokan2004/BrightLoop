from __future__ import annotations

from sqlalchemy import or_, select

from app.models import Customer, PaymentTerm
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    model = Customer

    def list(self, *, q: str | None, page: int, size: int) -> tuple[list[Customer], int]:
        stmt = select(Customer).order_by(Customer.name, Customer.id)
        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(
                or_(
                    Customer.name.ilike(pattern),
                    Customer.company_name.ilike(pattern),
                    Customer.email.ilike(pattern),
                )
            )
        return self.paginate(stmt, page, size)


class PaymentTermRepository(BaseRepository[PaymentTerm]):
    model = PaymentTerm

    def list(self) -> list[PaymentTerm]:
        return list(self.db.scalars(select(PaymentTerm).order_by(PaymentTerm.due_days)))
