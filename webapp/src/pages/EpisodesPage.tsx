import { useEffect, useState } from "react";
import { API_BASE } from "../lib/api";

interface Episode {
  episode_index: number;
  session_id: string | null;
  robot_id: string | null;
  length: number;
  task: string;
  path: string;
}

interface EpisodeDetail {
  episode_index: number;
  frames: Array<{ frame_index: number; action: number[]; producer_id: string; timestamp: number }>;
}

const CURATION_LABELS = ["keep", "reject", "uncertain"];

export function EpisodesPage() {
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [detail, setDetail] = useState<EpisodeDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [label, setLabel] = useState("keep");
  const [note, setNote] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/episodes`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as { episodes: Episode[] };
      setEpisodes(data.episodes ?? []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const openEpisode = async (idx: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/episodes/${idx}`);
      const data = (await res.json()) as { success?: boolean; episode?: EpisodeDetail };
      if (data.success && data.episode) setDetail(data.episode);
    } catch {
      /* ignore */
    }
  };

  const curate = async (idx: number) => {
    try {
      await fetch(`${API_BASE}/api/v1/episodes/${idx}/curate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ label, note }),
      });
      setDetail(null);
      void load();
    } catch {
      /* ignore */
    }
  };

  return (
    <section className="page-card" data-testid="episodes-page">
      <h2>Episode library — replay + curation</h2>
      <p style={{ margin: "0 0 1rem", fontSize: "0.88rem", color: "var(--shell-muted)" }}>
        Recorded teleop sessions (LeRobot JSONL). Open one to replay its frames, then label it keep
        / reject / uncertain for the data flywheel.
      </p>
      {loading && (
        <div className="skeleton" data-testid="episodes-loading" style={{ height: "3rem" }} />
      )}
      {error && (
        <p data-testid="episodes-error" style={{ color: "var(--danger, #ef4444)" }}>
          Failed to load episodes: {error}
        </p>
      )}
      {!loading && !error && episodes.length === 0 && (
        <p data-testid="episodes-empty">
          No episodes yet. Run a teleop session, then check back — the flywheel starts empty.
        </p>
      )}
      {episodes.map((e) => (
        <div
          key={e.episode_index}
          className="tool-row"
          data-testid={`episode-row-${e.episode_index}`}
        >
          <div>
            <strong>episode_{e.episode_index.toString().padStart(6, "0")}</strong>
            <div style={{ fontSize: "0.78rem", color: "var(--shell-muted)" }}>
              {e.robot_id} · {e.length} frames · {e.task}
            </div>
          </div>
          <button
            type="button"
            className="btn secondary"
            onClick={() => void openEpisode(e.episode_index)}
          >
            Replay
          </button>
        </div>
      ))}

      {detail && (
        <section className="page-card" data-testid="episode-detail" style={{ marginTop: "1rem" }}>
          <h3>
            Episode {detail.episode_index} — {detail.frames.length} frames
          </h3>
          <div
            style={{ fontSize: "0.82rem", color: "var(--shell-muted)", marginBottom: "0.75rem" }}
          >
            First 10 resolved actions (linear, angular, linear_y, pan, tilt):
          </div>
          <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: "0.78rem" }}>
            {detail.frames
              .slice(0, 10)
              .map((f) => JSON.stringify(f.action))
              .join("\n")}
          </pre>
          <div className="filters-row" style={{ marginTop: "0.75rem" }}>
            <div className="field">
              <label htmlFor="curate-label">Label</label>
              <select id="curate-label" value={label} onChange={(e) => setLabel(e.target.value)}>
                {CURATION_LABELS.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </div>
            <div className="field" style={{ flex: 1, minWidth: "12rem" }}>
              <label htmlFor="curate-note">Note</label>
              <input
                id="curate-note"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="e.g. clean base demo, no robot"
              />
            </div>
            <button
              type="button"
              className="btn"
              onClick={() => void curate(detail.episode_index)}
              data-testid="curate-submit"
            >
              Save curation
            </button>
            <button type="button" className="btn secondary" onClick={() => setDetail(null)}>
              Close
            </button>
          </div>
        </section>
      )}
    </section>
  );
}
