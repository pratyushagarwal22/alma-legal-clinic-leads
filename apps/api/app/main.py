"""FastAPI application factory, router registration, and error mapping.

Domain exceptions raised by the service layer are translated to HTTP status codes
here, in one place, so routers stay thin (they never catch/translate). The auth
failure is deliberately mapped to a single generic 401 that reveals nothing about
which field was wrong.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routers import auth, health, leads
from app.core.config import get_settings
from app.services.auth_service import InvalidCredentialsError
from app.services.lead_service import LeadNotFoundError, LeadValidationError


def create_app() -> FastAPI:
    """Application factory: build the FastAPI app, register routers and errors."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(leads.router)

    _register_exception_handlers(app)

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidCredentialsError)
    async def _invalid_credentials(
        _request: Request, _exc: InvalidCredentialsError
    ) -> JSONResponse:
        # Generic, fixed body for every auth failure: no user enumeration.
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid email or password"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(LeadNotFoundError)
    async def _lead_not_found(
        _request: Request, exc: LeadNotFoundError
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(LeadValidationError)
    async def _lead_validation(
        _request: Request, exc: LeadValidationError
    ) -> JSONResponse:
        # Covers InvalidFileTypeError / FileTooLargeError (subclasses).
        return JSONResponse(status_code=400, content={"detail": str(exc)})


app = create_app()
