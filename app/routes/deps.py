from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_access_token
from app.models import User
from app.models.enums import UserRole
from app.repositories.user import UserRepository
from app.schemas.common import PageParams

DbSession = Annotated[Session, Depends(get_db)]
Paging = Annotated[PageParams, Depends()]

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise AuthenticationError("Not authenticated")
    user = UserRepository(db).get(decode_access_token(credentials.credentials))
    if user is None or not user.is_active:
        raise AuthenticationError("Account not found or disabled")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    def check(user: CurrentUser) -> User:
        if user.role not in roles:
            raise PermissionDeniedError("You don't have permission to do this")
        return user

    return check


# Admin: whole system. Staff: day-to-day work. Customer: own data through the portal.
AdminUser = Annotated[User, Depends(require_roles(UserRole.admin))]
StaffUser = Annotated[User, Depends(require_roles(UserRole.admin, UserRole.staff))]
CustomerUser = Annotated[User, Depends(require_roles(UserRole.customer))]


def get_customer_id(user: CustomerUser) -> int:
    if user.customer_id is None:
        raise PermissionDeniedError("This login is not linked to a customer")
    return user.customer_id


PortalCustomerId = Annotated[int, Depends(get_customer_id)]
