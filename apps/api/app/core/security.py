"""Password hashing and JWT helpers.

Central place for credential handling so no other layer implements its own.
Password hashing is backed by passlib's bcrypt scheme; verification handles
legacy hashes via ``deprecated="auto"`` should the scheme ever change. JWTs are
signed/verified with the symmetric secret and algorithm from ``Settings`` so the
token format can evolve without touching business logic.
"""

from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import Settings, get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str | int,
    *,
    settings: Settings | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Issue a signed JWT whose ``sub`` claim identifies the authenticated user.

    ``iat`` and ``exp`` are included so tokens expire; expiry defaults to
    ``Settings.jwt_access_token_expires_minutes``.
    """
    settings = settings or get_settings()
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        or timedelta(minutes=settings.jwt_access_token_expires_minutes)
    )
    payload = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(
    token: str, *, settings: Settings | None = None
) -> dict:
    """Verify a JWT's signature and expiry, returning its claims.

    Raises ``jwt.PyJWTError`` (e.g. ``ExpiredSignatureError``,
    ``InvalidTokenError``) if the token is invalid.
    """
    settings = settings or get_settings()
    return jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
