"""Idempotent seed for the single attorney user.

Reads ``SEED_ATTORNEY_EMAIL`` / ``SEED_ATTORNEY_PASSWORD`` from settings and
creates the attorney only if a user with that email does not already exist.
Running this repeatedly never creates a duplicate.

Run with: ``python -m app.db.seed``
"""

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import User
from app.db.session import SessionLocal


def seed_attorney() -> None:
    settings = get_settings()
    email = settings.seed_attorney_email
    password = settings.seed_attorney_password

    with SessionLocal() as session:
        existing = session.query(User).filter(User.email == email).first()
        if existing is not None:
            print(f"Attorney already exists (id={existing.id}, email={email}); skipping insert.")
            return

        user = User(email=email, hashed_password=hash_password(password))
        session.add(user)
        session.commit()
        session.refresh(user)
        print(f"Seeded attorney (id={user.id}, email={email}).")


if __name__ == "__main__":
    seed_attorney()
