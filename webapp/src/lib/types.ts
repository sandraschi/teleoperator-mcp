export interface LogEntry {
  id: string;
  timestamp: string;
  level: string;
  kind: string;
  detail: string;
  meta: Record<string, unknown>;
}

export interface LogsResponse {
  entries: LogEntry[];
  total: number;
  limit: number;
  offset: number;
  max_entries: number;
  sort: string;
}

export interface Capabilities {
  status: string;
  server: { name: string; version: string; fastmcp: string };
  tool_surface: {
    total: number;
    portmanteau_count: number;
    atomic_count: number;
    portmanteau_tools: string[];
    atomic_tools: string[];
  };
  features: Record<string, boolean>;
  inventory: Record<string, string[]>;
  runtime: Record<string, string | number | boolean>;
  timestamp: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  uptime_s: number;
  teleop?: {
    active?: boolean;
    frames_in?: number;
    robot?: string;
    display_name?: string;
  };
  livekit?: { running?: boolean };
}
