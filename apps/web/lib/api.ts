/**
 * Thin API client for the FastAPI backend.
 *
 * The base URL is supplied by an environment variable so the same build can point
 * at local dev, Docker Compose, or a deployed API without code changes. The
 * `NEXT_PUBLIC_` prefix makes it readable from both server and client components.
 *
 * Helpers are intentionally small: a shared `request` core, plus JSON and
 * multipart conveniences. Later tasks (forms, login, dashboard) build on these.
 */

const DEFAULT_BASE_URL = "http://localhost:8000";

export function getApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_BASE_URL;
  // Trim a trailing slash so callers can pass paths like "/health" freely.
  return raw.replace(/\/+$/, "");
}

export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(status: number, message: string, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  /** Extra headers merged on top of the defaults. */
  headers?: HeadersInit;
}

async function request<T>(
  path: string,
  init: RequestInit,
): Promise<T> {
  const url = `${getApiBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`;

  const response = await fetch(url, {
    // Always hit the network for API data; never serve a stale cached response.
    cache: "no-store",
    ...init,
  });

  const payload = await parseBody(response);

  if (!response.ok) {
    const message =
      (isRecord(payload) && typeof payload.detail === "string"
        ? payload.detail
        : response.statusText) || `Request failed with ${response.status}`;
    throw new ApiError(response.status, message, payload);
  }

  return payload as T;
}

async function parseBody(response: Response): Promise<unknown> {
  if (response.status === 204) return null;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/** GET (or any method) expecting a JSON response. */
export function getJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  return request<T>(path, { method: "GET", ...options });
}

/** POST a JSON body and expect a JSON response. */
export function postJson<T>(
  path: string,
  body: unknown,
  options: RequestOptions = {},
): Promise<T> {
  return request<T>(path, {
    method: "POST",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    body: JSON.stringify(body),
  });
}

/**
 * POST a multipart/form-data body (e.g. a resume upload).
 *
 * Note: we do NOT set Content-Type manually — the browser/runtime sets it along
 * with the correct multipart boundary when a FormData body is passed.
 */
export function postForm<T>(
  path: string,
  form: FormData,
  options: RequestOptions = {},
): Promise<T> {
  return request<T>(path, {
    method: "POST",
    ...options,
    body: form,
  });
}

export interface HealthResponse {
  status: string;
}

/** Liveness probe against the API's GET /health endpoint. */
export function getHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/health");
}
