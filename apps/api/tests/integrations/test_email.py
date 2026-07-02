"""Tests for the ``EmailService`` integration.

Two layers are covered:

* Template builders (``prospect_confirmation`` / ``attorney_notification``) are
  pure functions with no I/O, so they are tested directly.
* The SMTP implementation is exercised against a running Mailpit container: a
  message is sent over SMTP (``SMTP_HOST``/``SMTP_PORT``) and then read back via
  Mailpit's HTTP API to confirm delivery. If Mailpit is unreachable the SMTP test
  is skipped rather than failing (``docker compose up -d mailpit`` to run it).
"""

import json
import os
import urllib.error
import urllib.request

import pytest

from app.core.config import get_settings
from app.integrations.email.base import EmailMessage
from app.integrations.email.smtp import SmtpEmailService
from app.integrations.email.templates import (
    attorney_notification,
    prospect_confirmation,
)

MAILPIT_API_URL = os.getenv("MAILPIT_API_URL", "http://localhost:8025")


def test_prospect_confirmation_is_addressed_to_the_prospect():
    message = prospect_confirmation(first_name="Ada", to_email="ada@example.com")

    assert isinstance(message, EmailMessage)
    assert message.to == "ada@example.com"
    assert "Ada" in message.body
    assert message.subject


def test_attorney_notification_carries_prospect_details():
    message = attorney_notification(
        attorney_email="attorney@example.com",
        first_name="Ada",
        last_name="Lovelace",
        prospect_email="ada@example.com",
    )

    assert message.to == "attorney@example.com"
    assert "Ada" in message.body
    assert "Lovelace" in message.body
    assert "ada@example.com" in message.body
    assert message.subject


def _mailpit_reachable() -> bool:
    try:
        urllib.request.urlopen(f"{MAILPIT_API_URL}/api/v1/messages", timeout=2)
        return True
    except (urllib.error.URLError, OSError):
        return False


def _clear_mailpit() -> None:
    request = urllib.request.Request(
        f"{MAILPIT_API_URL}/api/v1/messages", method="DELETE"
    )
    urllib.request.urlopen(request, timeout=5)


def _mailpit_messages() -> list[dict]:
    with urllib.request.urlopen(
        f"{MAILPIT_API_URL}/api/v1/messages", timeout=5
    ) as response:
        payload = json.loads(response.read())
    return payload.get("messages", [])


def test_smtp_send_delivers_message_to_mailpit():
    if not _mailpit_reachable():
        pytest.skip("Mailpit not reachable; run `docker compose up -d mailpit`")

    _clear_mailpit()

    service = SmtpEmailService.from_settings(get_settings())
    message = prospect_confirmation(
        first_name="Grace", to_email="grace@example.com"
    )
    service.send(message)

    delivered = _mailpit_messages()
    assert len(delivered) == 1
    received = delivered[0]
    assert received["Subject"] == message.subject
    assert any(to["Address"] == "grace@example.com" for to in received["To"])
