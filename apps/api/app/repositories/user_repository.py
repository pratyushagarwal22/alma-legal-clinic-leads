"""Data access for the attorney ``User``.

The repository layer is the ONLY layer that queries the database. It holds plain
data-access methods with no business logic and does not manage transactions
(commits are the service layer's responsibility per the design's layering rules).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: int) -> User | None:
        return self._session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self._session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
