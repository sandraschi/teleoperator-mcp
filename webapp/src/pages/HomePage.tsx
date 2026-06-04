import { useCallback, useEffect, useState } from "react";
import { XrSession } from "../xr-session";
import { useCapabilities } from "../lib/capabilities";
import type { HealthResponse } from "../lib/types";

export function HomePage() {
  const { caps, loading: capsLoading } = useCapabilities();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [xrHint, setXrHint] = useState("Checking WebXR…");
  const [vrSupported, setVrSupported] = useState(false);
  const [entering, setEntering] = useState(false);
  const [robot, setRobot] = useState("boomy");

  const pollHealth = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/health");
      setHealth((await res.json()) as HealthResponse);
    } catch {
      setHealth(null);
    }
  }, []);

  useEffect(() => {
    void pollHealth();
    const id = window.setInterval(() => void pollHealth(), 3000);
    return () => window.clearInterval(id);
  }, [pollHealth]);

  useEffect(() => {
    void (async () => {
      if (!navigator.xr) {
        setXrHint("WebXR not available in this browser.");
        return;
      }
      const ok = await navigator.xr.isSessionSupported("immersive-vr");
      setVrSupported(ok);
      setXrHint(
        ok
          ? "WebXR immersive-vr supported. Use HTTPS on headset (Tailscale Serve)."
          : "immersive-vr not supported on this device.",
      );
    })();
  }, []);

  const enterVr = async () => {
    const canvas = document.getElementById("xr-canvas") as HTMLCanvasElement | null;
    if (!canvas) return;
    setEntering(true);
    try {
      const session = new XrSession(canvas, robot);
      await session.start();
    } catch (err) {
      setXrHint(err instanceof Error ? err.message : String(err));
      setEntering(false);
    }
  };

  useEffect(() => {
    const onEnd = () => setEntering(false);
    document.body.addEventListener("teleop-xr-ended", onEnd);
    return () => document.body.removeEventListener("teleop-xr-ended", onEnd);
  }, []);

  return (
    <>
      <div className="page-grid">
        <div className="stat-card">
          <dt>Backend</dt>
          <dd>{health?.status === "ok" ? "Online" : "Offline"}</dd>
        </div>
        <div className="stat-card">
          <dt>Teleop session</dt>
          <dd>{health?.teleop?.active ? "Active" : "Idle"}</dd>
        </div>
        <div className="stat-card">
          <dt>Frames in</dt>
          <dd>{health?.teleop?.frames_in ?? 0}</dd>
        </div>
        <div className="stat-card">
          <dt>Uptime</dt>
          <dd>{health ? `${health.uptime_s}s` : "—"}</dd>
        </div>
      </div>

      <section className="page-card">
        <h2>Enter VR teleop</h2>
        <p style={{ margin: "0 0 1rem", color: "var(--shell-muted)", fontSize: "0.9rem" }}>
          Pico 4 / Quest browser → WebXR pose stream → Boomy. Chin HUD stays out of the way.
        </p>
        <div className="field">
          <label htmlFor="robot-select">Robot</label>
          <select
            id="robot-select"
            value={robot}
            onChange={(e) => setRobot(e.target.value)}
            disabled={entering}
          >
            <option value="boomy">Boomy (Yahboom)</option>
          </select>
        </div>
        <button
          type="button"
          className="btn"
          disabled={!vrSupported || entering}
          onClick={() => void enterVr()}
        >
          {entering ? "In VR session…" : "Enter VR"}
        </button>
        <p style={{ margin: "0.75rem 0 0", fontSize: "0.85rem", color: "var(--shell-muted)" }}>
          {xrHint}
        </p>
      </section>

      <section className="page-card">
        <h2>Capabilities</h2>
        {capsLoading && <div className="skeleton" style={{ width: "60%", marginBottom: "0.5rem" }} />}
        {caps && (
          <>
            <div className="cap-badges" style={{ marginBottom: "0.75rem" }}>
              {Object.entries(caps.features).map(([k, v]) => (
                <span key={k} className={`cap-badge ${v ? "on" : "off"}`}>
                  {k.replace(/_/g, " ")}
                </span>
              ))}
            </div>
            <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--shell-muted)" }}>
              {caps.tool_surface.atomic_count} atomic tools · transport {String(caps.runtime.transport)}
            </p>
          </>
        )}
      </section>
    </>
  );
}
