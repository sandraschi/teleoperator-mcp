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

export interface RobotCatalogEntry {
  status: string;
  robot_id: string;
  display_name: string;
  has_base?: boolean;
  has_arms?: boolean;
  has_legs?: boolean;
  hand_type?: string;
  balance_risk?: boolean;
  virtual_twin?: boolean;
  platform?: string;
  message?: string;
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
    robots?: Record<string, RobotCatalogEntry>;
  };
  livekit?: { running?: boolean };
  onboarding?: {
    configured: boolean;
    service: string;
    url: string;
  };
}
