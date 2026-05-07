import type {
  Alert,
  DashboardSummary,
  Environment,
  Manuscript,
  PredictionResponse,
  RiskIndices,
  Scenario,
  TelemetrySample,
} from "@/types";

const BASE = "/api";

async function jget<T>(url: string): Promise<T> {
  const r = await fetch(BASE + url);
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}

async function jpost<T>(url: string, body?: unknown): Promise<T> {
  const r = await fetch(BASE + url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}

async function jput<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(BASE + url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}

export const api = {
  manuscripts: () => jget<Manuscript[]>("/manuscripts"),
  manuscript: (id: string) => jget<Manuscript>(`/manuscripts/${id}`),
  indices: (id: string) => jget<RiskIndices>(`/manuscripts/${id}/indices`),
  indicesHistory: (id: string, limit = 200) =>
    jget<RiskIndices[]>(`/manuscripts/${id}/indices/history?limit=${limit}`),
  whatif: (id: string, body: Record<string, unknown>) =>
    jpost<RiskIndices>(`/manuscripts/${id}/whatif`, body),
  predict: (id: string) => jget<PredictionResponse>(`/manuscripts/${id}/predict`),

  environments: () => jget<Environment[]>("/environments"),
  environment: (id: string) => jget<Environment>(`/environments/${id}`),
  telemetry: (id: string, limit = 1000, quota?: string) => {
    const q = new URLSearchParams({ limit: String(limit) });
    if (quota) q.append("quota", quota);
    return jget<TelemetrySample[]>(`/environments/${id}/telemetry?${q}`);
  },

  weights: (envType: string) =>
    jget<{ environment_type: string; weights: Record<string, number>; variables: string[] }>(
      `/weights/${envType}`,
    ),
  weightsAll: () => jget<Record<string, Record<string, number>>>("/weights"),
  setWeights: (envType: string, w: Record<string, number>) =>
    jput<Record<string, number>>(`/weights/${envType}`, w),
  resetWeights: (envType: string) => jpost<Record<string, number>>(`/weights/${envType}/reset`),

  thresholds: () =>
    jget<{ environmental: Record<string, Record<string, [number, number]>>; risk_indices: Record<string, Record<string, number>> }>(
      "/thresholds",
    ),

  alerts: (status?: string) =>
    jget<Alert[]>(`/alerts${status ? `?status=${status}` : ""}`),
  ackAlert: (id: string, status?: string, note?: string) =>
    jpost<Alert>(`/alerts/${id}/ack`, { status, note }),

  triggerScenario: (envId: string, scenario: Scenario, durationHours = 72) =>
    jpost<{ status: string }>("/demo/scenario", {
      environment_id: envId,
      scenario,
      duration_hours: durationHours,
    }),
  resetScenarios: () => jpost<{ status: string }>("/demo/reset"),

  summary: () => jget<DashboardSummary>("/dashboard/summary"),

  tsne: (envId: string) =>
    jget<{ points: Array<{ x: number; y: number; z: number; cluster: number; ts: string }>; current?: { x: number; y: number; z: number; cluster: number } }>(
      `/environments/${envId}/tsne`,
    ),

  recommendations: (alertId: string) =>
    jget<{
      azioni_immediate: string[];
      verifiche_tecniche: string[];
      piano_medio_termine: string[];
    }>(`/alerts/${alertId}/recommendations`),
};

export type { TelemetrySample };
