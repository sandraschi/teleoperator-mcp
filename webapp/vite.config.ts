import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 10900,
    strictPort: true,
    host: true,
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
