import { create } from "zustand";
import { API_BASE } from "./lib/api";

interface BackendState {
  online: boolean | null;
  toolCount: number;
  uptime: number;
  lastCheck: number;
  setOnline: (online: boolean) => void;
  setToolCount: (count: number) => void;
  setUptime: (uptime: number) => void;
  checkHealth: () => Promise<void>;
}

export const useBackendStore = create<BackendState>((set) => ({
  online: null,
  toolCount: 0,
  uptime: 0,
  lastCheck: 0,
  setOnline: (online: boolean) => set({ online, lastCheck: Date.now() }),
  setToolCount: (count: number) => set({ toolCount: count }),
  setUptime: (uptime: number) => set({ uptime }),
  checkHealth: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/health`);
      if (!res.ok) {
        set({ online: false, lastCheck: Date.now() });
        return;
      }
      const data = await res.json();
      set({
        online: data.status === "ok",
        toolCount: 0,
        uptime: data.uptime_s ?? 0,
        lastCheck: Date.now(),
      });
    } catch {
      set({ online: false, lastCheck: Date.now() });
    }
  },
}));
