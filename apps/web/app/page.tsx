import { getApiBaseUrl, getHealth } from "@/lib/api";

// Render on every request so the health check reflects the API's current state.
export const dynamic = "force-dynamic";

type Health =
  | { ok: true; status: string }
  | { ok: false; error: string };

async function checkHealth(): Promise<Health> {
  try {
    const res = await getHealth();
    return { ok: true, status: res.status };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

export default async function HomePage() {
  const baseUrl = getApiBaseUrl();
  const health = await checkHealth();

  return (
    <main>
      <h1>Legal Clinic Leads</h1>
      <p className="subtitle">Frontend scaffold is running.</p>

      <div className="card">
        <h2>API connectivity</h2>
        {health.ok ? (
          <span className="status ok">
            <span className="dot" />
            Reached API — /health responded &ldquo;{health.status}&rdquo;
          </span>
        ) : (
          <span className="status err">
            <span className="dot" />
            Could not reach API — {health.error}
          </span>
        )}
        <p className="meta">
          API base URL: <code>{baseUrl}</code>
        </p>
      </div>
    </main>
  );
}
