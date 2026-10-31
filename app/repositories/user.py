from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import PasswordResetToken, RefreshToken, User
from app.models.enums import UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.lower()))

    def list(self, *, role: UserRole | None, page: int, size: int) -> tuple[list[User], int]:
        stmt = select(User).order_by(User.id)
        if role:
            stmt = stmt.where(User.role == role)
        return self.paginate(stmt, page, size)


class TokenRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, token: RefreshToken | PasswordResetToken) -> None:
        self.db.add(token)
        self.db.flush()

    def get_refresh(self, token_hash: str) -> RefreshToken | None:
        return self.db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    def get_reset(self, token_hash: str) -> PasswordResetToken | None:
        return self.db.scalar(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )

    def revoke_all_refresh(self, user_id: int, at: datetime) -> None:
        self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=at)
        )
