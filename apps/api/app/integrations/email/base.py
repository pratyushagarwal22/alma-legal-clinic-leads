"""Email integration interface.

Email is an integration behind an interface so implementations (SMTP -> Mailpit
now, a hosted provider later) can be swapped without touching business logic. Per
the design's layering rules this is called only from the service layer, never from
routers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

DEFAULT_SENDER = "no-reply@legalclinic.example"


@dataclass(frozen=True)
class EmailMessage:
    """A single plain-text email to be delivered.

    ``to`` is the recipient address, ``subject`` and ``body`` the content, and
    ``sender`` the From address (defaulted so callers need only supply it when it
    differs).
    """

    to: str
    subject: str
    body: str
    sender: str = DEFAULT_SENDER


class EmailService(ABC):
    """Interface for delivering an :class:`EmailMessage`."""

    @abstractmethod
    def send(self, message: EmailMessage) -> None:
        """Deliver ``message`` to its recipient."""
