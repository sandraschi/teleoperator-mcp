import { Room, RoomEvent, Track } from "livekit-client";
import * as THREE from "three";

export type VideoConnectState = "off" | "connecting" | "live" | "error";

/** Subscribe to Boomy camera track published on LiveKit; map to center FOV plane. */
export class LiveKitVideoPlane {
  private room: Room | null = null;
  private mesh: THREE.Mesh;
  private material: THREE.MeshBasicMaterial;
  private texture: THREE.VideoTexture | null = null;
  private videoEl: HTMLVideoElement | null = null;
  private state: VideoConnectState = "off";
  private lastError: string | null = null;
  onLive: (() => void) | null = null;

  constructor(scene: THREE.Scene) {
    this.material = new THREE.MeshBasicMaterial({ color: 0x111118 });
    this.mesh = new THREE.Mesh(new THREE.PlaneGeometry(1.6, 0.9), this.material);
    this.mesh.position.set(0, 0, -1.2);
    scene.add(this.mesh);
  }

  get connectState(): VideoConnectState {
    return this.state;
  }

  get error(): string | null {
    return this.lastError;
  }

  async connect(robot: string): Promise<boolean> {
    this.state = "connecting";
    this.lastError = null;

    try {
      const cfgRes = await fetch(`/api/v1/livekit/config?robot=${encodeURIComponent(robot)}`);
      if (!cfgRes.ok) {
        this.state = "off";
        return false;
      }
      const cfg = (await cfgRes.json()) as { enabled?: boolean; url?: string; room?: string };
      if (!cfg.enabled || !cfg.url || !cfg.room) {
        this.state = "off";
        return false;
      }

      const identity = `viewer-${robot}-${Date.now()}`;
      const tokenRes = await fetch("/api/v1/livekit/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identity, room: cfg.room, name: "Teleop Viewer" }),
      });
      if (!tokenRes.ok) {
        this.state = "error";
        this.lastError = `token HTTP ${tokenRes.status}`;
        return false;
      }
      const tokenPayload = (await tokenRes.json()) as {
        success?: boolean;
        token?: string;
        url?: string;
        message?: string;
      };
      if (!tokenPayload.success || !tokenPayload.token) {
        this.state = "error";
        this.lastError = tokenPayload.message ?? "token failed";
        return false;
      }

      const wsUrl = tokenPayload.url ?? cfg.url;
      this.room = new Room({ adaptiveStream: true, dynacast: true });

      this.room.on(RoomEvent.TrackSubscribed, (track) => {
        if (track.kind !== Track.Kind.Video || this.videoEl) {
          return;
        }
        const el = track.attach() as HTMLVideoElement;
        el.playsInline = true;
        el.muted = true;
        void el.play().catch(() => undefined);
        this.videoEl = el;
        this.texture = new THREE.VideoTexture(el);
        this.texture.colorSpace = THREE.SRGBColorSpace;
        this.material.map = this.texture;
        this.material.color.setHex(0xffffff);
        this.material.needsUpdate = true;
        this.state = "live";
        this.onLive?.();
      });

      this.room.on(RoomEvent.Disconnected, () => {
        if (this.state === "live") {
          this.state = "error";
          this.lastError = "disconnected";
        }
      });

      await this.room.connect(wsUrl, tokenPayload.token);
      return true;
    } catch (err) {
      this.state = "error";
      this.lastError = err instanceof Error ? err.message : String(err);
      return false;
    }
  }

  disconnect(): void {
    this.room?.disconnect();
    this.room = null;
    if (this.videoEl) {
      this.videoEl.srcObject = null;
      this.videoEl.remove();
      this.videoEl = null;
    }
    if (this.texture) {
      this.texture.dispose();
      this.texture = null;
    }
    this.material.map = null;
    this.material.color.setHex(0x111118);
    this.material.needsUpdate = true;
    this.state = "off";
  }
}
