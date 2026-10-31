from fastapi import APIRouter, status

from app.routes.deps import AdminUser, DbSession, Paging, StaffUser
from app.schemas.common import Page, to_page
from app.schemas.discount import DiscountCreate, DiscountRead, DiscountUpdate
from app.services.discount import DiscountService

router = APIRouter(prefix="/discounts", tags=["Discounts"])


@router.get("", response_model=Page[DiscountRead])
def list_discounts(_: StaffUser, db: DbSession, paging: Paging, active: bool | None = None):
    items, total = DiscountService(db).list(active, paging)
    return to_page(DiscountRead, items, total, paging)


@router.post("", response_model=DiscountRead, status_code=status.HTTP_201_CREATED)
def create_discount(data: DiscountCreate, admin: AdminUser, db: DbSession):
    """Only the admin can create discount rules."""
    return DiscountService(db).create(data, admin)


@router.get("/{discount_id}", response_model=DiscountRead)
def get_discount(discount_id: int, _: StaffUser, db: DbSession):
    return DiscountService(db).get(discount_id)


@router.patch("/{discount_id}", response_model=DiscountRead)
def update_discount(discount_id: int, data: DiscountUpdate, _: AdminUser, db: DbSession):
    return DiscountService(db).update(discount_id, data)


@router.delete("/{discount_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_discount(discount_id: int, _: AdminUser, db: DbSession) -> None:
    DiscountService(db).delete(discount_id)
