"""Message builders for the two lead-intake emails.

These are pure functions that assemble :class:`EmailMessage` values; they perform
no I/O. The service layer will call them after a lead is persisted and hand the
result to an ``EmailService`` for delivery.
"""

from app.integrations.email.base import EmailMessage


def prospect_confirmation(*, first_name: str, to_email: str) -> EmailMessage:
    """Confirmation sent to the prospect acknowledging their submission."""
    body = (
        f"Hi {first_name},\n\n"
        "Thanks for reaching out to the legal clinic. We've received your "
        "application and one of our attorneys will review it and be in touch "
        "soon.\n\n"
        "Best regards,\n"
        "The Legal Clinic Team"
    )
    return EmailMessage(
        to=to_email,
        subject="We received your application",
        body=body,
    )


def attorney_notification(
    *,
    attorney_email: str,
    first_name: str,
    last_name: str,
    prospect_email: str,
) -> EmailMessage:
    """Notification sent to the internal attorney about a new lead."""
    body = (
        "A new lead has been submitted.\n\n"
        f"Name: {first_name} {last_name}\n"
        f"Email: {prospect_email}\n\n"
        "Sign in to the dashboard to review the details and their resume."
    )
    return EmailMessage(
        to=attorney_email,
        subject=f"New lead: {first_name} {last_name}",
        body=body,
    )
