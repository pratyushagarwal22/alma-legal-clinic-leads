"""Lead request/response DTOs.

``LeadCreate`` is the input carried by the public submission form; ``email`` is an
``EmailStr`` so malformed addresses are rejected at the API boundary (before any
business logic runs). ``LeadOut`` is the response DTO and deliberately exposes
only what the UI needs — notably the resume's original filename and content type
for display/download — while never leaking internal storage details (the stored
path/key) or any hashed values.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.db.models import LeadState


class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr


class LeadStateUpdate(BaseModel):
    """Body of ``PATCH /leads/{id}/state``: the target state for the lead."""

    state: LeadState


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: str
    state: LeadState
    resume_original_name: str
    resume_content_type: str
    resume_size: int
    created_at: datetime
    updated_at: datetime
