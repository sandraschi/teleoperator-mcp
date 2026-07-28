import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useCapabilities } from "../lib/capabilities";
import { LoggerPanel } from "./LoggerPanel";
import { useState } from "react";
import { useZoom } from "../hooks/useZoom";

const NAV = [
  { to: "/", label: "Home", end: true },
  { to: "/tools", label: "Tools" },
  { to: "/logs", label: "Logs" },
  { to: "/apps", label: "Apps" },
  { to: "/settings", label: "Settings" },
  { to: "/help", label: "Help" },
];

const PAGE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/tools": "MCP Tools",
  "/logs": "Event Logs",
  "/apps": "Fleet Apps",
  "/settings": "Settings",
  "/help": "Help",
};

export function Shell() {
  useZoom();
  const { pathname } = useLocation();
  const { caps, loading, error } = useCapabilities();
  const [loggerCollapsed, setLoggerCollapsed] = useState(false);

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
          <span
            data-testid="backend-dot"
            className={`status-pill ${error ? "warn" : "ok"}`}
          >
            MCP {loading ? "…" : error ? "offline" : "ok"}
          </span>
          {caps && (
            <span className="status-pill ok" data-testid="kpi-server">{caps.tool_surface.total} tools</span>
          )}
        </div>
      </header>

      <main className="iron-main">
        <Outlet />
      </main>

      <LoggerPanel
        collapsed={loggerCollapsed}
        onToggle={() => setLoggerCollapsed((v) => !v)}
      />
    </div>
  );
}
