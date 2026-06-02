import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 10900,
    strictPort: true,
    host: true,
    // Tailscale Serve forwards Host: goliath.*.ts.net — Vite 6 blocks unknown hosts by default
    allowedHosts: ["localhost", "127.0.0.1", "goliath", ".ts.net"],
    proxy: {
      "/api": { target: "http://127.0.0.1:10901", changeOrigin: true },
      "/ws": { target: "ws://127.0.0.1:10901", ws: true },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
