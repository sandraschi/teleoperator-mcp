import { useEffect, useState } from "react";
import { API_BASE } from "../lib/api";

interface FleetApp {
  name: string;
  port: number | null;
  desc: string;
  url: string;
  known?: boolean;
}

const FALLBACK_APPS: FleetApp[] = [
  {
    name: "teleoperator-mcp",
    port: 10900,
    desc: "WebXR teleop gateway (this app)",
    url: "/",
    known: true,
  },
  {
    name: "yahboom-mcp",
    port: 10892,
    desc: "Boomy ROS 2 robot control",
    url: "http://localhost:10892",
    known: true,
  },
  {
    name: "devices-mcp",
    port: 10870,
    desc: "Fleet device inventory",
    url: "http://localhost:10870",
    known: true,
  },
  {
    name: "bookmarks-mcp",
    port: 10880,
    desc: "Browser bookmarks + fleet docs RAG",
    url: "http://localhost:10880",
    known: true,
  },
  {
    name: "mcp-central-docs",
    port: null,
    desc: "Pico revive pack, WEBXR, teleop runbooks",
    url: "https://github.com/sandraschi/mcp-central-docs/tree/main/pico",
    known: true,
  },
];

export function AppsPage() {
  const [apps, setApps] = useState<FleetApp[]>(FALLBACK_APPS);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/fleet/apps`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as { apps?: FleetApp[] };
        if (!cancelled && Array.isArray(data.apps) && data.apps.length > 0) {
          setApps(data.apps);
        }
      } catch {
        // Backend fleet catalog unavailable - keep the local fallback list.
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const known = apps.filter((a) => a.known !== false);
  const experimental = apps.filter((a) => a.known === false);

  return (
    <section className="page-card" data-testid="apps-page">
      <h2>Fleet discovery</h2>
      <p style={{ margin: "0 0 1rem", fontSize: "0.88rem", color: "var(--shell-muted)" }}>
        Local MCP webapps on Goliath. Tailscale Serve URLs work on Pico when logged in.
      </p>
      {loading && (
        <div className="skeleton" data-testid="apps-loading" style={{ height: "3rem" }} />
      )}
      {!loading && (
        <div className="table-wrap">
          <table className="data-table" data-testid="apps-table">
            <thead>
              <tr>
                <th>Service</th>
                <th>Port</th>
                <th>Description</th>
                <th>Open</th>
              </tr>
            </thead>
            <tbody>
              {known.map((app) => (
                <tr key={app.name} data-testid={`app-row-${app.name}`}>
                  <td>
                    <code>{app.name}</code>
                  </td>
                  <td>{app.port ?? "—"}</td>
                  <td>{app.desc}</td>
                  <td>
                    <a
                      href={app.url}
                      target={app.url.startsWith("http") ? "_blank" : undefined}
                      rel="noreferrer"
                    >
                      Open
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {experimental.length > 0 && (
        <section
          className="page-card"
          data-testid="apps-experimental"
          style={{ marginTop: "1rem" }}
        >
          <h3>Experimental (not in fleet registry)</h3>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Port</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {experimental.map((app) => (
                  <tr key={app.name}>
                    <td>
                      <code>{app.name}</code>
                    </td>
                    <td>{app.port ?? "—"}</td>
                    <td>{app.desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
      <p style={{ margin: "1rem 0 0", fontSize: "0.8rem", color: "var(--shell-muted)" }}>
        glama.json registered at repo root for Glama discovery protocol.
      </p>
    </section>
  );
}
