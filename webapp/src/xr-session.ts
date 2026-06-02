import * as THREE from "three";
import { XrHud } from "./hud";
import { LiveKitVideoPlane } from "./livekit-video";
import { PoseStream } from "./pose-stream";
import type { ControllerPose, HeadPose } from "./types";

const SEND_INTERVAL_MS = 1000 / 30;
const DEAD_ZONE = 0.12;
const SQUEEZE_THRESHOLD = 0.5;

function quatToHeadEuler(q: THREE.Quaternion): HeadPose {
  const e = new THREE.Euler().setFromQuaternion(q, "YXZ");
  return { yaw: e.y, pitch: e.x, roll: e.z };
}

function readController(source: XRInputSource | undefined): ControllerPose {
  if (!source?.gamepad) {
    return { connected: false, axes: [], buttons: {} };
  }
  const gp = source.gamepad;
  const axes = [...gp.axes].map((v) => (Math.abs(v) < DEAD_ZONE ? 0 : v));
  return {
    connected: true,
    axes,
    buttons: {
      trigger: gp.buttons[0]?.value ?? 0,
      squeeze: gp.buttons[1]?.value ?? 0,
    },
  };
}

function squeezeActive(controller: ControllerPose): boolean {
  return (controller.buttons.squeeze ?? 0) > SQUEEZE_THRESHOLD;
}

export class XrSession {
  private renderer: THREE.WebGLRenderer;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private stream: PoseStream;
  private video: LiveKitVideoPlane;
  private hud: XrHud | null = null;
  private session: XRSession | null = null;
  private refSpace: XRReferenceSpace | null = null;
  private lastSend = 0;
  private lastSentAt = 0;
  private rttMs: number | null = null;
  private squeezeHeld = false;
  private robotId: string;

  constructor(canvas: HTMLCanvasElement, robot: string) {
    this.robotId = robot;
    this.stream = new PoseStream(robot);
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.renderer.xr.enabled = true;

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.01, 20);
    this.scene.add(this.camera);

    this.video = new LiveKitVideoPlane(this.scene);

    this.stream.onOpen = () => this.hud?.update({ wsConnected: true });
    this.stream.onClose = () => this.hud?.update({ wsConnected: false });
    this.stream.onAck = (ack) => {
      this.rttMs = performance.now() - this.lastSentAt;
      if (ack.watchdog) {
        this.hud?.update({ estop: true, takeoverHeld: false });
      }
    };
  }

  async start(): Promise<void> {
    if (!navigator.xr) throw new Error("WebXR not available");
    this.session = await navigator.xr.requestSession("immersive-vr", {
      requiredFeatures: ["local-floor"],
    });
    await this.renderer.xr.setSession(this.session);
    this.refSpace = await this.session.requestReferenceSpace("local-floor");
    this.hud = new XrHud(this.camera);
    this.video.onLive = () => this.hud?.update({ videoLive: true });
    void this.video.connect(this.robotId);
    this.stream.connect();
    document.body.classList.add("in-xr");
    this.session.addEventListener("end", () => this.stop());
    this.renderer.setAnimationLoop((time, frame) => this.onFrame(time, frame));
  }

  stop(): void {
    this.stream.sendEstop();
    this.stream.disconnect();
    this.video.disconnect();
    this.hud?.dispose();
    this.hud = null;
    this.renderer.setAnimationLoop(null);
    document.body.classList.remove("in-xr");
    this.session?.end();
    this.session = null;
  }

  private onFrame(time: number, frame?: XRFrame): void {
    if (!frame || !this.refSpace) {
      this.renderer.render(this.scene, this.camera);
      return;
    }

    const pose = frame.getViewerPose(this.refSpace);
    let head: HeadPose = { yaw: 0, pitch: 0, roll: 0 };
    if (pose) {
      head = quatToHeadEuler(
        new THREE.Quaternion(
          pose.transform.orientation.x,
          pose.transform.orientation.y,
          pose.transform.orientation.z,
          pose.transform.orientation.w,
        ),
      );
    }

    const sources = this.session?.inputSources ?? [];
    const right = readController([...sources].find((s) => s.handedness === "right"));
    const left = readController([...sources].find((s) => s.handedness === "left"));
    const takeoverHeld = squeezeActive(right) || squeezeActive(left);

    if (takeoverHeld && !this.squeezeHeld) {
      this.stream.sendTakeover();
    }
    this.squeezeHeld = takeoverHeld;

    if (time - this.lastSend >= SEND_INTERVAL_MS) {
      this.lastSend = time;
      this.lastSentAt = performance.now();
      this.stream.sendFrame({ head, right, left });
    }

    this.hud?.update({
      rttMs: this.rttMs,
      videoLive: this.video.connectState === "live",
      deadman: (right.buttons.trigger ?? 0) > 0.5,
      estop: false,
      takeoverHeld,
      seq: this.stream.frameSeq,
      panTilt: `${Math.round(head.yaw * 57.3)} / ${Math.round(head.pitch * 57.3)}`,
    });

    this.renderer.render(this.scene, this.camera);
  }
}
