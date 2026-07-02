"""Fixtures for the API integration tests (Task 10).

These tests drive the real FastAPI app end-to-end with a ``TestClient`` against
the throwaway test Postgres (the ``db_session`` fixture from the top-level
``conftest.py``). Only two collaborators are swapped for hermetic, deterministic
runs:

* ``get_db`` is overridden to hand the request the test's transactional session,
  so data created in a test is visible to the endpoint and vice versa, and
  everything is rolled back afterwards.
* ``get_email_service`` is overridden with an in-memory capturing transport so
  email dispatch can be asserted without a live SMTP server (design §12).
* ``get_file_storage`` is pointed at a per-test temp directory so uploaded
  resumes never touch the developer's ``uploads/`` folder.

Everything else (routers, services, repositories, JWT decoding, real Postgres)
runs unmodified.
"""

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.db.models import User
from app.integrations.email.base import EmailMessage, EmailService
from app.integrations.storage.local import LocalFileStorage
from app.main import create_app

ATTORNEY_EMAIL = "attorney@example.com"
ATTORNEY_PASSWORD = "correct-horse-battery-staple"

# Hermetic settings with a strong secret so the tests do not depend on .env and
# do not trip PyJWT's short-key warning. Token issue (AuthService) and decode
# (get_current_attorney) both resolve settings via ``get_settings``, so a single
# override keeps them consistent.
TEST_SETTINGS = Settings(jwt_secret="test-secret-that-is-comfortably-long-enough-32b")


class CapturingEmailService(EmailService):
    """In-memory ``EmailService`` that records every message it is asked to send."""

    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


@pytest.fixture()
def email_service() -> CapturingEmailService:
    return CapturingEmailService()


@pytest.fixture()
def uploads_dir(tmp_path):
    return tmp_path / "uploads"


@pytest.fixture()
def client(db_session, email_service, uploads_dir) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    app.dependency_overrides[deps.get_db] = lambda: db_session
    app.dependency_overrides[deps.get_email_service] = lambda: email_service
    app.dependency_overrides[deps.get_file_storage] = lambda: LocalFileStorage(
        uploads_dir
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def attorney(db_session) -> User:
    """Seed the single attorney into the test DB (stands in for the seed script)."""
    user = User(
        email=ATTORNEY_EMAIL,
        hashed_password=hash_password(ATTORNEY_PASSWORD),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def token(client, attorney) -> str:
    response = client.post(
        "/auth/login",
        json={"email": ATTORNEY_EMAIL, "password": ATTORNEY_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture()
def auth_headers(token) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
