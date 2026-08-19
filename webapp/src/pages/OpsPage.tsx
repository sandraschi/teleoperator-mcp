import { useEffect, useState } from "react";
import { API_BASE } from "../lib/api";

interface SupervisionRow {
  robot_id: string;
  display_name: string;
  virtual_twin?: boolean;
  claimed: boolean;
  operator_id: string | null;
  claimed_at: number | null;
}

interface SupervisionPayload {
  robots: SupervisionRow[];
  active: boolean;
  active_robot: string | null;
  require_claim: boolean;
}

export function OpsPage() {
  const [data, setData] = useState<SupervisionPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/supervision`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setData((await res.json()) as SupervisionPayload);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    const id = window.setInterval(() => void load(), 5000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <section className="page-card" data-testid="ops-page">
      <h2>Ops console — multi-robot supervision</h2>
      <p style={{ margin: "0 0 1rem", fontSize: "0.88rem", color: "var(--shell-muted)" }}>
        Monitor every robot's claim + reachability. Drive is single-session by design (one physical
        robot, one operator); supervision is fleet-wide.
      </p>
      {loading && <div className="skeleton" data-testid="ops-loading" style={{ height: "3rem" }} />}
      {error && (
        <p data-testid="ops-error" style={{ color: "var(--danger, #ef4444)" }}>
          Failed to load supervision: {error}
        </p>
      )}
      {data && (
        <>
          <div className="tool-row" data-testid="ops-active">
            <strong>Active session</strong>
            <span className={`status-pill ${data.active ? "ok" : ""}`}>
              {data.active ? (data.active_robot ?? "active") : "none"}
            </span>
          </div>
          <div className="table-wrap">
            <table className="data-table" data-testid="ops-table">
              <thead>
                <tr>
                  <th>Robot</th>
                  <th>Type</th>
                  <th>Claim</th>
                  <th>Operator</th>
                </tr>
              </thead>
              <tbody>
                {data.robots.map((r) => (
                  <tr key={r.robot_id} data-testid={`ops-row-${r.robot_id}`}>
                    <td>
                      <code>{r.robot_id}</code>
                    </td>
                    <td>{r.virtual_twin ? "virtual" : "physical"}</td>
                    <td>
                      <span className={`status-pill ${r.claimed ? "ok" : "warn"}`}>
                        {r.claimed ? "claimed" : "free"}
                      </span>
                    </td>
                    <td>{r.operator_id ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p style={{ margin: "1rem 0 0", fontSize: "0.8rem", color: "var(--shell-muted)" }}>
            Claim gate {data.require_claim ? "enabled" : "disabled"} · refresh every 5s
          </p>
        </>
      )}
    </section>
  );
}
