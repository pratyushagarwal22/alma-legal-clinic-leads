/**
 * Client-side auth token store for the attorney session.
 *
 * The JWT issued by POST /auth/login is kept in localStorage so it survives
 * reloads within the browser tab. This is deliberately minimal (design §10):
 * no refresh tokens or roles. The token is read from here by the API client's
 * authorized-request helper and by the internal-route guard.
 *
 * All accessors are SSR-safe: on the server there is no `window`, so they
 * return the logged-out state rather than throwing.
 */

const TOKEN_KEY = "legal_clinic_token";

function hasWindow(): boolean {
  return typeof window !== "undefined";
}

/** Return the stored JWT, or null if none is present (or on the server). */
export function getToken(): string | null {
  if (!hasWindow()) return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

/** Persist the JWT returned by a successful login. */
export function setToken(token: string): void {
  if (!hasWindow()) return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

/** Remove the stored JWT (logout). */
export function clearToken(): void {
  if (!hasWindow()) return;
  window.localStorage.removeItem(TOKEN_KEY);
}

/** True when a token is present. Not a validity check — the API still enforces auth. */
export function isAuthenticated(): boolean {
  return getToken() !== null;
}
