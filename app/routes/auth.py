from fastapi import APIRouter, BackgroundTasks, Request, status

from app.core.email import send_email
from app.routes.deps import CurrentUser, DbSession
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenPair,
)
from app.schemas.common import Message
from app.schemas.user import UserRead
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


def _client(request: Request) -> tuple[str | None, str | None]:
    return request.headers.get("user-agent"), request.client.host if request.client else None


@router.post("/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def signup(data: SignupRequest, db: DbSession):
    """Create a customer account. Staff accounts are created by an admin under /users/staff."""
    return AuthService(db).signup(data)


@router.post("/login", response_model=TokenPair)
def login(data: LoginRequest, request: Request, db: DbSession):
    return AuthService(db).login(data.email, data.password, *_client(request))


@router.post("/refresh", response_model=TokenPair)
def refresh(data: RefreshRequest, request: Request, db: DbSession):
    return AuthService(db).refresh(data.refresh_token, *_client(request))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(data: RefreshRequest, db: DbSession) -> None:
    AuthService(db).logout(data.refresh_token)


@router.post("/forgot-password", response_model=Message)
def forgot_password(data: ForgotPasswordRequest, background: BackgroundTasks, db: DbSession):
    email = AuthService(db).forgot_password(data.email)
    if email is not None:
        background.add_task(send_email, email)
    return Message(message="If that email is registered, a reset link is on its way.")


@router.post("/reset-password", response_model=Message)
def reset_password(data: ResetPasswordRequest, db: DbSession):
    AuthService(db).reset_password(data.token, data.new_password)
    return Message(message="Password updated. Please log in again.")


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser):
    return user
