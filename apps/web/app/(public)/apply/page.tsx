"use client";

import { useRef, useState } from "react";

import { ApiError, createLead, type Lead } from "@/lib/api";

type Status =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "success"; lead: Lead }
  | { kind: "error"; message: string };

interface FieldErrors {
  firstName?: string;
  lastName?: string;
  email?: string;
  resume?: string;
}

export default function ApplyPage() {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [resume, setResume] = useState<File | null>(null);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  const fileInputRef = useRef<HTMLInputElement>(null);

  function validate(): FieldErrors {
    const next: FieldErrors = {};
    if (!firstName.trim()) next.firstName = "First name is required.";
    if (!lastName.trim()) next.lastName = "Last name is required.";
    if (!email.trim()) next.email = "Email is required.";
    if (!resume) next.resume = "A resume file is required.";
    return next;
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const found = validate();
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setStatus({ kind: "submitting" });
    try {
      const lead = await createLead({
        firstName: firstName.trim(),
        lastName: lastName.trim(),
        email: email.trim(),
        // Guarded by validate() above.
        resume: resume as File,
      });
      setStatus({ kind: "success", lead });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? `Could not reach the server: ${err.message}`
            : "Something went wrong. Please try again.";
      setStatus({ kind: "error", message });
    }
  }

  function resetForm() {
    setFirstName("");
    setLastName("");
    setEmail("");
    setResume(null);
    setErrors({});
    setStatus({ kind: "idle" });
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  if (status.kind === "success") {
    return (
      <main>
        <h1>Application received</h1>
        <p className="subtitle">Thanks for reaching out to the legal clinic.</p>

        <div className="card">
          <span className="status ok">
            <span className="dot" />
            Your application was submitted successfully.
          </span>
          <p className="meta">
            We&rsquo;ve sent a confirmation to <code>{status.lead.email}</code>.
            An attorney will review your submission and reach out to you.
          </p>
          <button type="button" className="button secondary" onClick={resetForm}>
            Submit another application
          </button>
        </div>
      </main>
    );
  }

  const submitting = status.kind === "submitting";

  return (
    <main>
      <h1>Apply to the Legal Clinic</h1>
      <p className="subtitle">
        Share your details and resume, and an attorney will get in touch.
      </p>

      <form className="card" onSubmit={handleSubmit} noValidate>
        {status.kind === "error" && (
          <span className="status err" role="alert">
            <span className="dot" />
            {status.message}
          </span>
        )}

        <div className="field">
          <label htmlFor="firstName">First name</label>
          <input
            id="firstName"
            name="firstName"
            type="text"
            value={firstName}
            disabled={submitting}
            onChange={(e) => setFirstName(e.target.value)}
            aria-invalid={Boolean(errors.firstName)}
          />
          {errors.firstName && <span className="field-error">{errors.firstName}</span>}
        </div>

        <div className="field">
          <label htmlFor="lastName">Last name</label>
          <input
            id="lastName"
            name="lastName"
            type="text"
            value={lastName}
            disabled={submitting}
            onChange={(e) => setLastName(e.target.value)}
            aria-invalid={Boolean(errors.lastName)}
          />
          {errors.lastName && <span className="field-error">{errors.lastName}</span>}
        </div>

        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            name="email"
            type="email"
            value={email}
            disabled={submitting}
            onChange={(e) => setEmail(e.target.value)}
            aria-invalid={Boolean(errors.email)}
          />
          {errors.email && <span className="field-error">{errors.email}</span>}
        </div>

        <div className="field">
          <label htmlFor="resume">Resume / CV</label>
          <input
            id="resume"
            name="resume"
            type="file"
            ref={fileInputRef}
            accept=".pdf,.doc,.docx"
            disabled={submitting}
            onChange={(e) => setResume(e.target.files?.[0] ?? null)}
            aria-invalid={Boolean(errors.resume)}
          />
          {errors.resume && <span className="field-error">{errors.resume}</span>}
        </div>

        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Submitting…" : "Submit application"}
        </button>
      </form>
    </main>
  );
}
