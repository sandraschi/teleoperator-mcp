import { useEffect, useState } from "react";
import { API_BASE } from "../lib/api";
import type { LogEntry, LogsResponse } from "../lib/types";

export function InboxPage() {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/logs?limit=20&sort=desc`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as LogsResponse;
        if (!cancelled) setEntries(data.entries ?? []);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const warnings = entries.filter((e) => e.level === "WARNING" || e.level === "ERROR");

  return (
    <section className="page-card" data-testid="inbox-page">
      <h2>Activity inbox</h2>
      <p style={{ margin: "0 0 1rem", fontSize: "0.88rem", color: "var(--shell-muted)" }}>
        Recent teleop + system events from the backend ring buffer. Warnings and errors are surfaced
        first.
      </p>
      {loading && (
        <div className="skeleton" data-testid="inbox-loading" style={{ height: "3rem" }} />
      )}
      {error && (
        <p data-testid="inbox-error" style={{ color: "var(--danger, #ef4444)" }}>
          Failed to load inbox: {error}
        </p>
      )}
      {!loading && !error && entries.length === 0 && (
        <p data-testid="inbox-empty">No events yet. Run a teleop session or check the Logs page.</p>
      )}
      {!loading && !error && entries.length > 0 && (
        <>
          {warnings.length > 0 && (
            <div className="tool-row" data-testid="inbox-warnings">
              <strong>{warnings.length} warning(s) in the last 20 events</strong>
              <span className="status-pill warn">needs attention</span>
            </div>
          )}
          <div className="table-wrap">
            <table className="data-table" data-testid="inbox-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Level</th>
                  <th>Kind</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e) => (
                  <tr key={e.id} data-testid={`inbox-row-${e.id}`}>
                    <td style={{ whiteSpace: "nowrap" }}>{e.timestamp}</td>
                    <td>{e.level}</td>
                    <td>{e.kind}</td>
                    <td>{e.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
