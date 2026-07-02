"""Auth request/response DTOs.

Kept minimal per scope: a login request carrying the attorney's credentials and
a bearer-token response. Email is a plain string (no ``EmailStr``) to avoid an
extra dependency; the credential lookup happens in the service layer.
"""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
