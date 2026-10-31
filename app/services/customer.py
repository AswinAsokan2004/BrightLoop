from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models import Customer, PaymentTerm
from app.repositories.customer import CustomerRepository, PaymentTermRepository
from app.schemas.common import PageParams
from app.schemas.customer import CustomerCreate, CustomerUpdate, PaymentTermCreate
from app.services.common import apply_updates


class CustomerService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.customers = CustomerRepository(db)
        self.payment_terms = PaymentTermRepository(db)

    def create(self, data: CustomerCreate) -> Customer:
        customer = self.customers.add(Customer(**data.model_dump()))
        self.db.commit()
        return customer

    def get(self, customer_id: int) -> Customer:
        customer = self.customers.get(customer_id)
        if customer is None:
            raise NotFoundError("Customer not found")
        return customer

    def list(self, q: str | None, params: PageParams) -> tuple[list[Customer], int]:
        return self.customers.list(q=q, page=params.page, size=params.size)

    def update(self, customer_id: int, data: CustomerUpdate) -> Customer:
        customer = self.get(customer_id)
        apply_updates(customer, data)
        self.db.commit()
        return customer

    def delete(self, customer_id: int) -> None:
        customer = self.get(customer_id)
        try:
            self.customers.delete(customer)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("Customer has subscriptions, invoices or a portal login and cannot be deleted") from exc

    # --- Payment terms -------------------------------------------------------

    def list_payment_terms(self) -> list[PaymentTerm]:
        return self.payment_terms.list()

    def create_payment_term(self, data: PaymentTermCreate) -> PaymentTerm:
        term = self.payment_terms.add(PaymentTerm(**data.model_dump()))
        self.db.commit()
        return term
