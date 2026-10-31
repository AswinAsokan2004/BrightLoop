"""Create the first admin account (sign-up only ever creates customers).

    uv run python -m app.scripts.create_admin --name "Riya Menon" --email admin@brightloop.com
"""

import argparse
import getpass
import sys

from app.core.database import SessionLocal
from app.core.security import check_password_strength, hash_password
from app.models import User
from app.models.enums import UserRole
from app.repositories.user import UserRepository


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", help="Prompted for if omitted")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Password: ")
    try:
        check_password_strength(password)
    except ValueError as exc:
        sys.exit(str(exc))

    with SessionLocal() as db:
        users = UserRepository(db)
        email = args.email.lower()
        user = users.get_by_email(email)
        if user is None:
            users.add(User(name=args.name, email=email, password_hash=hash_password(password), role=UserRole.admin))
            print(f"Created admin {email}")
        else:
            # Lets you claim a seeded account (e.g. admin@brightloop.com) by setting a real password
            user.name, user.role, user.is_active = args.name, UserRole.admin, True
            user.password_hash = hash_password(password)
            print(f"Updated {email}: now an admin with the new password")
        db.commit()


if __name__ == "__main__":
    main()
