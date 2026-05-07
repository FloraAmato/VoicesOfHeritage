import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ComposedChart,
  Scatter,
} from "recharts";
import { api } from "@/api/client";
import { connectTelemetry } from "@/api/ws";
import type { Environment, TelemetrySample } from "@/types";
import { fmtTime } from "@/lib/format";

const CHANNELS = [
  { key: "T", label: "T (°C)", color: "#dc2626" },
  { key: "RH", label: "RH (%)", color: "#2563eb" },
  { key: "lux", label: "Lux", color: "#f59e0b" },
  { key: "VOC", label: "VOC (ppb)", color: "#7c3aed" },
  { key: "PM10", label: "PM10 (µg/m³)", color: "#0891b2" },
  { key: "CO2", label: "CO₂ (ppm)", color: "#475569" },
] as const;

export function EnvironmentView() {
  const [envs, setEnvs] = useState<Environment[]>([]);
  const [envId, setEnvId] = useState<string>("");
  const [samples, setSamples] = useState<TelemetrySample[]>([]);
  const [thresholds, setThresholds] = useState<Record<string, Record<string, [number, number]>>>({});
  const [quotaFilter, setQuotaFilter] = useState<string>("");

  useEffect(() => {
    api.environments().then((e) => {
      setEnvs(e);
      if (e.length) setEnvId(e[0].id);
    });
    api.thresholds().then((t) => setThresholds(t.environmental));
  }, []);

  // Load history when env changes
  useEffect(() => {
    if (!envId) return;
    const env = envs.find((e) => e.id === envId);
    const isSala = env?.tipo === "sala_storica_pt_soppalco";
    const q = isSala ? quotaFilter || "piano_terra" : undefined;
    api.telemetry(envId, 600, q).then(setSamples);
  }, [envId, quotaFilter, envs]);

  // Live updates via WS
  useEffect(() => {
    const stop = connectTelemetry((m) => {
      if (m.type === "telemetry_batch") {
        const env = envs.find((e) => e.id === envId);
        const isSala = env?.tipo === "sala_storica_pt_soppalco";
        const q = isSala ? quotaFilter || "piano_terra" : null;
        const filtered = m.samples.filter(
          (s) => s.environment_id === envId && (q === null || s.quota === q),
        );
        if (filtered.length) {
          setSamples((prev) => [...prev, ...filtered].slice(-1000));
        }
      }
    });
    return stop;
  }, [envId, quotaFilter, envs]);

  const data = useMemo(
    () =>
      samples.map((s) => ({
        ts: s.timestamp,
        label: fmtTime(s.timestamp),
        T: s.T,
        RH: s.RH,
        lux: s.lux,
        VOC: s.VOC,
        PM10: s.PM10,
        CO2: s.CO2,
      })),
    [samples],
  );

  const env = envs.find((e) => e.id === envId);
  const isSala = env?.tipo === "sala_storica_pt_soppalco";

  // marcatori superamenti soglia "attenzione"
  const breaches = useMemo(() => {
    const out: Array<{ ts: string; label: string; channel: string; value: number }> = [];
    if (!Object.keys(thresholds).length) return out;
    for (const s of samples) {
      const checkAt = (param: string, val: number, key: string) => {
        const t = thresholds[param];
        if (!t) return;
        const att = t.attenzione;
        if (att && (val < att[0] || val > att[1])) {
          out.push({ ts: s.timestamp, label: fmtTime(s.timestamp), channel: key, value: val });
        }
      };
      checkAt("T", s.T, "T");
      checkAt("RH", s.RH, "RH");
      checkAt("lux", s.lux, "lux");
      checkAt("VOC", s.VOC, "VOC");
    }
    return out;
  }, [samples, thresholds]);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end gap-4 justify-between">
        <div>
          <h1 className="text-2xl font-bold">Vista Ambiente</h1>
          <p className="text-sm text-slate-500">
            Sensore artunified multiparametrico — serie temporali con bande di soglia.
          </p>
        </div>
        <div className="flex gap-2 items-center">
          <select
            className="border border-slate-300 rounded-md px-3 py-1.5 text-sm bg-white"
            value={envId}
            onChange={(e) => setEnvId(e.target.value)}
          >
            {envs.map((e) => (
              <option key={e.id} value={e.id}>
                {e.nome}
              </option>
            ))}
          </select>
          {isSala && (
            <select
              className="border border-slate-300 rounded-md px-3 py-1.5 text-sm bg-white"
              value={quotaFilter || "piano_terra"}
              onChange={(e) => setQuotaFilter(e.target.value)}
            >
              <option value="piano_terra">Piano terra</option>
              <option value="soppalco">Soppalco</option>
            </select>
          )}
        </div>
      </header>

      {CHANNELS.map((c) => {
        const t = thresholds[c.key];
        const breach = breaches.filter((b) => b.channel === c.key);
        return (
          <div key={c.key} className="card">
            <div className="flex justify-between items-baseline mb-2">
              <div className="card-title m-0">{c.label}</div>
              {t && (
                <div className="text-xs text-slate-500">
                  Ottimale {t.ottimale.join("–")} · Attenzione fuori da {t.attenzione.join("–")}
                </div>
              )}
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <ComposedChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={Math.max(0, Math.floor(data.length / 12))} />
                <YAxis tick={{ fontSize: 11 }} />
                {t && (
                  <>
                    <ReferenceArea
                      y1={t.ottimale[0]}
                      y2={t.ottimale[1]}
                      fill="#16a34a"
                      fillOpacity={0.07}
                    />
                    <ReferenceArea
                      y1={t.attenzione[0]}
                      y2={t.attenzione[1]}
                      fill="#f59e0b"
                      fillOpacity={0.06}
                    />
                  </>
                )}
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey={c.key}
                  stroke={c.color}
                  dot={false}
                  strokeWidth={1.5}
                  isAnimationActive={false}
                />
                {breach.length > 0 && (
                  <Scatter
                    data={breach.map((b) => ({ label: b.label, [c.key]: b.value }))}
                    fill="#000"
                    shape="triangle"
                  />
                )}
                <Legend />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        );
      })}

      <div className="card">
        <div className="card-title">Box-plot stratificato per cluster</div>
        <p className="text-sm text-slate-500">
          Distribuzione delle feature ambientali raggruppate per cluster diagnostico (DBSCAN).
          Vedi Vista Predittiva → proiezione t-SNE per la visualizzazione 3D.
        </p>
        <BoxplotMini samples={samples} />
      </div>
    </div>
  );
}

function BoxplotMini({ samples }: { samples: TelemetrySample[] }) {
  // Calcolo q1/q2/q3/min/max per i 4 canali principali
  const stats = ["T", "RH", "VOC", "PM10"].map((k) => {
    const arr = samples.map((s) => (s as any)[k] as number).slice().sort((a, b) => a - b);
    if (!arr.length) return { k, q1: 0, med: 0, q3: 0, min: 0, max: 0 };
    const q = (p: number) => arr[Math.min(arr.length - 1, Math.floor(p * arr.length))];
    return { k, q1: q(0.25), med: q(0.5), q3: q(0.75), min: arr[0], max: arr[arr.length - 1] };
  });
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
      {stats.map((s) => (
        <div key={s.k} className="bg-slate-50 rounded-md p-3">
          <div className="font-semibold text-slate-700 mb-1">{s.k}</div>
          <div className="text-slate-500">min {s.min.toFixed(1)} · max {s.max.toFixed(1)}</div>
          <div className="mt-2 h-3 bg-slate-200 rounded-sm relative overflow-hidden">
            <div
              className="absolute inset-y-0 bg-slate-400"
              style={{
                left: `${((s.q1 - s.min) / Math.max(0.01, s.max - s.min)) * 100}%`,
                right: `${(1 - (s.q3 - s.min) / Math.max(0.01, s.max - s.min)) * 100}%`,
              }}
            />
            <div
              className="absolute inset-y-0 w-px bg-black"
              style={{ left: `${((s.med - s.min) / Math.max(0.01, s.max - s.min)) * 100}%` }}
            />
          </div>
          <div className="mt-1 text-slate-600">μ̃ {s.med.toFixed(1)}</div>
        </div>
      ))}
    </div>
  );
}
