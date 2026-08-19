import { useEffect } from "react";

interface BackendStatusHook {
  onReady: () => void;
  onError: (message: string) => void;
}

/**
 * Listen for the Tauri `backend-status` event emitted by native/src/backend.rs
 * (stdout watch -> "ready", connection failure -> "error: ..."). Falls back to
 * HTTP polling in the Shell when not running inside Tauri.
 */
export function useTauriBackendListener({ onReady, onError }: BackendStatusHook) {
  useEffect(() => {
    let disposed = false;
    let unlisten: (() => void) | null = null;

    void (async () => {
      try {
        const { listen } = await import("@tauri-apps/api/event");
        unlisten = await listen<string>("backend-status", (event) => {
          if (disposed) return;
          if (event.payload === "ready") {
            onReady();
          } else if (typeof event.payload === "string" && event.payload.startsWith("error:")) {
            onError(event.payload);
          }
        });
      } catch {
        // Not running inside Tauri - HTTP polling in the Shell covers this.
      }
    })();

    return () => {
      disposed = true;
      if (unlisten) unlisten();
    };
  }, [onReady, onError]);
}
