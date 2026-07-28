import { useCallback, useEffect, useState } from "react";
import { API_BASE } from "../lib/api";
import type { LogEntry, LogsResponse } from "../lib/types";

const LEVELS = ["", "DEBUG", "INFO", "WARNING", "ERROR"];
const KINDS = ["", "api", "teleop", "server", "system"];

export function LogsPage() {
  const [data, setData] = useState<LogsResponse | null>(null);
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [level, setLevel] = useState("");
  const [kind, setKind] = useState("");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<"asc" | "desc">("desc");
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(50);
  const [liveTail, setLiveTail] = useState(false);
  const [afterId, setAfterId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const params = new URLSearchParams({
        limit: String(limit),
        offset: String(liveTail ? 0 : offset),
        sort,
      });
      if (level) params.set("level", level);
      if (kind) params.set("kind", kind);
      if (search.trim()) params.set("search", search.trim());
      if (liveTail && afterId) params.set("after_id", afterId);

      const [logsRes, statsRes] = await Promise.all([
        fetch(API_BASE + `/api/logs?${params}`),
        fetch(API_BASE + "/api/logs/stats"),
      ]);
      const logs = (await logsRes.json()) as LogsResponse;
      setData(logs);
      if (liveTail && logs.entries.length) {
        setAfterId(logs.entries[0].id);
      }
      setStats(await statsRes.json());
    } catch {
      setData(null);
    } finally {
      setBusy(false);
    }
  }, [level, kind, search, sort, offset, limit, liveTail, afterId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!liveTail) return;
    const id = window.setInterval(() => void load(), 1500);
    return () => window.clearInterval(id);
  }, [liveTail, load]);

  const exportLogs = (format: "json" | "csv") => {
    const params = new URLSearchParams({ format, sort });
    if (level) params.set("level", level);
    if (kind) params.set("kind", kind);
    if (search.trim()) params.set("search", search.trim());
    window.open(`/api/logs/export?${params}`, "_blank");
  };

  const clearLogs = async () => {
    if (!window.confirm("Clear all log entries?")) return;
    await fetch(API_BASE + "/api/logs", { method: "DELETE" });
    setAfterId(null);
    void load();
  };

  const total = data?.total ?? 0;
  const page = Math.floor(offset / limit) + 1;
  const pages = Math.max(1, Math.ceil(total / limit));

  return (
    <>
      <section className="page-card">
        <h2>Ring buffer stats</h2>
        {stats ? (
          <div className="page-grid">
            <div className="stat-card">
              <dt>Total entries</dt>
              <dd>{String(stats.total ?? 0)}</dd>
            </div>
            <div className="stat-card">
              <dt>Max capacity</dt>
              <dd>{String(stats.max_entries ?? "—")}</dd>
            </div>
            <div className="stat-card">
              <dt>Rotation</dt>
              <dd>{String(stats.rotation ?? "—")}</dd>
            </div>
          </div>
        ) : (
          <div className="skeleton" style={{ height: "2rem", width: "40%" }} />
        )}
      </section>

      <section className="page-card">
        <div className="filters-row">
          <div className="field">
            <label htmlFor="log-level">Min level</label>
            <select id="log-level" value={level} onChange={(e) => { setLevel(e.target.value); setOffset(0); }}>
              {LEVELS.map((l) => (
                <option key={l || "all"} value={l}>{l || "All"}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="log-kind">Kind</label>
            <select id="log-kind" value={kind} onChange={(e) => { setKind(e.target.value); setOffset(0); }}>
              {KINDS.map((k) => (
                <option key={k || "all"} value={k}>{k || "All"}</option>
              ))}
            </select>
          </div>
          <div className="field" style={{ flex: 1, minWidth: "12rem" }}>
            <label htmlFor="log-search">Search</label>
            <input
              id="log-search"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
              placeholder="Filter detail or meta…"
            />
          </div>
          <div className="field">
            <label htmlFor="log-sort">Sort</label>
            <select id="log-sort" value={sort} onChange={(e) => setSort(e.target.value as "asc" | "desc")}>
              <option value="desc">Newest first</option>
              <option value="asc">Oldest first</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="log-limit">Page size</label>
            <select id="log-limit" value={limit} onChange={(e) => { setLimit(Number(e.target.value)); setOffset(0); }}>
              {[25, 50, 100, 200].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.85rem" }}>
            <input type="checkbox" checked={liveTail} onChange={(e) => setLiveTail(e.target.checked)} />
            Live tail
          </label>
          <button type="button" className="btn secondary" onClick={() => void load()} disabled={busy}>
            Refresh
          </button>
          <button type="button" className="btn secondary" onClick={() => exportLogs("json")}>
            Export JSON
          </button>
          <button type="button" className="btn secondary" onClick={() => exportLogs("csv")}>
            Export CSV
          </button>
          <button type="button" className="btn danger" onClick={() => void clearLogs()}>
            Clear
          </button>
        </div>

        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Level</th>
                <th>Kind</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {(data?.entries ?? []).map((e: LogEntry) => (
                <tr key={e.id}>
                  <td>{e.timestamp.replace("T", " ").slice(0, 19)}</td>
                  <td>{e.level}</td>
                  <td>{e.kind}</td>
                  <td>{e.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!liveTail && (
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem", alignItems: "center" }}>
            <button
              type="button"
              className="btn secondary"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - limit))}
            >
              Previous
            </button>
            <span style={{ fontSize: "0.85rem", color: "var(--shell-muted)" }}>
              Page {page} / {pages} ({total} entries)
            </span>
            <button
              type="button"
              className="btn secondary"
              disabled={offset + limit >= total}
              onClick={() => setOffset(offset + limit)}
            >
              Next
            </button>
          </div>
        )}
      </section>
    </>
  );
}
