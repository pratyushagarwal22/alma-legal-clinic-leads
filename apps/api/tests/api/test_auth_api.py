"""Integration tests for the auth router (Task 10).

The router is thin: it parses the credentials, calls ``AuthService.login``, and
returns the token. On bad credentials the service raises a domain error that maps
to a single generic 401 which never reveals whether the email or the password was
wrong (no user enumeration). Requires ``docker compose up -d db``.
"""

from tests.api.conftest import ATTORNEY_EMAIL, ATTORNEY_PASSWORD


def test_login_with_valid_credentials_returns_bearer_token(client, attorney):
    response = client.post(
        "/auth/login",
        json={"email": ATTORNEY_EMAIL, "password": ATTORNEY_PASSWORD},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and body["access_token"]


def test_wrong_password_returns_generic_401(client, attorney):
    response = client.post(
        "/auth/login",
        json={"email": ATTORNEY_EMAIL, "password": "definitely-wrong"},
    )

    assert response.status_code == 401


def test_unknown_email_returns_generic_401(client, attorney):
    response = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": ATTORNEY_PASSWORD},
    )

    assert response.status_code == 401


def test_wrong_password_and_unknown_email_are_indistinguishable(client, attorney):
    wrong_password = client.post(
        "/auth/login",
        json={"email": ATTORNEY_EMAIL, "password": "definitely-wrong"},
    )
    unknown_email = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": ATTORNEY_PASSWORD},
    )

    # Identical status AND identical body: a caller cannot tell which was wrong.
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
