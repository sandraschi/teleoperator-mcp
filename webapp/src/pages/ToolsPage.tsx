import { useState } from "react";
import { useCapabilities } from "../lib/capabilities";

const REST_ACTIONS: Record<string, { method: string; path: string; confirm?: string }> = {
  teleop_status: { method: "GET", path: "/api/v1/health" },
  teleop_livekit_status: { method: "GET", path: "/api/v1/livekit/status" },
  teleop_estop: { method: "POST", path: "/api/v1/teleop/estop", confirm: "Send E-STOP?" },
  teleop_takeover: { method: "POST", path: "/api/v1/teleop/takeover" },
  teleop_gaze_center: { method: "POST", path: "/api/v1/teleop/gaze/center" },
  teleop_livekit_publisher_start: { method: "POST", path: "/api/v1/livekit/publisher/start" },
  teleop_livekit_publisher_stop: { method: "POST", path: "/api/v1/livekit/publisher/stop" },
};

export function ToolsPage() {
  const { caps, loading } = useCapabilities();
  const [result, setResult] = useState<string>("");
  const [busy, setBusy] = useState<string | null>(null);

  const runTool = async (name: string) => {
    const action = REST_ACTIONS[name];
    if (!action) {
      setResult(`${name}: MCP-only — use your MCP client or configure via teleop_configure.`);
      return;
    }
    if (action.confirm && !window.confirm(action.confirm)) return;
    setBusy(name);
    setResult("");
    try {
      const res = await fetch(action.path, { method: action.method });
      const text = await res.text();
      setResult(`${name} (${res.status}):\n${text}`);
    } catch (err) {
      setResult(`${name}: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusy(null);
    }
  };

  const tools = caps?.tool_surface.atomic_tools ?? [];

  return (
    <>
      <section className="page-card">
        <h2>MCP tool inspector</h2>
        <p style={{ margin: "0 0 1rem", fontSize: "0.88rem", color: "var(--shell-muted)" }}>
          Dry-run via REST mirrors where available. Configure and set_mode require MCP or WebXR session.
        </p>
        {loading && <div className="skeleton" style={{ height: "3rem" }} />}
        {!loading && tools.length === 0 && <p>No tools reported by /api/capabilities.</p>}
        {tools.map((name) => (
          <div key={name} className="tool-row">
            <div>
              <strong>{name}</strong>
              <div style={{ fontSize: "0.78rem", color: "var(--shell-muted)" }}>
                {REST_ACTIONS[name] ? REST_ACTIONS[name].method + " " + REST_ACTIONS[name].path : "MCP only"}
              </div>
            </div>
            <button
              type="button"
              className={`btn secondary${name === "teleop_estop" ? " danger" : ""}`}
              disabled={busy === name}
              onClick={() => void runTool(name)}
            >
              {busy === name ? "Running…" : "Dry run"}
            </button>
          </div>
        ))}
      </section>
      {result && (
        <section className="page-card">
          <h2>Result</h2>
          <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: "0.8rem" }}>{result}</pre>
        </section>
      )}
    </>
  );
}
