from app.db.models import User
from app.repositories.user_repository import UserRepository


def test_get_by_email_and_id_round_trip(db_session):
    user = User(email="attorney@example.com", hashed_password="not-a-real-hash")
    db_session.add(user)
    db_session.flush()

    repo = UserRepository(db_session)

    by_email = repo.get_by_email("attorney@example.com")
    assert by_email is not None
    assert by_email.id == user.id

    by_id = repo.get_by_id(user.id)
    assert by_id is not None
    assert by_id.email == "attorney@example.com"


def test_get_missing_returns_none(db_session):
    repo = UserRepository(db_session)
    assert repo.get_by_email("nobody@example.com") is None
    assert repo.get_by_id(999999) is None
