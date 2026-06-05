import { useEffect, useState } from "react";

interface LlmProbe {
  name: string;
  url: string;
  status: "online" | "offline" | "checking";
  models?: string[];
}

export function SettingsPage() {
  const [providers, setProviders] = useState<LlmProbe[]>([
    { name: "Ollama", url: "http://127.0.0.1:11434/api/tags", status: "checking" },
    { name: "LM Studio", url: "http://127.0.0.1:1234/v1/models", status: "checking" },
  ]);
  const [preferred, setPreferred] = useState(() => localStorage.getItem("teleop-llm-provider") ?? "none");

  useEffect(() => {
    void (async () => {
      const next = await Promise.all(
        providers.map(async (p) => {
          try {
            const res = await fetch(p.url, { signal: AbortSignal.timeout(2500) });
            if (!res.ok) return { ...p, status: "offline" as const };
            const data = await res.json();
            const models =
              p.name === "Ollama"
                ? (data.models as { name: string }[] | undefined)?.map((m) => m.name).slice(0, 5)
                : (data.data as { id: string }[] | undefined)?.map((m) => m.id).slice(0, 5);
            return { ...p, status: "online" as const, models };
          } catch {
            return { ...p, status: "offline" as const };
          }
        }),
      );
      setProviders(next);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const savePreferred = (value: string) => {
    setPreferred(value);
    localStorage.setItem("teleop-llm-provider", value);
  };

  return (
    <>
      <section className="page-card">
        <h2>Local LLM — Glom On</h2>
        <p style={{ margin: "0 0 1rem", fontSize: "0.88rem", color: "var(--shell-muted)" }}>
          Auto-discovery of local inference engines. Teleop does not require LLM; reserved for future agent assist.
        </p>
        {providers.map((p) => (
          <div key={p.name} className="tool-row">
            <div>
              <strong>{p.name}</strong>
              <div style={{ fontSize: "0.78rem", color: "var(--shell-muted)" }}>
                {p.url} — {p.status}
                {p.models?.length ? ` · ${p.models.join(", ")}` : ""}
              </div>
            </div>
            <span className={`status-pill ${p.status === "online" ? "ok" : "warn"}`}>{p.status}</span>
          </div>
        ))}
        <div className="field" style={{ marginTop: "1rem" }}>
          <label htmlFor="llm-pref">Preferred provider (stored locally)</label>
          <select id="llm-pref" value={preferred} onChange={(e) => savePreferred(e.target.value)}>
            <option value="none">None</option>
            <option value="ollama">Ollama</option>
            <option value="lmstudio">LM Studio</option>
          </select>
        </div>
      </section>

      <section className="page-card">
        <h2>Runtime</h2>
        <dl className="debug" style={{ margin: 0 }}>
          <dt>Webapp port</dt>
          <dd>10900 (Vite)</dd>
          <dt>Backend port</dt>
          <dd>10901 (FastAPI + MCP)</dd>
          <dt>WebSocket</dt>
          <dd>/ws/teleop?robot=boomy | bumi | vboomy</dd>
        </dl>
      </section>
    </>
  );
}
