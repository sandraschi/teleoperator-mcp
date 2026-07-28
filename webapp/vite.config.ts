import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 10900,
    strictPort: true,
    host: true,
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
