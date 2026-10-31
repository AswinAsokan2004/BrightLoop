from fastapi import APIRouter, status

from app.models.enums import UserRole
from app.routes.deps import AdminUser, DbSession, Paging
from app.schemas.common import Page, to_page
from app.schemas.user import StaffCreate, UserRead, UserUpdate
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/staff", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_staff(data: StaffCreate, admin: AdminUser, db: DbSession):
    """Only the admin can add a new member of staff."""
    return UserService(db).create_staff(data, admin)


@router.get("", response_model=Page[UserRead])
def list_users(_: AdminUser, db: DbSession, paging: Paging, role: UserRole | None = None):
    items, total = UserService(db).list(role, paging)
    return to_page(UserRead, items, total, paging)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, _: AdminUser, db: DbSession):
    return UserService(db).get(user_id)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: int, data: UserUpdate, admin: AdminUser, db: DbSession):
    return UserService(db).update(user_id, data, admin)
