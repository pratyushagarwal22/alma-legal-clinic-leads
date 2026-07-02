"""Integration tests for the leads router (Task 10).

Exercises the full HTTP layer against the test Postgres: public creation without
auth, auth-guarding of the internal endpoints (401 without a token, success
with one), the ``PENDING`` -> ``REACHED_OUT`` state transition, and the resume
download endpoint's ``Content-Disposition`` / content-type behavior (PDF inline,
DOCX attachment). Requires ``docker compose up -d db``.
"""

PDF_BYTES = b"%PDF-1.4 fake resume bytes"
DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def _create_lead(
    client,
    *,
    first_name="Ada",
    last_name="Lovelace",
    email="ada@example.com",
    filename="resume.pdf",
    content=PDF_BYTES,
    content_type="application/pdf",
):
    return client.post(
        "/leads",
        data={"first_name": first_name, "last_name": last_name, "email": email},
        files={"resume": (filename, content, content_type)},
    )


# --- public creation (no auth) ---------------------------------------------


def test_create_lead_is_public_and_returns_lead_out(client, email_service):
    response = _create_lead(client)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["first_name"] == "Ada"
    assert body["last_name"] == "Lovelace"
    assert body["email"] == "ada@example.com"
    assert body["state"] == "PENDING"
    assert body["resume_original_name"] == "resume.pdf"
    assert body["resume_content_type"] == "application/pdf"
    # LeadOut must not leak internal storage details.
    assert "resume_path" not in body
    # Both notification emails were dispatched by the service.
    assert len(email_service.sent) == 2


# --- auth guarding: 401 without a token, success with one -------------------


def test_list_leads_requires_auth(client):
    assert client.get("/leads").status_code == 401


def test_list_leads_succeeds_with_token(client, auth_headers):
    _create_lead(client, email="one@example.com")
    _create_lead(client, email="two@example.com")

    response = client.get("/leads", headers=auth_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 2
    assert {lead["email"] for lead in body} == {"one@example.com", "two@example.com"}


def test_patch_state_requires_auth(client):
    created = _create_lead(client)
    lead_id = created.json()["id"]

    response = client.patch(
        f"/leads/{lead_id}/state", json={"state": "REACHED_OUT"}
    )

    assert response.status_code == 401


def test_get_resume_requires_auth(client):
    created = _create_lead(client)
    lead_id = created.json()["id"]

    assert client.get(f"/leads/{lead_id}/resume").status_code == 401


def test_invalid_token_is_rejected(client):
    response = client.get(
        "/leads", headers={"Authorization": "Bearer not-a-real-jwt"}
    )
    assert response.status_code == 401


# --- state transition -------------------------------------------------------


def test_patch_state_transitions_pending_to_reached_out(client, auth_headers):
    created = _create_lead(client)
    lead_id = created.json()["id"]
    assert created.json()["state"] == "PENDING"

    response = client.patch(
        f"/leads/{lead_id}/state",
        json={"state": "REACHED_OUT"},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["state"] == "REACHED_OUT"

    # The transition is persisted and visible on a subsequent list.
    listed = client.get("/leads", headers=auth_headers).json()
    assert listed[0]["state"] == "REACHED_OUT"


def test_patch_state_on_missing_lead_returns_404(client, auth_headers):
    response = client.patch(
        "/leads/999999/state",
        json={"state": "REACHED_OUT"},
        headers=auth_headers,
    )
    assert response.status_code == 404


# --- resume download: Content-Disposition + content type --------------------


def test_get_resume_returns_pdf_inline_with_original_filename(client, auth_headers):
    created = _create_lead(
        client, filename="ada-cv.pdf", content=PDF_BYTES, content_type="application/pdf"
    )
    lead_id = created.json()["id"]

    response = client.get(f"/leads/{lead_id}/resume", headers=auth_headers)

    assert response.status_code == 200, response.text
    assert response.content == PDF_BYTES
    assert response.headers["content-type"].startswith("application/pdf")
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("inline")
    assert 'filename="ada-cv.pdf"' in disposition


def test_get_resume_returns_docx_as_attachment_with_original_filename(
    client, auth_headers
):
    docx_bytes = b"PK\x03\x04 fake docx bytes"
    created = _create_lead(
        client,
        filename="ada-cv.docx",
        content=docx_bytes,
        content_type=DOCX_CONTENT_TYPE,
    )
    lead_id = created.json()["id"]

    response = client.get(f"/leads/{lead_id}/resume", headers=auth_headers)

    assert response.status_code == 200, response.text
    assert response.content == docx_bytes
    assert response.headers["content-type"].startswith(DOCX_CONTENT_TYPE)
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment")
    assert 'filename="ada-cv.docx"' in disposition
