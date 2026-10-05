"""Create an admin account after migration using environment-provided credentials.

Set ADMIN_EMAIL, ADMIN_PASSWORD, and optionally ADMIN_DISPLAY_NAME before running:
python -m app.utils.bootstrap_admin
"""

import os

from sqlalchemy import select

from app.core.security import hash_password
from app.database.session import get_session_factory
from app.models.user import Role, User
from app.schemas.auth import RegisterRequest


def main() -> None:
    if not os.environ.get("DATABASE_URL") and os.environ.get("POSTGRES_HOST"):
        from app.utils.container_start import configure_database
        configure_database()
    data = RegisterRequest(
        email=os.environ["ADMIN_EMAIL"],
        password=os.environ["ADMIN_PASSWORD"],
        display_name=os.environ.get("ADMIN_DISPLAY_NAME", "Administrator"),
    )
    email = str(data.email).lower()
    with get_session_factory()() as db:
        if db.scalar(select(User.id).where(User.email == email)) is not None:
            raise SystemExit("That email already belongs to an account; admin was not created.")
        role = db.scalar(select(Role).where(Role.name == "admin"))
        if role is None:
            role = Role(name="admin")
            db.add(role)
            db.flush()
        db.add(
            User(
                email=email,
                password_hash=hash_password(data.password),
                display_name=data.display_name,
                role_id=role.id,
            )
        )
        db.commit()
    print("Admin account created. Credentials were not printed.")


if __name__ == "__main__":
    main()
