"""Lead business logic.

All lead orchestration lives here, never in routers: creating a lead, listing
leads, transitioning state, and reading back a stored resume. The service depends
only on injected collaborators — a ``LeadRepository`` for the database, a
``FileStorage`` for the resume file, and an ``EmailService`` for notifications —
so it can be unit-tested with those mocked.

Create ordering & email failure behavior (per design §11 and the plan):

* The file (via ``FileStorage``) and the lead record (via ``LeadRepository``) are
  persisted FIRST; the two emails are sent AFTER.
* The service owns the transaction and commits once the record is persisted
  (commits live here, not in the repository).
* Email sends are best-effort: any send failure is caught and logged with the
  failing recipient identified (prospect or attorney), and lead creation still
  succeeds. A failed email never rolls back or fails lead creation.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import LeadState
from app.integrations.email.base import EmailMessage, EmailService
from app.integrations.email.templates import (
    attorney_notification,
    prospect_confirmation,
)
from app.integrations.storage.base import FileStorage
from app.repositories.lead_repository import LeadRepository
from app.schemas.lead import LeadCreate, LeadOut

logger = logging.getLogger(__name__)

# Light file validation, kept intentionally minimal per the design: accept only
# PDF/DOC/DOCX and cap the size. No name/email over-validation here (email is
# already validated at the schema boundary via ``EmailStr``).
ALLOWED_RESUME_EXTENSIONS = {".pdf", ".doc", ".docx"}
MAX_RESUME_SIZE_BYTES = 5 * 1024 * 1024


class LeadValidationError(Exception):
    """Base class for lead input validation failures."""


class InvalidFileTypeError(LeadValidationError):
    """Raised when an uploaded resume is not a PDF, DOC, or DOCX."""


class FileTooLargeError(LeadValidationError):
    """Raised when an uploaded resume exceeds the size cap."""


class LeadNotFoundError(Exception):
    """Raised when a referenced lead does not exist."""

    def __init__(self, lead_id: int) -> None:
        super().__init__(f"Lead {lead_id} not found")
        self.lead_id = lead_id


@dataclass(frozen=True)
class ResumeFile:
    """A stored resume ready to be served: raw bytes + display metadata.

    Returned by :meth:`LeadService.read_resume` so the resume endpoint (Task 10)
    can stream the file with the correct original filename and content type.
    """

    content: bytes
    original_name: str
    content_type: str


class LeadService:
    def __init__(
        self,
        *,
        session: Session,
        lead_repository: LeadRepository,
        file_storage: FileStorage,
        email_service: EmailService,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._leads = lead_repository
        self._storage = file_storage
        self._email = email_service
        self._settings = settings or get_settings()

    def create(
        self,
        data: LeadCreate,
        *,
        content: bytes,
        original_name: str,
        content_type: str,
    ) -> LeadOut:
        self._validate_resume(original_name=original_name, content=content)

        # Persist first: file, then record, then commit (the service owns the
        # transaction). Only after the lead is durable do we attempt emails.
        stored = self._storage.save(content=content, original_name=original_name)
        lead = self._leads.create(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            resume_path=stored.key,
            resume_original_name=original_name,
            resume_content_type=content_type,
            resume_size=stored.size,
        )
        self._session.commit()

        self._send_notifications(
            first_name=data.first_name,
            last_name=data.last_name,
            prospect_email=data.email,
        )

        return LeadOut.model_validate(lead)

    def list_all(self) -> list[LeadOut]:
        return [LeadOut.model_validate(lead) for lead in self._leads.list_all()]

    def update_state(self, lead_id: int, state: LeadState) -> LeadOut:
        lead = self._leads.update_state(lead_id, state)
        if lead is None:
            raise LeadNotFoundError(lead_id)
        self._session.commit()
        return LeadOut.model_validate(lead)

    def read_resume(self, lead_id: int) -> ResumeFile:
        lead = self._leads.get_by_id(lead_id)
        if lead is None:
            raise LeadNotFoundError(lead_id)
        content = self._storage.read(lead.resume_path)
        return ResumeFile(
            content=content,
            original_name=lead.resume_original_name,
            content_type=lead.resume_content_type,
        )

    def _validate_resume(self, *, original_name: str, content: bytes) -> None:
        extension = Path(original_name).suffix.lower()
        if extension not in ALLOWED_RESUME_EXTENSIONS:
            raise InvalidFileTypeError(
                f"Unsupported resume type '{extension or original_name}'; "
                "allowed types are PDF, DOC, DOCX."
            )
        if len(content) > MAX_RESUME_SIZE_BYTES:
            raise FileTooLargeError(
                f"Resume is {len(content)} bytes; the maximum is "
                f"{MAX_RESUME_SIZE_BYTES} bytes (5MB)."
            )

    def _send_notifications(
        self, *, first_name: str, last_name: str, prospect_email: str
    ) -> None:
        self._send_best_effort(
            "prospect",
            prospect_confirmation(first_name=first_name, to_email=prospect_email),
        )
        self._send_best_effort(
            "attorney",
            attorney_notification(
                attorney_email=self._settings.seed_attorney_email,
                first_name=first_name,
                last_name=last_name,
                prospect_email=prospect_email,
            ),
        )

    def _send_best_effort(self, recipient_role: str, message: EmailMessage) -> None:
        try:
            self._email.send(message)
        except Exception:
            # Best-effort: a failed email must never roll back or fail lead
            # creation. Log which recipient failed and carry on.
            logger.exception(
                "Failed to send %s email to %s", recipient_role, message.to
            )
