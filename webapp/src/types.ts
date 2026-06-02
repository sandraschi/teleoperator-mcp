/** WebXR pose frame v1 - see docs/PRD.md */

export interface PoseButtons {
  trigger?: number;
  squeeze?: number;
  a?: boolean;
  b?: boolean;
}

export interface ControllerPose {
  connected: boolean;
  axes: number[];
  buttons: PoseButtons;
}

export interface HeadPose {
  yaw: number;
  pitch: number;
  roll: number;
}

export interface PoseFrame {
  v: 1;
  t: number;
  seq: number;
  type?: "heartbeat" | "estop";
  head: HeadPose;
  right: ControllerPose;
  left: ControllerPose;
}

export interface HudState {
  wsConnected: boolean;
  rttMs: number | null;
  deadman: boolean;
  estop: boolean;
  seq: number;
  panTilt: string;
}

export const initialHudState = (): HudState => ({
  wsConnected: false,
  rttMs: null,
  deadman: false,
  estop: false,
  seq: 0,
  panTilt: "--",
});
