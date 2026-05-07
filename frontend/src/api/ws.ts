import type { TelemetrySample } from "@/types";

export type WSMessage =
  | { type: "telemetry_batch"; samples: TelemetrySample[] }
  | { type: "error"; message: string };

export function connectTelemetry(onMessage: (m: WSMessage) => void): () => void {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${proto}//${window.location.host}/ws/telemetry`;
  const ws = new WebSocket(url);
  ws.onmessage = (ev) => {
    try {
      const m = JSON.parse(ev.data) as WSMessage;
      onMessage(m);
    } catch {
      /* ignore */
    }
  };
  ws.onerror = () => onMessage({ type: "error", message: "WebSocket error" });
  return () => ws.close();
}
