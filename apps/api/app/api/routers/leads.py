"""Leads router — thin HTTP layer over ``LeadService``.

Each endpoint only parses/validates input, invokes a single service method, and
maps the result (or a guard) to an HTTP response. No DB access, no file IO, and
no business rules live here: creation ordering, validation, state changes, and
resume reads are all owned by the service. Domain exceptions raised by the
service (``LeadNotFoundError``, ``LeadValidationError``) are mapped to status
codes centrally in ``main.py``.
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import EmailStr

from app.api.deps import get_current_attorney, get_lead_service
from app.db.models import User
from app.schemas.lead import LeadCreate, LeadOut, LeadStateUpdate
from app.services.lead_service import LeadService

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("", response_model=LeadOut, status_code=201)
async def create_lead(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: EmailStr = Form(...),
    resume: UploadFile = File(...),
    lead_service: LeadService = Depends(get_lead_service),
) -> LeadOut:
    """Public: create a lead from the submitted form fields and resume file."""
    content = await resume.read()
    data = LeadCreate(first_name=first_name, last_name=last_name, email=email)
    return lead_service.create(
        data,
        content=content,
        original_name=resume.filename or "",
        content_type=resume.content_type or "application/octet-stream",
    )


@router.get("", response_model=list[LeadOut])
def list_leads(
    _attorney: User = Depends(get_current_attorney),
    lead_service: LeadService = Depends(get_lead_service),
) -> list[LeadOut]:
    return lead_service.list_all()


@router.patch("/{lead_id}/state", response_model=LeadOut)
def update_lead_state(
    lead_id: int,
    payload: LeadStateUpdate,
    _attorney: User = Depends(get_current_attorney),
    lead_service: LeadService = Depends(get_lead_service),
) -> LeadOut:
    return lead_service.update_state(lead_id, payload.state)


@router.get("/{lead_id}/resume")
def get_lead_resume(
    lead_id: int,
    _attorney: User = Depends(get_current_attorney),
    lead_service: LeadService = Depends(get_lead_service),
) -> StreamingResponse:
    resume = lead_service.read_resume(lead_id)
    # Inline for PDFs so the browser renders them in-tab; attachment otherwise
    # (e.g. DOCX) so it downloads. This is purely an HTTP-response mapping.
    disposition_type = (
        "inline" if resume.content_type == "application/pdf" else "attachment"
    )
    headers = {
        "Content-Disposition": f'{disposition_type}; filename="{resume.original_name}"'
    }
    return StreamingResponse(
        iter([resume.content]),
        media_type=resume.content_type,
        headers=headers,
    )
