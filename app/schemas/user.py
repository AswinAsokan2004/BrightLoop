from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import UserRole
from app.schemas.auth import Password
from app.schemas.common import Email, ORMModel


class UserRead(ORMModel):
    id: int
    name: str
    email: str
    role: UserRole
    customer_id: int | None
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime


class StaffCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: Email
    password: Password


class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    is_active: bool | None = None
