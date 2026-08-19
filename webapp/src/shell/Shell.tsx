import { useCallback, useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useTauriBackendListener } from "../hooks/useTauriBackendListener";
import { useZoom } from "../hooks/useZoom";
import { useCapabilities } from "../lib/capabilities";
import { LoggerPanel } from "./LoggerPanel";

const NAV = [
  { to: "/", label: "Home", end: true },
  { to: "/tools", label: "Tools" },
  { to: "/inbox", label: "Inbox" },
  { to: "/skills", label: "Skills" },
  { to: "/logs", label: "Logs" },
  { to: "/apps", label: "Apps" },
  { to: "/settings", label: "Settings" },
  { to: "/help", label: "Help" },
];

const PAGE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/tools": "MCP Tools",
  "/inbox": "Activity Inbox",
  "/skills": "Supervisor Skills",
  "/logs": "Event Logs",
  "/apps": "Fleet Apps",
  "/settings": "Settings",
  "/help": "Help",
};

export function Shell() {
  const { zoomLevel } = useZoom();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { caps, loading, error, refresh } = useCapabilities();
  const [loggerCollapsed, setLoggerCollapsed] = useState(false);

  const handleBackendReady = useCallback(() => {
    void refresh();
  }, [refresh]);
  const handleBackendError = useCallback((message: string) => {
    console.warn(message);
  }, []);

  useTauriBackendListener({ onReady: handleBackendReady, onError: handleBackendError });

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!e.ctrlKey) return;
      if (e.key.toLowerCase() === "l") {
        e.preventDefault();
        setLoggerCollapsed((v) => !v);
      } else if (e.key.toLowerCase() === "h") {
        e.preventDefault();
        navigate("/help");
      } else if (e.key.toLowerCase() === "k") {
        e.preventDefault();
        navigate("/logs");
        // Focus the logs search after navigation.
        window.setTimeout(() => {
          const el = document.getElementById("log-search");
          if (el) el.focus();
        }, 50);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [navigate]);

  const title = PAGE_TITLES[pathname] ?? "Teleoperator";

  return (
    <div className="iron-shell" data-testid="dashboard">
      <aside className="iron-sidebar">
        <div className="iron-sidebar__brand">
          <h1>Teleoperator</h1>
          <p>WebXR → Boomy · v0.1.0</p>
        </div>
        <nav className="iron-nav" aria-label="Primary">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => (isActive ? "active" : undefined)}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <header className="iron-topbar">
        <h2 className="iron-topbar__title">{title}</h2>
        <span className="iron-topbar__crumb">teleoperator-mcp</span>
        <div className="iron-topbar__status">
          <span data-testid="backend-dot" className={`status-pill ${error ? "warn" : "ok"}`}>
            MCP {loading ? "…" : error ? "offline" : "ok"}
          </span>
          {caps && (
            <span className="status-pill ok" data-testid="kpi-server">
              {caps.tool_surface.total} tools
            </span>
          )}
          <span
            className="status-pill"
            data-testid="zoom-indicator"
            title="Ctrl+Scroll zoom, Ctrl+0 reset"
          >
            {Math.round(zoomLevel * 100)}%
          </span>
        </div>
      </header>

      <main className="iron-main">
        <Outlet />
      </main>

      <LoggerPanel collapsed={loggerCollapsed} onToggle={() => setLoggerCollapsed((v) => !v)} />
    </div>
  );
}
