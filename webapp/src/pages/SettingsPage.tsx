import { useEffect } from "react";
import { useLlmStore } from "../store/llm";

export function SettingsPage() {
  const providers = useLlmStore((s) => s.providers);
  const selectedProvider = useLlmStore((s) => s.selectedProvider);
  const selectedModel = useLlmStore((s) => s.selectedModel);
  const gpu = useLlmStore((s) => s.gpu);
  const discover = useLlmStore((s) => s.discover);
  const selectProvider = useLlmStore((s) => s.selectProvider);
  const selectModel = useLlmStore((s) => s.selectModel);

  useEffect(() => {
    void discover();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const anyUp = providers.some((p) => p.status === "online");
  const probing = providers.some((p) => p.status === "checking");

  return (
    <>
      <section className="page-card" data-testid="settings-page">
        <h2>Local LLM — Glom On</h2>
        <p style={{ margin: "0 0 1rem", fontSize: "0.88rem", color: "var(--shell-muted)" }}>
          Auto-discovery of local inference engines. Teleop does not require LLM; reserved for
          future agent assist.
        </p>
        {probing && (
          <div className="skeleton" data-testid="llm-probing" style={{ height: "3rem" }} />
        )}
        {!probing && !anyUp && !gpu && (
          <p data-testid="llm-empty" style={{ color: "var(--shell-muted)" }}>
            No local LLM detected. Start <code>ollama serve</code> or LM Studio, then retry.
          </p>
        )}
        {gpu && (
          <div className="tool-row" data-testid="gpu-status">
            <div>
              <strong>{gpu.name}</strong>
              <div style={{ fontSize: "0.78rem", color: "var(--shell-muted)" }}>
                {gpu.vram_gb} GB VRAM detected
              </div>
            </div>
            <span className="status-pill ok">GPU</span>
          </div>
        )}
        {gpu && !anyUp && (
          <p className="onboarding-cue" data-testid="gpu-opportunity">
            NVIDIA GPU detected but no local LLM is running. Start <code>ollama serve</code> or LM
            Studio to enable local chat.
          </p>
        )}
        {providers.map((p) => (
          <div key={p.name} className="tool-row">
            <div>
              <strong>{p.label}</strong>
              <div style={{ fontSize: "0.78rem", color: "var(--shell-muted)" }}>
                {p.url} — {p.status}
                {p.models?.length ? ` · ${p.models.join(", ")}` : ""}
              </div>
            </div>
            <span className={`status-pill ${p.status === "online" ? "ok" : "warn"}`}>
              {p.status}
            </span>
          </div>
        ))}
        <div className="field" style={{ marginTop: "1rem" }}>
          <label htmlFor="llm-pref">Provider (stored locally)</label>
          <select
            id="llm-pref"
            data-testid="llm-provider-select"
            value={selectedProvider}
            onChange={(e) => selectProvider(e.target.value)}
          >
            <option value="none">None</option>
            {providers.map((p) => (
              <option key={p.name} value={p.name} disabled={p.status !== "online"}>
                {p.label}
              </option>
            ))}
          </select>
        </div>
        {selectedProvider !== "none" && (
          <div className="field" style={{ marginTop: "0.75rem" }}>
            <label htmlFor="llm-model">Model</label>
            <select
              id="llm-model"
              data-testid="llm-model-select"
              value={selectedModel}
              onChange={(e) => selectModel(e.target.value)}
            >
              {providers
                .find((p) => p.name === selectedProvider)
                ?.models.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
            </select>
          </div>
        )}
        <div style={{ marginTop: "1rem" }}>
          <button type="button" className="btn secondary" onClick={() => void discover()}>
            Re-scan local LLM
          </button>
        </div>
      </section>

      <section className="page-card">
        <h2>Runtime</h2>
        <dl className="debug" style={{ margin: 0 }}>
          <dt>Webapp port</dt>
          <dd>10900 (Vite)</dd>
          <dt>Backend port</dt>
          <dd>10901 (FastAPI + MCP)</dd>
          <dt>Video return</dt>
          <dd>LiveKit :15580</dd>
          <dt>Robot adapter</dt>
          <dd>yahboom-mcp :10892</dd>
        </dl>
      </section>
    </>
  );
}
