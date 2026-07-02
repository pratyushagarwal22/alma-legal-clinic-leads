from app.db.models import LeadState
from app.repositories.lead_repository import LeadRepository


def _make_lead(repo: LeadRepository, *, email: str = "prospect@example.com"):
    return repo.create(
        first_name="Ada",
        last_name="Lovelace",
        email=email,
        resume_path="uploads/abc123.pdf",
        resume_original_name="resume.pdf",
        resume_content_type="application/pdf",
        resume_size=2048,
    )


def test_create_sets_id_and_default_state(db_session):
    repo = LeadRepository(db_session)

    lead = _make_lead(repo)

    assert lead.id is not None
    assert lead.state == LeadState.PENDING
    assert lead.created_at is not None


def test_get_by_id_round_trip(db_session):
    repo = LeadRepository(db_session)

    created = _make_lead(repo)
    fetched = repo.get_by_id(created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.email == "prospect@example.com"
    assert fetched.resume_original_name == "resume.pdf"


def test_get_by_id_missing_returns_none(db_session):
    repo = LeadRepository(db_session)
    assert repo.get_by_id(999999) is None


def test_list_all_returns_created_leads(db_session):
    repo = LeadRepository(db_session)

    first = _make_lead(repo, email="a@example.com")
    second = _make_lead(repo, email="b@example.com")

    leads = repo.list_all()

    assert [lead.id for lead in leads] == [first.id, second.id]


def test_update_state_transitions_pending_to_reached_out(db_session):
    repo = LeadRepository(db_session)

    lead = _make_lead(repo)
    assert lead.state == LeadState.PENDING

    updated = repo.update_state(lead.id, LeadState.REACHED_OUT)

    assert updated is not None
    assert updated.id == lead.id
    assert updated.state == LeadState.REACHED_OUT
    assert repo.get_by_id(lead.id).state == LeadState.REACHED_OUT


def test_update_state_missing_returns_none(db_session):
    repo = LeadRepository(db_session)
    assert repo.update_state(999999, LeadState.REACHED_OUT) is None
