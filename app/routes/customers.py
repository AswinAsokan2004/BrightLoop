from fastapi import APIRouter, status

from app.routes.deps import AdminUser, CurrentUser, DbSession, Paging, StaffUser
from app.schemas.common import Page, to_page
from app.schemas.customer import (
    CustomerCreate,
    CustomerRead,
    CustomerUpdate,
    PaymentTermCreate,
    PaymentTermRead,
)
from app.services.customer import CustomerService

router = APIRouter(tags=["Customers"])


@router.get("/customers", response_model=Page[CustomerRead])
def list_customers(_: StaffUser, db: DbSession, paging: Paging, q: str | None = None):
    items, total = CustomerService(db).list(q, paging)
    return to_page(CustomerRead, items, total, paging)


@router.post("/customers", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(data: CustomerCreate, _: StaffUser, db: DbSession):
    return CustomerService(db).create(data)


@router.get("/customers/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, _: StaffUser, db: DbSession):
    return CustomerService(db).get(customer_id)


@router.patch("/customers/{customer_id}", response_model=CustomerRead)
def update_customer(customer_id: int, data: CustomerUpdate, _: StaffUser, db: DbSession):
    return CustomerService(db).update(customer_id, data)


@router.delete("/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: int, _: AdminUser, db: DbSession) -> None:
    CustomerService(db).delete(customer_id)


@router.get("/payment-terms", response_model=list[PaymentTermRead])
def list_payment_terms(_: CurrentUser, db: DbSession):
    return CustomerService(db).list_payment_terms()


@router.post("/payment-terms", response_model=PaymentTermRead, status_code=status.HTTP_201_CREATED)
def create_payment_term(data: PaymentTermCreate, _: AdminUser, db: DbSession):
    return CustomerService(db).create_payment_term(data)
