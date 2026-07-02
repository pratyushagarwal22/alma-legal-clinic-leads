"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError, login as apiLogin } from "@/lib/api";
import { setToken } from "@/lib/auth";

// Where to send the attorney after a successful login. The guard appends a
// `?next=<path>` when it bounces someone here; we honor it, falling back to the
// internal leads dashboard (built in a later task).
const DEFAULT_REDIRECT = "/leads";

function resolveRedirect(): string {
  if (typeof window === "undefined") return DEFAULT_REDIRECT;
  const next = new URLSearchParams(window.location.search).get("next");
  // Only allow same-origin relative paths to avoid open-redirects.
  if (next && next.startsWith("/") && !next.startsWith("//")) return next;
  return DEFAULT_REDIRECT;
}

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!email.trim() || !password) {
      setError("Email and password are required.");
      return;
    }

    setSubmitting(true);
    try {
      const { access_token } = await apiLogin(email.trim(), password);
      setToken(access_token);
      router.replace(resolveRedirect());
    } catch (err) {
      const message =
        err instanceof ApiError
          ? "Invalid email or password."
          : err instanceof Error
            ? `Could not reach the server: ${err.message}`
            : "Something went wrong. Please try again.";
      setError(message);
      setSubmitting(false);
    }
  }

  return (
    <main>
      <h1>Attorney sign in</h1>
      <p className="subtitle">Sign in to view and manage leads.</p>

      <form className="card" onSubmit={handleSubmit} noValidate>
        {error && (
          <span className="status err" role="alert">
            <span className="dot" />
            {error}
          </span>
        )}

        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="username"
            value={email}
            disabled={submitting}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            disabled={submitting}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </main>
  );
}
