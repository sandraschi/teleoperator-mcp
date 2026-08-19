import type { PoseFrame } from "./types";

export type PoseAck = { ok: boolean; seq?: number; error?: string; watchdog?: boolean };

export class PoseStream {
  private ws: WebSocket | null = null;
  private seq = 0;
  private heartbeatTimer: number | null = null;
  private reconnectTimer: number | null = null;
  private reconnectAttempt = 0;
  private intentionalClose = false;
  private readonly maxReconnectDelayMs = 30_000;
  private url: string;

  onAck: ((ack: PoseAck) => void) | null = null;
  onOpen: (() => void) | null = null;
  onClose: (() => void) | null = null;

  constructor(robot: string, claimToken = "") {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const tokenParam = claimToken ? `&token=${encodeURIComponent(claimToken)}` : "";
    this.url = `${proto}//${host}/ws/teleop?robot=${encodeURIComponent(robot)}${tokenParam}`;
  }

  connect(): void {
    this.intentionalClose = false;
    this.openSocket();
  }

  disconnect(): void {
    this.intentionalClose = true;
    if (this.reconnectTimer) window.clearTimeout(this.reconnectTimer);
    if (this.heartbeatTimer) window.clearInterval(this.heartbeatTimer);
    this.reconnectTimer = null;
    this.heartbeatTimer = null;
    this.ws?.close();
    this.ws = null;
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get frameSeq(): number {
    return this.seq;
  }

  sendFrame(frame: Omit<PoseFrame, "v" | "t" | "seq">): void {
    if (!this.connected) return;
    this.seq += 1;
    const payload: PoseFrame = {
      v: 1,
      t: Date.now(),
      seq: this.seq,
      ...frame,
    };
    this.ws?.send(JSON.stringify(payload));
  }

  sendEstop(): void {
    if (!this.connected) return;
    this.ws?.send(JSON.stringify({ v: 1, type: "estop", t: Date.now() }));
  }

  sendTakeover(): void {
    if (!this.connected) return;
    this.ws?.send(JSON.stringify({ v: 1, type: "takeover", t: Date.now() }));
  }

  private openSocket(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.ws = new WebSocket(this.url);
    this.ws.onopen = () => {
      this.reconnectAttempt = 0;
      this.onOpen?.();
      this.heartbeatTimer = window.setInterval(() => this.sendPresence(), 500);
    };
    this.ws.onclose = () => {
      if (this.heartbeatTimer) window.clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
      this.onClose?.();
      if (!this.intentionalClose) {
        this.scheduleReconnect();
      }
    };
    this.ws.onmessage = (ev) => {
      try {
        const ack = JSON.parse(String(ev.data)) as PoseAck;
        this.onAck?.(ack);
      } catch {
        /* ignore */
      }
    };
  }

  private scheduleReconnect(): void {
    const delay = Math.min(1000 * 2 ** this.reconnectAttempt, this.maxReconnectDelayMs);
    this.reconnectAttempt += 1;
    this.reconnectTimer = window.setTimeout(() => this.openSocket(), delay);
  }

  private sendHeartbeat(): void {
    if (!this.connected) return;
    this.ws?.send(JSON.stringify({ v: 1, type: "heartbeat", t: Date.now() }));
  }

  private sendPresence(): void {
    if (!this.connected) return;
    // Operator-presence deadman: server e-stops if this pulse stops arriving.
    this.ws?.send(JSON.stringify({ v: 1, type: "presence", t: Date.now() }));
  }
}
