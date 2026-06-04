const FLEET_APPS = [
  {
    name: "teleoperator-mcp",
    port: 10900,
    desc: "WebXR teleop gateway (this app)",
    url: "/",
  },
  {
    name: "yahboom-mcp",
    port: 10893,
    desc: "Boomy ROS 2 robot control",
    url: "http://localhost:10893",
  },
  {
    name: "devices-mcp",
    port: 10870,
    desc: "Fleet device inventory",
    url: "http://localhost:10870",
  },
  {
    name: "bookmarks-mcp",
    port: 10880,
    desc: "Browser bookmarks + fleet docs RAG",
    url: "http://localhost:10880",
  },
  {
    name: "mcp-central-docs",
    port: null,
    desc: "Pico revive pack, WEBXR, teleop runbooks",
    url: "https://github.com/sandraschi/mcp-central-docs/tree/main/pico",
  },
];

export function AppsPage() {
  return (
    <section className="page-card">
      <h2>Fleet discovery</h2>
      <p style={{ margin: "0 0 1rem", fontSize: "0.88rem", color: "var(--shell-muted)" }}>
        Local MCP webapps on Goliath. Tailscale Serve URLs work on Pico when logged in.
      </p>
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Service</th>
              <th>Port</th>
              <th>Description</th>
              <th>Open</th>
            </tr>
          </thead>
          <tbody>
            {FLEET_APPS.map((app) => (
              <tr key={app.name}>
                <td><code>{app.name}</code></td>
                <td>{app.port ?? "—"}</td>
                <td>{app.desc}</td>
                <td>
                  <a href={app.url} target={app.url.startsWith("http") ? "_blank" : undefined} rel="noreferrer">
                    Open
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p style={{ margin: "1rem 0 0", fontSize: "0.8rem", color: "var(--shell-muted)" }}>
        glama.json registered at repo root for Glama discovery protocol.
      </p>
    </section>
  );
}
