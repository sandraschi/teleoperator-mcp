import { XrSession } from "./xr-session";

const enterBtn = document.getElementById("enter-vr") as HTMLButtonElement;
const supportEl = document.getElementById("xr-support") as HTMLParagraphElement;
const robotSelect = document.getElementById("robot-select") as HTMLSelectElement;
const debugStats = document.getElementById("debug-stats") as HTMLDListElement;
const canvas = document.getElementById("xr-canvas") as HTMLCanvasElement;

let xr: XrSession | null = null;

async function probeXr(): Promise<void> {
  if (!navigator.xr) {
    supportEl.textContent = "WebXR not available in this browser.";
    return;
  }
  const supported = await navigator.xr.isSessionSupported("immersive-vr");
  supportEl.textContent = supported
    ? "WebXR immersive-vr supported. HTTPS required on headset."
    : "immersive-vr not supported on this device.";
  enterBtn.disabled = !supported;
}

enterBtn.addEventListener("click", async () => {
  enterBtn.disabled = true;
  try {
    xr = new XrSession(canvas, robotSelect.value);
    await xr.start();
  } catch (err) {
    supportEl.textContent = err instanceof Error ? err.message : String(err);
    enterBtn.disabled = false;
  }
});

async function pollHealth(): Promise<void> {
  try {
    const res = await fetch("/api/v1/health");
    const data = (await res.json()) as {
      teleop?: { active?: boolean; frames_in?: number };
    };
    debugStats.innerHTML = `
      <dt>Backend</dt><dd>ok</dd>
      <dt>Teleop active</dt><dd>${data.teleop?.active ? "yes" : "no"}</dd>
      <dt>Frames</dt><dd>${data.teleop?.frames_in ?? 0}</dd>
    `;
  } catch {
    debugStats.innerHTML = "<dt>Backend</dt><dd>offline</dd>";
  }
}

probeXr();
pollHealth();
setInterval(pollHealth, 3000);
