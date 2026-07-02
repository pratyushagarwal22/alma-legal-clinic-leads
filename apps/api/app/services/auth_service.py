"""Authentication business logic.

All login logic lives here, never in routers. The service looks the attorney up
via ``UserRepository``, verifies the supplied password against the stored hash,
and issues a JWT. On any failure it raises :class:`InvalidCredentialsError` with a
single generic message so callers cannot tell whether the email or the password
was wrong (no user enumeration).
"""

from app.core.config import Settings, get_settings
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse

# A valid bcrypt hash of an arbitrary password, produced once with the same
# hashing context as real passwords. When no user matches the email we still run
# a full bcrypt verification against this hash, so an unknown email costs the
# same time as a wrong password and cannot be distinguished by timing (no
# user-enumeration side channel).
_DUMMY_PASSWORD_HASH = hash_password("dummy-password-never-used-for-login")


class InvalidCredentialsError(Exception):
    """Raised when authentication fails for any reason.

    The message is deliberately generic and identical for both an unknown email
    and a wrong password, so it never reveals which was incorrect.
    """

    def __init__(self, message: str = "Invalid email or password") -> None:
        super().__init__(message)


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        *,
        settings: Settings | None = None,
    ) -> None:
        self._users = user_repository
        self._settings = settings or get_settings()

    def login(self, credentials: LoginRequest) -> TokenResponse:
        user = self._users.get_by_email(credentials.email)
        # Always run one real bcrypt verification, even when the user is unknown
        # (against a dummy hash), so both failure paths take the same time.
        hashed_password = (
            user.hashed_password if user is not None else _DUMMY_PASSWORD_HASH
        )
        password_ok = verify_password(credentials.password, hashed_password)
        if user is None or not password_ok:
            raise InvalidCredentialsError()

        token = create_access_token(user.id, settings=self._settings)
        return TokenResponse(access_token=token)
