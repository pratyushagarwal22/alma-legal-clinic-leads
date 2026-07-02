"""Tests for the ``AuthService`` (Task 8).

All login logic lives in the service, not in routers. The service authenticates
the seeded attorney against ``UserRepository`` and issues a JWT. On bad
credentials it raises a single domain error that never reveals whether the email
or the password was the problem.

These tests exercise the service against the throwaway test Postgres (the
``db_session`` fixture from ``conftest.py``); the attorney is created in-test to
stand in for the seeded user. Requires ``docker compose up -d db``.
"""

import pytest

from app.core.config import Settings
from app.core.security import decode_access_token, hash_password
from app.db.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import AuthService, InvalidCredentialsError

ATTORNEY_EMAIL = "attorney@example.com"
ATTORNEY_PASSWORD = "correct-horse-battery-staple"

# Hermetic settings with a strong secret so the tests do not depend on .env and
# do not trip PyJWT's short-key warning.
TEST_SETTINGS = Settings(
    jwt_secret="test-secret-that-is-comfortably-long-enough-32b",
    jwt_algorithm="HS256",
    jwt_access_token_expires_minutes=60,
)


def _seed_attorney(db_session) -> User:
    user = User(
        email=ATTORNEY_EMAIL,
        hashed_password=hash_password(ATTORNEY_PASSWORD),
    )
    db_session.add(user)
    db_session.flush()
    return user


def _service(db_session) -> AuthService:
    return AuthService(UserRepository(db_session), settings=TEST_SETTINGS)


def test_valid_credentials_return_decodable_jwt_for_seeded_attorney(db_session):
    attorney = _seed_attorney(db_session)
    service = _service(db_session)

    token = service.login(
        LoginRequest(email=ATTORNEY_EMAIL, password=ATTORNEY_PASSWORD)
    )

    assert isinstance(token, TokenResponse)
    assert token.token_type == "bearer"

    claims = decode_access_token(token.access_token, settings=TEST_SETTINGS)
    assert claims["sub"] == str(attorney.id)


def test_wrong_password_raises_invalid_credentials(db_session):
    _seed_attorney(db_session)
    service = _service(db_session)

    with pytest.raises(InvalidCredentialsError):
        service.login(LoginRequest(email=ATTORNEY_EMAIL, password="wrong-password"))


def test_unknown_email_raises_invalid_credentials(db_session):
    _seed_attorney(db_session)
    service = _service(db_session)

    with pytest.raises(InvalidCredentialsError):
        service.login(
            LoginRequest(email="nobody@example.com", password=ATTORNEY_PASSWORD)
        )


def test_error_message_does_not_reveal_which_field_was_wrong(db_session):
    _seed_attorney(db_session)
    service = _service(db_session)

    with pytest.raises(InvalidCredentialsError) as wrong_password:
        service.login(LoginRequest(email=ATTORNEY_EMAIL, password="wrong-password"))
    with pytest.raises(InvalidCredentialsError) as unknown_email:
        service.login(
            LoginRequest(email="nobody@example.com", password=ATTORNEY_PASSWORD)
        )

    # Both failure modes must produce an identical, generic message so the
    # caller cannot distinguish an unknown email from a wrong password.
    assert str(wrong_password.value) == str(unknown_email.value)
    message = str(wrong_password.value).lower()
    for leak in ("not found", "no such", "unknown", "does not exist", "no user"):
        assert leak not in message
