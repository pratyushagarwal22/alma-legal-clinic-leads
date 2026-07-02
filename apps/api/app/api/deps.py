"""FastAPI dependency wiring for the HTTP layer.

This module is the single place where the object graph is assembled: it opens a
DB session per request, builds the repositories from that session, constructs the
integration adapters (file storage, email) from settings, and hands services
their injected collaborators. Routers depend only on the services and the
``get_current_attorney`` guard defined here — they never build these themselves.

Keeping construction here (rather than in routers) preserves the layering: swap a
collaborator (e.g. an S3 ``FileStorage`` or a hosted ``EmailService``) by changing
one factory, with no router or service edits.
"""

from collections.abc import Iterator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import SessionLocal
from app.integrations.email.base import EmailService
from app.integrations.email.smtp import SmtpEmailService
from app.integrations.storage.base import FileStorage
from app.integrations.storage.local import LocalFileStorage
from app.repositories.lead_repository import LeadRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.lead_service import LeadService

# ``auto_error=False`` so a missing/blank Authorization header yields ``None``
# here instead of a framework-default 403; the guard then raises a consistent
# 401 itself.
_bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Iterator[Session]:
    """Yield a database session and guarantee it is closed after the request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_user_repository(session: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(session)


def get_lead_repository(session: Session = Depends(get_db)) -> LeadRepository:
    return LeadRepository(session)


def get_file_storage(settings: Settings = Depends(get_settings)) -> FileStorage:
    return LocalFileStorage(settings.uploads_dir)


def get_email_service(settings: Settings = Depends(get_settings)) -> EmailService:
    return SmtpEmailService.from_settings(settings)


def get_auth_service(
    users: UserRepository = Depends(get_user_repository),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(users, settings=settings)


def get_lead_service(
    session: Session = Depends(get_db),
    leads: LeadRepository = Depends(get_lead_repository),
    storage: FileStorage = Depends(get_file_storage),
    email: EmailService = Depends(get_email_service),
    settings: Settings = Depends(get_settings),
) -> LeadService:
    return LeadService(
        session=session,
        lead_repository=leads,
        file_storage=storage,
        email_service=email,
        settings=settings,
    )


def get_current_attorney(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    users: UserRepository = Depends(get_user_repository),
    settings: Settings = Depends(get_settings),
) -> User:
    """Authenticate the bearer token and return the attorney, or raise 401.

    A missing header, an unverifiable/expired token, or a token whose subject no
    longer maps to a user all fail identically with a generic 401 so the endpoint
    reveals nothing beyond "you are not authenticated".
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        claims = decode_access_token(credentials.credentials, settings=settings)
    except jwt.PyJWTError as exc:
        raise unauthorized from exc

    subject = claims.get("sub")
    if subject is None:
        raise unauthorized

    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise unauthorized from exc

    user = users.get_by_id(user_id)
    if user is None:
        raise unauthorized
    return user
