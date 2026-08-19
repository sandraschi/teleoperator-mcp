export function HelpPage() {
  return (
    <section className="page-card help-prose" data-testid="help-page">
      <h2>Teleoperator quick start</h2>
      <p data-testid="help-intro">
        WebXR headset (Pico 4, Quest) streams 30 Hz pose frames over WebSocket to this gateway,
        which maps them to Yahboom Boomy drive commands via the ProducerCommand adapter layer.
      </p>

      <h3>Pico 4 path</h3>
      <ul>
        <li>
          Sideload Tailscale from the revive pack (<code>pico-tailscale-setup</code>).
        </li>
        <li>
          Open Pico Browser (not Wolvic) to your Tailscale Serve URL, e.g.{" "}
          <code>https://goliath.*.ts.net/</code>.
        </li>
        <li>Home → Enter VR → squeeze either grip for takeover, trigger for deadman drive.</li>
      </ul>

      <h3>Controls (WebXR)</h3>
      <ul>
        <li>Right stick: base translation / rotation</li>
        <li>Head pose: camera pan/tilt when gaze group is in DIRECT mode</li>
        <li>Squeeze (either hand): human takeover</li>
        <li>Watchdog: no frames → automatic e-stop</li>
      </ul>

      <h3>Startup</h3>
      <ul>
        <li>
          <code>webapp\start.bat</code> — clears ports, starts backend :10901 + Vite :10900
        </li>
        <li>
          <code>-WithTailscaleServe</code> — exposes HTTPS for headset access
        </li>
      </ul>

      <h3>Standards</h3>
      <p>
        This dashboard follows fleet SOTA webapp standards: Iron Shell layout,{" "}
        <code>/api/capabilities</code>,<code>/api/logs</code>, and standard routes (Tools, Logs,
        Apps, Settings, Help).
      </p>
    </section>
  );
}
