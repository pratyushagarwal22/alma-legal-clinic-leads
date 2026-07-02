"""Tests for the ``LeadService`` (Task 9).

All lead business logic lives in the service. Per design §12 and the plan, these
are unit tests: the repository, file storage, and email service are mocked, so
the tests exercise the service's orchestration, ordering, validation, and
best-effort email behavior in isolation (no database, disk, or SMTP required).
"""

import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock

import pytest

from app.core.config import Settings
from app.db.models import Lead, LeadState
from app.integrations.email.base import EmailMessage, EmailService
from app.integrations.storage.base import FileStorage, StoredFile
from app.repositories.lead_repository import LeadRepository
from app.schemas.lead import LeadCreate, LeadOut
from app.services.lead_service import (
    FileTooLargeError,
    InvalidFileTypeError,
    LeadNotFoundError,
    LeadService,
    ResumeFile,
)

ATTORNEY_EMAIL = "attorney@example.com"
PROSPECT_EMAIL = "ada@example.com"

TEST_SETTINGS = Settings(seed_attorney_email=ATTORNEY_EMAIL)

PDF_BYTES = b"%PDF-1.4 fake resume bytes"


def _make_lead(
    *,
    lead_id: int = 1,
    first_name: str = "Ada",
    last_name: str = "Lovelace",
    email: str = PROSPECT_EMAIL,
    state: LeadState = LeadState.PENDING,
    resume_path: str = "stored-key-abc123.pdf",
    resume_original_name: str = "resume.pdf",
    resume_content_type: str = "application/pdf",
    resume_size: int = len(PDF_BYTES),
) -> Lead:
    """Build a fully-populated ``Lead`` as the repository would return it.

    Server-side defaults (id, timestamps) are set explicitly since the object is
    never flushed to a real database in these unit tests.
    """
    lead = Lead(
        first_name=first_name,
        last_name=last_name,
        email=email,
        resume_path=resume_path,
        resume_original_name=resume_original_name,
        resume_content_type=resume_content_type,
        resume_size=resume_size,
    )
    lead.id = lead_id
    lead.state = state
    lead.created_at = datetime(2026, 7, 1, tzinfo=timezone.utc)
    lead.updated_at = datetime(2026, 7, 1, tzinfo=timezone.utc)
    return lead


def _build_service(
    *,
    session=None,
    repo=None,
    storage=None,
    email=None,
    created_lead: Lead | None = None,
):
    session = session or MagicMock()
    repo = repo or MagicMock(spec=LeadRepository)
    storage = storage or MagicMock(spec=FileStorage)
    email = email or MagicMock(spec=EmailService)

    repo.create.return_value = created_lead or _make_lead()
    storage.save.return_value = StoredFile(key="stored-key-abc123.pdf", size=len(PDF_BYTES))

    service = LeadService(
        session=session,
        lead_repository=repo,
        file_storage=storage,
        email_service=email,
        settings=TEST_SETTINGS,
    )
    return service, session, repo, storage, email


def _create(service, *, original_name="resume.pdf", content=PDF_BYTES, content_type="application/pdf"):
    return service.create(
        LeadCreate(first_name="Ada", last_name="Lovelace", email=PROSPECT_EMAIL),
        content=content,
        original_name=original_name,
        content_type=content_type,
    )


# --- create: persistence + both emails ------------------------------------


def test_create_stores_file_and_record_then_sends_both_emails():
    service, session, repo, storage, email = _build_service()

    manager = Mock()
    manager.attach_mock(storage.save, "save")
    manager.attach_mock(repo.create, "create")
    manager.attach_mock(session.commit, "commit")
    manager.attach_mock(email.send, "send")

    result = _create(service)

    # File persisted via storage with the uploaded bytes/name.
    storage.save.assert_called_once_with(content=PDF_BYTES, original_name="resume.pdf")

    # Record persisted via the repository with the stored key + metadata.
    assert repo.create.call_count == 1
    kwargs = repo.create.call_args.kwargs
    assert kwargs["first_name"] == "Ada"
    assert kwargs["last_name"] == "Lovelace"
    assert kwargs["email"] == PROSPECT_EMAIL
    assert kwargs["resume_path"] == "stored-key-abc123.pdf"
    assert kwargs["resume_original_name"] == "resume.pdf"
    assert kwargs["resume_content_type"] == "application/pdf"
    assert kwargs["resume_size"] == len(PDF_BYTES)

    # Service owns the transaction: it commits.
    session.commit.assert_called_once()

    # Both emails sent, to the prospect and the attorney.
    assert email.send.call_count == 2
    recipients = {call.args[0].to for call in email.send.call_args_list}
    assert recipients == {PROSPECT_EMAIL, ATTORNEY_EMAIL}
    assert all(isinstance(call.args[0], EmailMessage) for call in email.send.call_args_list)

    # Ordering: persistence (commit) happens BEFORE any email is sent.
    call_names = [name for name, _, _ in manager.mock_calls]
    assert call_names.index("commit") < call_names.index("send")

    assert isinstance(result, LeadOut)


# --- file validation: only PDF/DOC/DOCX up to 5MB ---------------------------


@pytest.mark.parametrize("original_name", ["resume.pdf", "resume.doc", "resume.docx", "RESUME.PDF"])
def test_create_accepts_pdf_doc_docx(original_name):
    service, _session, repo, storage, _email = _build_service()

    _create(service, original_name=original_name)

    storage.save.assert_called_once()
    repo.create.assert_called_once()


@pytest.mark.parametrize("original_name", ["resume.txt", "resume.exe", "resume.png", "resume"])
def test_create_rejects_disallowed_file_types(original_name):
    service, session, repo, storage, email = _build_service()

    with pytest.raises(InvalidFileTypeError):
        _create(service, original_name=original_name)

    # Nothing is persisted or emailed when validation fails.
    storage.save.assert_not_called()
    repo.create.assert_not_called()
    session.commit.assert_not_called()
    email.send.assert_not_called()


def test_create_accepts_file_at_the_5mb_cap():
    service, _session, _repo, storage, _email = _build_service()
    content = b"%PDF-" + b"x" * (5 * 1024 * 1024 - 5)  # exactly 5 MiB

    _create(service, content=content)

    storage.save.assert_called_once()


def test_create_rejects_file_over_5mb():
    service, session, repo, storage, email = _build_service()
    content = b"%PDF-" + b"x" * (5 * 1024 * 1024)  # one byte over 5 MiB

    with pytest.raises(FileTooLargeError):
        _create(service, content=content)

    storage.save.assert_not_called()
    repo.create.assert_not_called()
    session.commit.assert_not_called()
    email.send.assert_not_called()


# --- email failure is best-effort ------------------------------------------


def test_create_succeeds_and_logs_when_prospect_email_fails(caplog):
    service, session, repo, storage, email = _build_service()

    def _fail_prospect(message: EmailMessage) -> None:
        if message.to == PROSPECT_EMAIL:
            raise RuntimeError("smtp down")

    email.send.side_effect = _fail_prospect

    with caplog.at_level(logging.ERROR):
        result = _create(service)

    # Lead still created and committed despite the email failure.
    repo.create.assert_called_once()
    session.commit.assert_called_once()
    session.rollback.assert_not_called()

    # Both sends still attempted; a failure of one does not skip the other.
    assert email.send.call_count == 2

    # Success is still returned.
    assert isinstance(result, LeadOut)

    # The failing recipient (prospect) is identified in the logs.
    assert "prospect" in caplog.text.lower()


def test_create_succeeds_and_logs_when_attorney_email_fails(caplog):
    service, session, repo, storage, email = _build_service()

    def _fail_attorney(message: EmailMessage) -> None:
        if message.to == ATTORNEY_EMAIL:
            raise RuntimeError("smtp down")

    email.send.side_effect = _fail_attorney

    with caplog.at_level(logging.ERROR):
        result = _create(service)

    repo.create.assert_called_once()
    session.commit.assert_called_once()
    session.rollback.assert_not_called()
    assert isinstance(result, LeadOut)
    assert "attorney" in caplog.text.lower()


# --- list ------------------------------------------------------------------


def test_list_all_returns_lead_out_records():
    service, _session, repo, _storage, _email = _build_service()
    repo.list_all.return_value = [
        _make_lead(lead_id=1, email="a@example.com"),
        _make_lead(lead_id=2, email="b@example.com"),
    ]

    result = service.list_all()

    assert len(result) == 2
    assert all(isinstance(item, LeadOut) for item in result)
    assert [item.id for item in result] == [1, 2]


# --- update state ----------------------------------------------------------


def test_update_state_moves_pending_to_reached_out():
    service, session, repo, _storage, _email = _build_service()
    repo.update_state.return_value = _make_lead(state=LeadState.REACHED_OUT)

    result = service.update_state(1, LeadState.REACHED_OUT)

    repo.update_state.assert_called_once_with(1, LeadState.REACHED_OUT)
    session.commit.assert_called_once()
    assert result.state == LeadState.REACHED_OUT


def test_update_state_raises_when_lead_missing():
    service, _session, repo, _storage, _email = _build_service()
    repo.update_state.return_value = None

    with pytest.raises(LeadNotFoundError):
        service.update_state(999, LeadState.REACHED_OUT)


# --- read resume -----------------------------------------------------------


def test_read_resume_returns_bytes_filename_and_content_type():
    service, _session, repo, storage, _email = _build_service()
    repo.get_by_id.return_value = _make_lead(
        resume_path="stored-key.pdf",
        resume_original_name="my-cv.pdf",
        resume_content_type="application/pdf",
    )
    storage.read.return_value = b"the-real-bytes"

    resume = service.read_resume(1)

    storage.read.assert_called_once_with("stored-key.pdf")
    assert isinstance(resume, ResumeFile)
    assert resume.content == b"the-real-bytes"
    assert resume.original_name == "my-cv.pdf"
    assert resume.content_type == "application/pdf"


def test_read_resume_raises_when_lead_missing():
    service, _session, repo, _storage, _email = _build_service()
    repo.get_by_id.return_value = None

    with pytest.raises(LeadNotFoundError):
        service.read_resume(999)


# --- LeadOut does not leak internal fields ---------------------------------


def test_lead_out_excludes_internal_fields_and_includes_resume_display_fields():
    lead = _make_lead(
        resume_path="secret/stored-key-abc123.pdf",
        resume_original_name="resume.pdf",
        resume_content_type="application/pdf",
    )

    dumped = LeadOut.model_validate(lead).model_dump()

    # No stored file path/key and no hashed values leak out.
    assert "resume_path" not in dumped
    assert "resume_key" not in dumped
    assert "hashed_password" not in dumped
    for key in dumped:
        assert "path" not in key.lower()
        assert "key" not in key.lower()
        assert "hash" not in key.lower()
    assert "secret/stored-key-abc123.pdf" not in str(dumped)

    # What the UI needs is present, including filename + content type.
    assert dumped["resume_original_name"] == "resume.pdf"
    assert dumped["resume_content_type"] == "application/pdf"


# --- LeadCreate rejects invalid emails at the boundary ----------------------


def test_lead_create_rejects_invalid_email():
    with pytest.raises(Exception):
        LeadCreate(first_name="Ada", last_name="Lovelace", email="not-an-email")
