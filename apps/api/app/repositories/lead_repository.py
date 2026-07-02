"""Data access for ``Lead`` rows.

The repository layer is the ONLY layer that queries the database. It holds plain
data-access methods with no business logic and does not manage transactions
(commits are the service layer's responsibility per the design's layering rules).
Methods ``flush`` so server-side defaults (id, state, timestamps) are populated
on the returned instances.
"""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Lead, LeadState


class LeadRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        first_name: str,
        last_name: str,
        email: str,
        resume_path: str,
        resume_original_name: str,
        resume_content_type: str,
        resume_size: int,
    ) -> Lead:
        lead = Lead(
            first_name=first_name,
            last_name=last_name,
            email=email,
            resume_path=resume_path,
            resume_original_name=resume_original_name,
            resume_content_type=resume_content_type,
            resume_size=resume_size,
        )
        self._session.add(lead)
        self._session.flush()
        self._session.refresh(lead)
        return lead

    def list_all(self) -> Sequence[Lead]:
        return self._session.execute(select(Lead).order_by(Lead.id)).scalars().all()

    def get_by_id(self, lead_id: int) -> Lead | None:
        return self._session.get(Lead, lead_id)

    def update_state(self, lead_id: int, state: LeadState) -> Lead | None:
        lead = self._session.get(Lead, lead_id)
        if lead is None:
            return None
        lead.state = state
        self._session.flush()
        self._session.refresh(lead)
        return lead
