"""Auth router — thin HTTP layer over ``AuthService``.

The endpoint only parses the credentials, delegates to the service, and returns
the token DTO. All authentication logic lives in the service; a failed login
raises ``InvalidCredentialsError``, mapped centrally in ``main.py`` to a single
generic 401 (no user enumeration).
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_auth_service
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    credentials: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return auth_service.login(credentials)
