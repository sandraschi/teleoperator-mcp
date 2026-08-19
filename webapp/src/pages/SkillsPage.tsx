import { useEffect, useState } from "react";
import { API_BASE } from "../lib/api";

interface Skill {
  name: string;
  description: string;
}

export function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/skills`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as Skill[];
        if (!cancelled) setSkills(Array.isArray(data) ? data : []);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="page-card" data-testid="skills-page">
      <h2>Supervisor skills</h2>
      <p style={{ margin: "0 0 1rem", fontSize: "0.88rem", color: "var(--shell-muted)" }}>
        Skill-first chat composition — the Chat panel loads the first skill as its base system
        prompt.
      </p>
      {loading && (
        <div className="skeleton" data-testid="skills-loading" style={{ height: "3rem" }} />
      )}
      {error && (
        <p data-testid="skills-error" style={{ color: "var(--danger, #ef4444)" }}>
          Failed to load skills: {error}. Is the backend running?
        </p>
      )}
      {!loading && !error && skills.length === 0 && (
        <p data-testid="skills-empty">No skills reported by /api/skills.</p>
      )}
      {!loading &&
        !error &&
        skills.map((s) => (
          <div key={s.name} className="tool-row" data-testid={`skill-row-${s.name}`}>
            <div>
              <strong>{s.name}</strong>
              <div style={{ fontSize: "0.78rem", color: "var(--shell-muted)" }}>
                {s.description}
              </div>
            </div>
            <span className="status-pill ok">available</span>
          </div>
        ))}
    </section>
  );
}
