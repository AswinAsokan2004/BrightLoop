from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from app.core.security import check_password_strength
from app.schemas.common import Email

Password = Annotated[str, Field(max_length=72), AfterValidator(check_password_strength)]


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: Email
    password: Password
    company_name: str | None = Field(None, max_length=150)
    phone: str | None = Field(None, max_length=30)


class LoginRequest(BaseModel):
    email: Email
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: Email


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: Password
