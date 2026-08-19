import { useCallback, useEffect, useRef, useState } from "react";
import type { LogEntry } from "../lib/types";

interface LoggerPanelProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function LoggerPanel({ collapsed, onToggle }: LoggerPanelProps) {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [tail, setTail] = useState(true);
  const [afterId, setAfterId] = useState<string | null>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  const userScrolledRef = useRef(false);

  const fetchLogs = useCallback(async () => {
    try {
      const params = new URLSearchParams({ limit: "40", sort: "desc" });
      if (tail && afterId) params.set("after_id", afterId);
      const res = await fetch(`/api/logs?${params}`);
      if (!res.ok) return;
      const data = await res.json();
      const batch = (data.entries ?? []) as LogEntry[];
      if (tail && afterId && batch.length) {
        setEntries((prev) => {
          const ids = new Set(prev.map((e) => e.id));
          const merged = [...batch.filter((e) => !ids.has(e.id)), ...prev];
          return merged.slice(0, 200);
        });
        setAfterId(batch[0]?.id ?? afterId);
      } else if (!afterId) {
        setEntries(batch);
        if (batch[0]) setAfterId(batch[0].id);
      }
    } catch {
      /* backend offline */
    }
  }, [tail, afterId]);

  useEffect(() => {
    void fetchLogs();
    const id = window.setInterval(() => void fetchLogs(), 2000);
    return () => window.clearInterval(id);
  }, [fetchLogs]);

  useEffect(() => {
    const el = bodyRef.current;
    if (!el || userScrolledRef.current || collapsed) return;
    el.scrollTop = 0;
  }, [entries, collapsed]);

  const onScroll = () => {
    const el = bodyRef.current;
    if (!el) return;
    userScrolledRef.current = el.scrollTop > 24;
  };

  return (
    <aside className={`iron-logger${collapsed ? " collapsed" : ""}`} aria-label="Event logger">
      <div className="iron-logger__header">
        <strong>Logger</strong>
        <label style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
          <input
            type="checkbox"
            checked={tail}
            onChange={(e) => {
              setTail(e.target.checked);
              userScrolledRef.current = false;
            }}
          />
          Live tail
        </label>
        <button type="button" onClick={onToggle} aria-expanded={collapsed ? "false" : "true"}>
          {collapsed ? "Expand" : "Collapse"}
        </button>
      </div>
      {!collapsed && (
        <div className="iron-logger__body" ref={bodyRef} onScroll={onScroll}>
          {entries.length === 0 && <div className="log-line level-INFO">No log entries yet.</div>}
          {entries.map((e) => (
            <div key={e.id} className={`log-line level-${e.level}`}>
              <span style={{ opacity: 0.6 }}>{e.timestamp.slice(11, 19)}</span> [{e.kind}]{" "}
              {e.detail}
            </div>
          ))}
        </div>
      )}
    </aside>
  );
}
