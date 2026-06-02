# Concepts and glossary

Plain-language definitions for terms used across teleoperator-mcp docs. Not a tutorial — just enough to read the architecture without prior robotics/ML context.

---

## Teleoperation and VR

| Term | Meaning |
|------|---------|
| **Teleoperation (teleop)** | A human controls a remote robot in real time — here via a VR headset. |
| **Telesupervision** | The human watches an autonomous policy run and can veto, retask, or take over. Mode B in [DUAL_MODE_ARCHITECTURE.md](DUAL_MODE_ARCHITECTURE.md). |
| **WebXR** | Browser API for immersive VR. Our client uses it instead of a native Pico/Meta app. See [WEBXR.md](WEBXR.md). |
| **Pose stream** | Head orientation + controller stick/buttons sent ~30 times per second over WebSocket. |
| **Deadman** | Drive only while the trigger is held — release trigger and the robot stops. |
| **Chin HUD** | Small status strip rendered below your gaze in VR (connection, RTT, drive state). |

---

## This repo's architecture

| Term | Meaning |
|------|---------|
| **Hot path** | WebSocket pose ingress (~30 Hz). Must stay low-latency; never goes through MCP. |
| **Cold path** | MCP tools (status, configure, estop, future mode switching). Seconds-scale is fine. |
| **Producer** | Anything that emits robot commands: human pose-mapper, nav controller, VLA policy. |
| **Adapter (robot adapter)** | Platform-specific sink: turns `ProducerCommand` into REST/ROS calls for one robot (Boomy today). Code: `src/teleoperator_mcp/adapters/`. |
| **Arbiter** | Future module that decides which producer owns each actuator group per tick. Milestone 3. |
| **Actuator groups** | `base` (drive), `gaze` (head/PTZ), `manip` (arms/hands). Not every robot has every group. |
| **ProducerCommand** | Standard packet: `{ producer_id, base?, gaze?, manip? }` between producers and adapter. |
| **RobotCapabilities** | Descriptor (`has_base`, `has_arms`, `hand_type`, `balance_risk`, …) so the arbiter knows what is safe on each platform. |

---

## Fleet and robots

| Term | Meaning |
|------|---------|
| **Boomy** | Yahboom Raspbot v2 wheeled robot. Rung 0 — validates software with no manipulation arms. Driven via [yahboom-mcp](https://github.com/sandraschi/yahboom-mcp). |
| **Goliath** | Your Windows PC running teleoperator-mcp, yahboom-mcp, and Tailscale Serve. |
| **MCP (Model Context Protocol)** | Standard way Cursor/agents call tools on fleet servers. Our supervisor interface. |
| **FastMCP** | Python MCP framework (v3.2+) used for `teleop_status`, `teleop_configure`, `teleop_estop`. |
| **yahboom-mcp** | Separate repo: ROS 2 bridge, REST API, camera, MCP tools for Boomy hardware. |
| **LiveKit / myconf** | WebRTC stack for video return (v1.5). Robot camera -> Goliath -> headset browser. |

---

## Autonomy and learning (future phases)

| Term | Meaning |
|------|---------|
| **LeRobot** | Open-source **robotics dataset and training stack** from Hugging Face ([huggingface.co/lerobot](https://huggingface.co/lerobot)). Defines a standard **episode format** (observations, actions, timestamps, optional video) so teleop demos can train imitation-learning policies. We plan to log Mode A sessions in this format (Milestone 4) — even Boomy base-motion demos — as fine-tuning data for later VLA work. |
| **VLA (vision-language-action)** | Model that takes camera + language goal and outputs robot actions. Examples: **WALL-OSS-0.5**, **UnifoLM-VLA-0**. Manipulation-only in our architecture — not locomotion. |
| **WALL-OSS / WALL-OSS-0.5** | Open manipulation foundation model (X Square Robot, ~4B params). Strong prior for hand-centric tasks; fine-tuned on your LeRobot episodes. |
| **UnifoLM-VLA-0** | Unitree's open VLA (Qwen2.5-VL base). Alternative producer if you stay in Unitree ecosystem. |
| **Data flywheel** | Loop: teleop demos -> LeRobot dataset -> fine-tune policy -> autonomy -> human corrects -> more demos. |
| **Imitation learning** | Train a policy to mimic recorded human demonstrations (as opposed to RL from scratch). |

---

## Networking

| Term | Meaning |
|------|---------|
| **Tailscale** | Mesh VPN: Pico, Meta Quest, and Goliath share a private tailnet with stable hostnames. |
| **Tailscale Serve** | HTTPS reverse proxy on Goliath exposing local `:10900` as `https://goliath.*.ts.net`. Required for WebXR without manual certs. See [HTTPS.md](HTTPS.md) and [TAILSCALE_VIEWERS.md](TAILSCALE_VIEWERS.md). |
| **CORS** | Browser security rule. Backend allowlists the headset origin via `TELEOP_CORS_ORIGINS`. |

---

## Abbreviations

| Abbr | Expansion |
|------|-----------|
| PTZ | Pan-tilt-zoom (camera servos on Boomy) |
| SFU | Selective Forwarding Unit (LiveKit video routing) |
| VLA | Vision-language-action model |
| DOF | Degrees of freedom (joint axes) |
| E-stop | Emergency stop (zero velocity / halt) |
