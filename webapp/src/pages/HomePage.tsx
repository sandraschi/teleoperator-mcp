import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { API_BASE } from "../lib/api";
import { useCapabilities } from "../lib/capabilities";
import { MOCK_ROBOTS, MOCK_SESSION } from "../lib/mockOnboarding";
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
  const [operatorId, setOperatorId] = useState(() => localStorage.getItem("teleop_operator") || "");
  const [claimToken, setClaimToken] = useState(
    () => localStorage.getItem("teleop_claim_token") || "",
  );
  const [claiming, setClaiming] = useState(false);
  const setOnline = useBackendStore((s) => s.setOnline);
  const pollAttempt = useRef(0);
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const configured = health?.onboarding?.configured === true;
  const mockMode = health !== null && !configured;

  const mockFrames = MOCK_SESSION.frames_in;
  const framesIn = health?.teleop?.frames_in ?? (mockMode ? mockFrames : 0);

  const mockCatalog: Record<string, RobotCatalogEntry> = useMemo(
    () =>
      Object.fromEntries(
        MOCK_ROBOTS.map((r) => [
          r.robot_id,
          { status: r.status, robot_id: r.robot_id, display_name: r.display_name },
        ]),
      ),
    [],
  );

  const catalog = useMemo(
    () => health?.teleop?.robots ?? (mockMode ? mockCatalog : FALLBACK_ROBOTS),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [health?.teleop?.robots, mockMode, mockCatalog],
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

  const claimRobot = async () => {
    if (!operatorId.trim()) return;
    setClaiming(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/session/claim`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ operator_id: operatorId.trim(), robot_id: robot }),
      });
      const data = (await res.json()) as { success?: boolean; token?: string; message?: string };
      if (data.success && data.token) {
        setClaimToken(data.token);
        localStorage.setItem("teleop_claim_token", data.token);
        localStorage.setItem("teleop_operator", operatorId.trim());
      } else {
        setXrHint(data.message ?? "Claim failed");
      }
    } catch {
      setXrHint("Claim failed — is the backend running?");
    } finally {
      setClaiming(false);
    }
  };

  const releaseClaim = async () => {
    if (!claimToken) return;
    try {
      await fetch(`${API_BASE}/api/v1/session/release`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: claimToken }),
      });
    } finally {
      setClaimToken("");
      localStorage.removeItem("teleop_claim_token");
    }
  };

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
      const session = new XrSession(canvas, robot, claimToken);
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
      {mockMode && (
        <div
          className="page-card"
          data-testid="mock-data-banner"
          style={{ border: "1px dashed var(--danger, #dc2626)", marginBottom: "1rem" }}
        >
          <p style={{ margin: 0, fontSize: "0.88rem", color: "var(--shell-muted)" }}>
            <span data-testid="mock-badge" className="status-pill warn">
              MOCK
            </span>{" "}
            Sample teleop data shown while the robot bridge is not connected. It clears
            automatically once yahboom-mcp reports ready.
          </p>
        </div>
      )}

      {mockMode && (
        <section className="page-card" data-testid="onboarding-cue">
          <h2>Complete onboarding — connect Boomy</h2>
          <p style={{ margin: "0 0 1rem", color: "var(--shell-muted)", fontSize: "0.9rem" }}>
            Start the robot bridge (yahboom-mcp on port 10892) and restart this backend, or drive
            the vboomy virtual twin without hardware.
          </p>
          <a className="btn danger" href="#/settings">
            Open setup guide
          </a>
        </section>
      )}

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
          <dd>{framesIn}</dd>
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

        <div className="tool-row" data-testid="claim-row">
          <div style={{ flex: 1, minWidth: "10rem" }}>
            <label htmlFor="operator-id">Operator claim</label>
            <input
              id="operator-id"
              value={operatorId}
              onChange={(e) => setOperatorId(e.target.value)}
              placeholder="Your name / operator id"
              disabled={!!claimToken}
              style={{ marginTop: "0.25rem", width: "100%" }}
            />
          </div>
          {claimToken ? (
            <button type="button" className="btn secondary" onClick={() => void releaseClaim()}>
              Release
            </button>
          ) : (
            <button
              type="button"
              className="btn"
              disabled={claiming || !operatorId.trim()}
              onClick={() => void claimRobot()}
              data-testid="claim-button"
            >
              {claiming ? "Claiming…" : "Claim robot"}
            </button>
          )}
        </div>
        {claimToken && (
          <p style={{ margin: "0.5rem 0 0", fontSize: "0.8rem", color: "var(--shell-muted)" }}>
            Robot claimed. The teleop socket requires this token; e-stop always works.
          </p>
        )}

        <button
          type="button"
          className="btn"
          disabled={!vrSupported || entering || !claimToken}
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
