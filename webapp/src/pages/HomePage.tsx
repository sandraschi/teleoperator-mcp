import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { API_BASE } from "../lib/api";
import { useCapabilities } from "../lib/capabilities";
import type { HealthResponse, RobotCatalogEntry } from "../lib/types";
import { useBackendStore } from "../store";
import { XrSession } from "../xr-session";

const FALLBACK_ROBOTS: Record<string, RobotCatalogEntry> = {
  boomy: { status: "available", robot_id: "boomy", display_name: "Boomy (Yahboom)" },
  bumi: { status: "available", robot_id: "bumi", display_name: "Bumi (biped)" },
  vboomy: {
    status: "available",
    robot_id: "vboomy",
    display_name: "vBoomy (Resonite virtual twin)",
    virtual_twin: true,
  },
};

function robotFromUrl(): string {
  const params = new URLSearchParams(window.location.search);
  const q = params.get("robot")?.trim().toLowerCase();
  return q || "boomy";
}

export function HomePage() {
  const { caps, loading: capsLoading } = useCapabilities();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [xrHint, setXrHint] = useState("Checking WebXR…");
  const [vrSupported, setVrSupported] = useState(false);
  const [entering, setEntering] = useState(false);
  const [robot, setRobot] = useState(robotFromUrl);
  const setOnline = useBackendStore((s) => s.setOnline);
  const pollAttempt = useRef(0);
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const catalog = useMemo(
    () => health?.teleop?.robots ?? FALLBACK_ROBOTS,
    [health?.teleop?.robots],
  );

  const robotOptions = useMemo(
    () =>
      Object.entries(catalog)
        .filter(([, meta]) => meta.status === "available")
        .sort(([a], [b]) => a.localeCompare(b)),
    [catalog],
  );

  const selectedMeta = catalog[robot];

  const pollHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/health`);
      const data = (await res.json()) as HealthResponse;
      setHealth(data);
      setOnline(true);
      pollAttempt.current = 0;
    } catch {
      setHealth(null);
      setOnline(false);
      pollAttempt.current += 1;
    }
  }, [setOnline]);

  useEffect(() => {
    void pollHealth();
    const schedule = () => {
      const delays = [1000, 2000, 4000, 8000, 16000];
      const delay = delays[Math.min(pollAttempt.current, delays.length - 1)];
      pollTimer.current = setTimeout(() => {
        void pollHealth().then(schedule);
      }, delay);
    };
    const id = setTimeout(schedule, 3000);
    return () => {
      clearTimeout(id);
      if (pollTimer.current) clearTimeout(pollTimer.current);
    };
  }, [pollHealth]);

  useEffect(() => {
    const q = robotFromUrl();
    if (q !== robot) setRobot(q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const url = new URL(window.location.href);
    url.searchParams.set("robot", robot);
    window.history.replaceState(null, "", url.toString());
  }, [robot]);

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
        <div className="stat-card" data-testid="kpi-server">
          <dt>Backend</dt>
          <dd>{health?.status === "ok" ? "Online" : "Offline"}</dd>
        </div>
        <div className="stat-card" data-testid="kpi-robot">
          <dt>Teleop session</dt>
          <dd>{health?.teleop?.active ? "Active" : "Idle"}</dd>
        </div>
        <div className="stat-card" data-testid="kpi-webrtc">
          <dt>Frames in</dt>
          <dd>{health?.teleop?.frames_in ?? 0}</dd>
        </div>
        <div className="stat-card" data-testid="kpi-tools">
          <dt>Uptime</dt>
          <dd>{health ? `${health.uptime_s}s` : "—"}</dd>
        </div>
      </div>

      <section className="page-card">
        <h2>Enter VR teleop</h2>
        <p style={{ margin: "0 0 1rem", color: "var(--shell-muted)", fontSize: "0.9rem" }}>
          Pico 4 / Quest browser → WebXR pose stream → fleet robot or Resonite virtual twin.
        </p>
        <div className="field">
          <label htmlFor="robot-select">Robot</label>
          <select
            id="robot-select"
            value={robot}
            onChange={(e) => setRobot(e.target.value)}
            disabled={entering}
          >
            {robotOptions.map(([id, meta]) => (
              <option key={id} value={id}>
                {meta.display_name}
                {meta.virtual_twin ? " · virtual" : ""}
              </option>
            ))}
          </select>
        </div>
        {selectedMeta?.virtual_twin && (
          <p style={{ margin: "0 0 0.75rem", fontSize: "0.82rem", color: "var(--shell-muted)" }}>
            Resonite OSC on port 9000 — register with scripts/register-vboomy.ps1
          </p>
        )}
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
        {capsLoading && (
          <div className="skeleton" style={{ width: "60%", marginBottom: "0.5rem" }} />
        )}
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
              {caps.tool_surface.atomic_count} atomic tools · transport{" "}
              {String(caps.runtime.transport)}
            </p>
          </>
        )}
      </section>
    </>
  );
}
