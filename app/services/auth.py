from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import OutgoingEmail
from app.core.exceptions import AuthenticationError, BadRequestError, ConflictError
from app.core.security import (
    create_access_token,
    hash_password,
    hash_token,
    new_opaque_token,
    utcnow,
    verify_password,
)
from app.models import Customer, PasswordResetToken, RefreshToken, User
from app.models.enums import UserRole
from app.repositories.customer import CustomerRepository
from app.repositories.user import TokenRepository, UserRepository
from app.schemas.auth import SignupRequest, TokenPair


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.tokens = TokenRepository(db)
        self.customers = CustomerRepository(db)

    def signup(self, data: SignupRequest) -> User:
        """Public sign-up always creates a customer account, never staff or admin."""
        if self.users.get_by_email(data.email):
            raise ConflictError("An account with this email already exists")

        customer = self.customers.add(
            Customer(
                name=data.company_name or data.name,
                company_name=data.company_name,
                email=data.email,
                phone=data.phone,
            )
        )
        user = self.users.add(
            User(
                name=data.name,
                email=data.email,
                password_hash=hash_password(data.password),
                role=UserRole.customer,
                customer_id=customer.id,
            )
        )
        self.db.commit()
        return user

    def login(self, email: str, password: str, user_agent: str | None, ip_address: str | None) -> TokenPair:
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("This account is disabled")

        user.last_login_at = utcnow()
        tokens = self._issue_tokens(user, user_agent, ip_address)
        self.db.commit()
        return tokens

    def refresh(self, refresh_token: str, user_agent: str | None, ip_address: str | None) -> TokenPair:
        stored = self.tokens.get_refresh(hash_token(refresh_token))
        if stored is None or stored.revoked_at is not None or stored.expires_at <= utcnow():
            raise AuthenticationError("Invalid or expired refresh token")
        user = self.users.get(stored.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Invalid or expired refresh token")

        stored.revoked_at = utcnow()  # rotate: each refresh token works once
        tokens = self._issue_tokens(user, user_agent, ip_address)
        self.db.commit()
        return tokens

    def logout(self, refresh_token: str) -> None:
        stored = self.tokens.get_refresh(hash_token(refresh_token))
        if stored is not None and stored.revoked_at is None:
            stored.revoked_at = utcnow()
            self.db.commit()

    def forgot_password(self, email: str) -> OutgoingEmail | None:
        """Returns the email to send, or None. The API answers the same either way (no account enumeration)."""
        user = self.users.get_by_email(email)
        if user is None or not user.is_active:
            return None

        raw, token_hash = new_opaque_token()
        self.tokens.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=utcnow() + timedelta(minutes=settings.password_reset_minutes),
            )
        )
        self.db.commit()

        link = f"{settings.frontend_url}/reset-password?token={raw}"
        return OutgoingEmail(
            to=user.email,
            subject="Reset your Brightloop password",
            body=(
                f"Hi {user.name},\n\n"
                f"Use this link to choose a new password:\n{link}\n\n"
                f"It expires in {settings.password_reset_minutes} minutes and works once. "
                "If you didn't ask for this, you can ignore this email."
            ),
        )

    def reset_password(self, token: str, new_password: str) -> None:
        stored = self.tokens.get_reset(hash_token(token))
        now = utcnow()
        if stored is None or stored.used_at is not None or stored.expires_at <= now:
            raise BadRequestError("This reset link is invalid or has expired")

        user = self.users.get(stored.user_id)
        if user is None or not user.is_active:
            raise BadRequestError("This reset link is invalid or has expired")

        user.password_hash = hash_password(new_password)
        stored.used_at = now
        self.tokens.revoke_all_refresh(user.id, now)  # sign out every device
        self.db.commit()

    def _issue_tokens(self, user: User, user_agent: str | None, ip_address: str | None) -> TokenPair:
        raw, token_hash = new_opaque_token()
        self.tokens.add(
            RefreshToken(
                user_id=user.id,
                token_hash=token_hash,
                user_agent=user_agent[:255] if user_agent else None,
                ip_address=ip_address,
                expires_at=utcnow() + timedelta(days=settings.refresh_token_days),
            )
        )
        return TokenPair(
            access_token=create_access_token(user.id, user.role),
            refresh_token=raw,
            expires_in=settings.access_token_minutes * 60,
        )
