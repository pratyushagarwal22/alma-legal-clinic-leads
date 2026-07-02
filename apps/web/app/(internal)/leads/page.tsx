"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  ApiError,
  fetchResume,
  listLeads,
  updateLeadState,
  type Lead,
} from "@/lib/api";
import { clearToken } from "@/lib/auth";

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; leads: Lead[] }
  | { kind: "error"; message: string };

export default function LeadsDashboardPage() {
  const router = useRouter();
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  // Per-row pending flags so a single action disables only its own buttons.
  const [busy, setBusy] = useState<Record<number, boolean>>({});
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setState({ kind: "loading" });
    try {
      const leads = await listLeads();
      setState({ kind: "ready", leads });
    } catch (err) {
      setState({ kind: "error", message: describeError(err) });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function handleLogout() {
    clearToken();
    router.replace("/login");
  }

  async function handleMarkReachedOut(lead: Lead) {
    setNotice(null);
    setBusy((prev) => ({ ...prev, [lead.id]: true }));
    try {
      const updated = await updateLeadState(lead.id, "REACHED_OUT");
      setState((prev) =>
        prev.kind === "ready"
          ? {
              kind: "ready",
              leads: prev.leads.map((l) => (l.id === updated.id ? updated : l)),
            }
          : prev,
      );
    } catch (err) {
      setNotice(describeError(err));
    } finally {
      setBusy((prev) => ({ ...prev, [lead.id]: false }));
    }
  }

  async function handleOpenResume(lead: Lead) {
    setNotice(null);
    setBusy((prev) => ({ ...prev, [lead.id]: true }));
    try {
      const { blob } = await fetchResume(lead.id);
      const objectUrl = URL.createObjectURL(blob);
      if (lead.resume_content_type === "application/pdf") {
        // PDFs render inline in a new tab.
        window.open(objectUrl, "_blank", "noopener,noreferrer");
      } else {
        // Everything else (e.g. DOCX) downloads with the original filename.
        const anchor = document.createElement("a");
        anchor.href = objectUrl;
        anchor.download = lead.resume_original_name;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
      }
      // Release the object URL after the browser has had a chance to use it.
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
    } catch (err) {
      setNotice(describeError(err));
    } finally {
      setBusy((prev) => ({ ...prev, [lead.id]: false }));
    }
  }

  return (
    <main className="wide">
      <div className="dashboard-header">
        <div>
          <h1>Leads</h1>
          <p className="subtitle">All submitted applications.</p>
        </div>
        <button type="button" className="button secondary" onClick={handleLogout}>
          Log out
        </button>
      </div>

      {notice && (
        <span className="status err" role="alert">
          <span className="dot" />
          {notice}
        </span>
      )}

      {state.kind === "loading" && (
        <div className="card">
          <p className="meta">Loading leads…</p>
        </div>
      )}

      {state.kind === "error" && (
        <div className="card">
          <span className="status err" role="alert">
            <span className="dot" />
            {state.message}
          </span>
          <button type="button" className="button secondary" onClick={() => void load()}>
            Try again
          </button>
        </div>
      )}

      {state.kind === "ready" && state.leads.length === 0 && (
        <div className="card">
          <p className="meta">No leads yet.</p>
        </div>
      )}

      {state.kind === "ready" && state.leads.length > 0 && (
        <div className="table-wrap">
          <table className="leads-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>State</th>
                <th>Resume</th>
                <th className="actions-col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {state.leads.map((lead) => {
                const isBusy = Boolean(busy[lead.id]);
                const reachedOut = lead.state === "REACHED_OUT";
                return (
                  <tr key={lead.id}>
                    <td className="truncate" title={`${lead.first_name} ${lead.last_name}`}>
                      {lead.first_name} {lead.last_name}
                    </td>
                    <td className="truncate" title={lead.email}>
                      {lead.email}
                    </td>
                    <td>
                      <span className={`badge ${reachedOut ? "badge-ok" : "badge-pending"}`}>
                        {reachedOut ? "Reached out" : "Pending"}
                      </span>
                    </td>
                    <td className="truncate" title={lead.resume_original_name}>
                      {lead.resume_original_name}
                    </td>
                    <td className="actions-col">
                      <div className="row-actions">
                        <button
                          type="button"
                          className="button small secondary"
                          disabled={isBusy}
                          onClick={() => void handleOpenResume(lead)}
                        >
                          Resume
                        </button>
                        <button
                          type="button"
                          className="button small"
                          disabled={isBusy || reachedOut}
                          onClick={() => void handleMarkReachedOut(lead)}
                        >
                          {reachedOut ? "Done" : "Mark reached out"}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}

function describeError(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return `Could not reach the server: ${err.message}`;
  return "Something went wrong. Please try again.";
}
