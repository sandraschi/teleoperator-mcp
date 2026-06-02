import * as THREE from "three";
import type { HudState } from "./types";

/** Chin-strip HUD in head space - below gaze, does not block center FOV. */
export class XrHud {
  private group: THREE.Group;
  private canvas: HTMLCanvasElement;
  private texture: THREE.CanvasTexture;
  private mesh: THREE.Mesh;
  private state: HudState;
  private lastLine = "";

  constructor(camera: THREE.Camera) {
    this.state = {
      wsConnected: false,
      videoLive: false,
      rttMs: null,
      deadman: false,
      estop: false,
      takeoverHeld: false,
      seq: 0,
      panTilt: "--",
    };

    this.canvas = document.createElement("canvas");
    this.canvas.width = 512;
    this.canvas.height = 64;
    this.texture = new THREE.CanvasTexture(this.canvas);

    const geo = new THREE.PlaneGeometry(0.45, 0.056);
    const mat = new THREE.MeshBasicMaterial({
      map: this.texture,
      transparent: true,
      opacity: 0.72,
      depthTest: false,
    });
    this.mesh = new THREE.Mesh(geo, mat);

    this.group = new THREE.Group();
    this.group.add(this.mesh);
    this.group.position.set(0, -0.28, -0.55);
    camera.add(this.group);

    this.redraw();
  }

  update(state: Partial<HudState>): void {
    this.state = { ...this.state, ...state };
    this.redraw();
  }

  dispose(): void {
    this.texture.dispose();
    this.mesh.geometry.dispose();
    (this.mesh.material as THREE.Material).dispose();
  }

  private redraw(): void {
    const ctx = this.canvas.getContext("2d");
    if (!ctx) return;

    const rtt = this.state.rttMs != null ? `${Math.round(this.state.rttMs)} ms` : "--";
    const drive = this.state.estop
      ? "ESTOP"
      : this.state.takeoverHeld
        ? "TAKEOVER"
        : this.state.deadman
          ? "DRIVE"
          : "idle";
    const vid = this.state.videoLive ? "VID" : "vid--";
    const line = `${vid} | WS ${rtt} | ${drive} | PTZ ${this.state.panTilt} | #${this.state.seq}`;
    if (line === this.lastLine) {
      return;
    }
    this.lastLine = line;

    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    ctx.fillStyle = "rgba(12, 14, 24, 0.88)";
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    const dot = this.state.wsConnected ? "#4ade80" : "#f87171";
    ctx.fillStyle = dot;
    ctx.beginPath();
    ctx.arc(18, 32, 6, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = this.state.estop ? "#f87171" : this.state.takeoverHeld ? "#fbbf24" : "#e2e8f0";
    ctx.font = "18px system-ui, sans-serif";
    ctx.fillText(line, 36, 38);

    this.texture.needsUpdate = true;
  }
}
