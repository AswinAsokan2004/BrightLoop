from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.security import hash_password, utcnow
from app.models import User
from app.models.enums import UserRole
from app.repositories.user import TokenRepository, UserRepository
from app.schemas.common import PageParams
from app.schemas.user import StaffCreate, UserUpdate
from app.services.common import apply_updates


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.tokens = TokenRepository(db)

    def create_staff(self, data: StaffCreate, admin: User) -> User:
        if self.users.get_by_email(data.email):
            raise ConflictError("An account with this email already exists")
        user = self.users.add(
            User(
                name=data.name,
                email=data.email,
                password_hash=hash_password(data.password),
                role=UserRole.staff,
                created_by=admin.id,
            )
        )
        self.db.commit()
        return user

    def get(self, user_id: int) -> User:
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    def list(self, role: UserRole | None, params: PageParams) -> tuple[list[User], int]:
        return self.users.list(role=role, page=params.page, size=params.size)

    def update(self, user_id: int, data: UserUpdate, admin: User) -> User:
        user = self.get(user_id)
        if user.id == admin.id and data.is_active is False:
            raise BadRequestError("You cannot deactivate your own account")
        apply_updates(user, data)
        if data.is_active is False:
            self.tokens.revoke_all_refresh(user.id, utcnow())
        self.db.commit()
        return user
