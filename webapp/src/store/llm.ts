import { create } from "zustand";

export interface LlmProviderProbe {
  name: string;
  label: string;
  url: string;
  status: "online" | "offline" | "checking";
  models: string[];
}

interface LlmState {
  providers: LlmProviderProbe[];
  selectedProvider: string;
  selectedModel: string;
  discover: () => Promise<void>;
  selectProvider: (name: string) => void;
  selectModel: (model: string) => void;
}

const PROVIDER_DEFS: Array<{ name: string; label: string; url: string }> = [
  { name: "ollama", label: "Ollama", url: "http://127.0.0.1:11434/api/tags" },
  { name: "lmstudio", label: "LM Studio", url: "http://127.0.0.1:1234/v1/models" },
];

function readStorage(key: string, fallback: string): string {
  try {
    return localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}

function writeStorage(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* storage unavailable */
  }
}

function extractModels(name: string, data: unknown): string[] {
  if (name === "ollama") {
    const models = (data as { models?: Array<{ name: string }> })?.models;
    return models ? models.map((m) => m.name).slice(0, 20) : [];
  }
  const models = (data as { data?: Array<{ id: string }> })?.data;
  return models ? models.map((m) => m.id).slice(0, 20) : [];
}

export const useLlmStore = create<LlmState>((set, get) => ({
  providers: PROVIDER_DEFS.map((p) => ({
    ...p,
    status: "checking" as const,
    models: [],
  })),
  selectedProvider: readStorage("llm_provider", "ollama"),
  selectedModel: readStorage("llm_model", ""),

  discover: async () => {
    const results = await Promise.all(
      PROVIDER_DEFS.map(async (p) => {
        try {
          const res = await fetch(p.url, { signal: AbortSignal.timeout(2500) });
          if (!res.ok) {
            return { ...p, status: "offline" as const, models: [] as string[] };
          }
          const data = await res.json();
          return { ...p, status: "online" as const, models: extractModels(p.name, data) };
        } catch {
          return { ...p, status: "offline" as const, models: [] as string[] };
        }
      }),
    );
    set({ providers: results });

    const { selectedProvider, selectedModel } = get();
    const active = results.find((p) => p.name === selectedProvider);
    if (active?.status === "online" && active.models.length > 0) {
      if (!selectedModel || !active.models.includes(selectedModel)) {
        const first = active.models[0];
        set({ selectedModel: first });
        writeStorage("llm_model", first);
      }
    }
  },

  selectProvider: (name: string) => {
    set({ selectedProvider: name, selectedModel: "" });
    writeStorage("llm_provider", name);
    const active = get().providers.find((p) => p.name === name);
    if (active?.models.length) {
      const first = active.models[0];
      set({ selectedModel: first });
      writeStorage("llm_model", first);
    }
  },

  selectModel: (model: string) => {
    set({ selectedModel: model });
    writeStorage("llm_model", model);
  },
}));
