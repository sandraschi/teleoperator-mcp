import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Capabilities } from "./types";

interface CapabilitiesContextValue {
  caps: Capabilities | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

const CapabilitiesContext = createContext<CapabilitiesContextValue | null>(null);

export function CapabilitiesProvider({ children }: { children: ReactNode }) {
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/capabilities");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setCaps((await res.json()) as Capabilities);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const value = useMemo(
    () => ({ caps, loading, error, refresh }),
    [caps, loading, error, refresh],
  );

  return <CapabilitiesContext.Provider value={value}>{children}</CapabilitiesContext.Provider>;
}

export function useCapabilities(): CapabilitiesContextValue {
  const ctx = useContext(CapabilitiesContext);
  if (!ctx) throw new Error("useCapabilities must be used within CapabilitiesProvider");
  return ctx;
}
