"""SMTP implementation of the ``EmailService`` interface, targeting Mailpit.

The client is built from ``Settings`` (``smtp_host`` / ``smtp_port``) which point
at the Mailpit container in development. Mailpit accepts unauthenticated,
plaintext SMTP, so no TLS or login is performed. Only the opaque interface is
meant to be consumed by the service layer.
"""

import smtplib
from email.message import EmailMessage as MimeMessage

from app.core.config import Settings, get_settings
from app.integrations.email.base import EmailMessage, EmailService


class SmtpEmailService(EmailService):
    def __init__(self, *, host: str, port: int) -> None:
        self._host = host
        self._port = port

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "SmtpEmailService":
        settings = settings or get_settings()
        return cls(host=settings.smtp_host, port=settings.smtp_port)

    def send(self, message: EmailMessage) -> None:
        mime = MimeMessage()
        mime["From"] = message.sender
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.body)
        with smtplib.SMTP(self._host, self._port) as client:
            client.send_message(mime)
