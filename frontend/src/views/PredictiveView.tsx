import { useEffect, useMemo, useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Scatter,
  ScatterChart,
  ZAxis,
} from "recharts";
import { api } from "@/api/client";
import { SeverityBadge } from "@/components/SeverityBadge";
import type { Environment, Manuscript, PredictionResponse, RiskIndices } from "@/types";

const CLUSTER_COLORS = ["#16a34a", "#84cc16", "#f59e0b", "#dc2626", "#94a3b8"];

export function PredictiveView() {
  const [manuscripts, setManuscripts] = useState<Manuscript[]>([]);
  const [envs, setEnvs] = useState<Environment[]>([]);
  const [id, setId] = useState<string>("");
  const [history, setHistory] = useState<RiskIndices[]>([]);
  const [pred, setPred] = useState<PredictionResponse | null>(null);
  const [whatIfResult, setWhatIfResult] = useState<RiskIndices | null>(null);
  const [tsne, setTsne] = useState<{ points: any[]; current?: any } | null>(null);

  // What-if state
  const [tSet, setTSet] = useState<string>("");
  const [rhSet, setRhSet] = useState<string>("");
  const [luxSet, setLuxSet] = useState<string>("");
  const [vocSet, setVocSet] = useState<string>("");
  const [targetEnv, setTargetEnv] = useState<string>("");

  useEffect(() => {
    api.manuscripts().then((all) => {
      setManuscripts(all);
      if (all.length) setId(all[0].id);
    });
    api.environments().then(setEnvs);
  }, []);

  useEffect(() => {
    if (!id) return;
    api.indicesHistory(id, 200).then(setHistory);
    api.predict(id).then(setPred).catch(() => setPred(null));
    const m = manuscripts.find((x) => x.id === id);
    if (m) api.tsne(m.ambiente_id).then(setTsne).catch(() => setTsne(null));
  }, [id, manuscripts]);

  const trajectory = useMemo(() => {
    if (!pred) return [];
    // Past + future
    const past = history.slice(-30).map((h, i) => ({
      t: i - history.slice(-30).length,
      RI: h.RI_Totale,
    }));
    const future = pred.trajectory.map((p) => ({
      t: p.t_days,
      RI_pred: p.RI_pred,
      lower: p.lower,
      upper: p.upper,
    }));
    return [...past, ...future];
  }, [pred, history]);

  const runWhatIf = async () => {
    if (!id) return;
    const body: Record<string, unknown> = {};
    if (tSet) body.T_set = parseFloat(tSet);
    if (rhSet) body.RH_set = parseFloat(rhSet);
    if (luxSet) body.lux_set = parseFloat(luxSet);
    if (vocSet) body.VOC_set = parseFloat(vocSet);
    if (targetEnv) body.target_environment_id = targetEnv;
    const out = await api.whatif(id, body);
    setWhatIfResult(out);
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end gap-4 justify-between">
        <div>
          <h1 className="text-2xl font-bold">Vista Predittiva</h1>
          <p className="text-sm text-slate-500">
            Traiettoria RI<sub>Totale</sub>, RUT-A e simulatore what-if.
          </p>
        </div>
        <select
          className="border border-slate-300 rounded-md px-3 py-1.5 text-sm bg-white"
          value={id}
          onChange={(e) => setId(e.target.value)}
        >
          {manuscripts.map((mm) => (
            <option key={mm.id} value={mm.id}>
              {mm.id} — {mm.nome}
            </option>
          ))}
        </select>
      </header>

      <div className="card">
        <div className="card-title">Traiettoria RI<sub>Totale</sub> — passato + 30 gg di proiezione</div>
        <ResponsiveContainer width="100%" height={280}>
          <ComposedChart data={trajectory}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="t" tick={{ fontSize: 11 }} label={{ value: "giorni", position: "insideBottom", fontSize: 10 }} />
            <YAxis tick={{ fontSize: 11 }} domain={[0, 100]} />
            <Tooltip />
            <Legend />
            <Area
              type="monotone"
              dataKey="upper"
              stroke="none"
              fill="#0ea5e9"
              fillOpacity={0.15}
              name="banda 90%"
            />
            <Area
              type="monotone"
              dataKey="lower"
              stroke="none"
              fill="#fff"
              fillOpacity={1}
            />
            <Line type="monotone" dataKey="RI" stroke="#0f172a" strokeWidth={2} dot={false} name="osservato" />
            <Line
              type="monotone"
              dataKey="RI_pred"
              stroke="#0ea5e9"
              strokeWidth={2}
              strokeDasharray="4 2"
              dot={false}
              name="predetto"
            />
          </ComposedChart>
        </ResponsiveContainer>
        {pred && (
          <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
            <div className="bg-slate-50 rounded-md p-3">
              <div className="text-xs uppercase text-slate-500">RI corrente</div>
              <div className="text-2xl font-bold">{pred.current_RI.toFixed(1)}%</div>
            </div>
            <div className="bg-slate-50 rounded-md p-3">
              <div className="text-xs uppercase text-slate-500">RI predetto a 30 gg</div>
              <div className="text-2xl font-bold">{pred.predicted_RI_30d.toFixed(1)}%</div>
            </div>
            <div className="bg-amber-50 rounded-md p-3 border border-amber-200">
              <div className="text-xs uppercase text-amber-700">RUT-A (giorni residui)</div>
              <div className="text-2xl font-bold text-amber-900">
                {pred.RUT_A_days >= 9999 ? "—" : pred.RUT_A_days.toFixed(0)}
              </div>
              {pred.RUT_A_days < 9999 && (
                <div className="text-xs text-amber-700">
                  IC 90%: [{pred.RUT_A_lower.toFixed(0)}, {pred.RUT_A_upper.toFixed(0)}] gg
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-title">Simulatore what-if</div>
        <p className="text-sm text-slate-500 mb-3">
          Imposta valori ipotetici per ricalcolare RI<sub>Totale</sub> senza salvare. Cambiare
          ambiente target applica la matrice pesi del nuovo contesto.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <Field label="T set (°C)" value={tSet} onChange={setTSet} ph="es. 18" />
          <Field label="RH set (%)" value={rhSet} onChange={setRhSet} ph="es. 50" />
          <Field label="lux set" value={luxSet} onChange={setLuxSet} ph="es. 50" />
          <Field label="VOC set (ppb)" value={vocSet} onChange={setVocSet} ph="es. 200" />
          <div>
            <label className="block text-xs font-semibold uppercase text-slate-500 mb-1">
              Sposta in ambiente
            </label>
            <select
              className="border border-slate-300 rounded-md px-2 py-1.5 text-sm w-full"
              value={targetEnv}
              onChange={(e) => setTargetEnv(e.target.value)}
            >
              <option value="">—</option>
              {envs.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.nome}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="mt-3 flex gap-2">
          <button className="btn-primary" onClick={runWhatIf}>
            Calcola
          </button>
          <button
            className="btn-ghost"
            onClick={() => {
              setTSet(""); setRhSet(""); setLuxSet(""); setVocSet(""); setTargetEnv("");
              setWhatIfResult(null);
            }}
          >
            Reset
          </button>
        </div>
        {whatIfResult && (
          <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
            <div className="bg-slate-50 rounded-md p-3">
              <div className="text-xs uppercase text-slate-500">RI Totale (what-if)</div>
              <div className="text-2xl font-bold">{whatIfResult.RI_Totale.toFixed(1)}%</div>
              <SeverityBadge severity={whatIfResult.severity} />
            </div>
            <div className="bg-slate-50 rounded-md p-3 col-span-2 text-xs grid grid-cols-2 gap-y-1">
              <div>Chimico: <strong>{whatIfResult.RI_Chimico.toFixed(1)}%</strong></div>
              <div>Meccanico: <strong>{whatIfResult.RI_Meccanico.toFixed(2)}%</strong></div>
              <div>Insetti: <strong>{whatIfResult.RI_Insetti.toFixed(1)}%</strong></div>
              <div>Muffa: <strong>{whatIfResult.RI_Muffa.toFixed(2)}%</strong></div>
              <div className="col-span-2">Foto.: <strong>ΔE* {whatIfResult.RI_Fotodeterioramento.toFixed(1)}</strong></div>
            </div>
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-title">Proiezione t-SNE — cluster diagnostici</div>
        {tsne ? (
          <ResponsiveContainer width="100%" height={320}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" dataKey="x" tick={{ fontSize: 10 }} />
              <YAxis type="number" dataKey="y" tick={{ fontSize: 10 }} />
              <ZAxis type="number" dataKey="z" range={[40, 80]} />
              <Tooltip />
              {[0, 1, 2, 3, -1].map((c) => {
                const pts = tsne.points.filter((p: any) => p.cluster === c);
                if (!pts.length) return null;
                return (
                  <Scatter
                    key={c}
                    data={pts}
                    fill={CLUSTER_COLORS[c === -1 ? 4 : c]}
                    name={c === -1 ? "noise" : `Cluster ${c}`}
                  />
                );
              })}
              {tsne.current && (
                <Scatter
                  data={[tsne.current]}
                  fill="#000"
                  shape="star"
                  name="manufatto corrente"
                />
              )}
            </ScatterChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-slate-500">
            t-SNE non ancora disponibile per questo ambiente.
          </p>
        )}
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  ph,
}: {
  label: string;
  value: string;
  onChange: (s: string) => void;
  ph?: string;
}) {
  return (
    <div>
      <label className="block text-xs font-semibold uppercase text-slate-500 mb-1">{label}</label>
      <input
        type="number"
        className="border border-slate-300 rounded-md px-2 py-1.5 text-sm w-full"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={ph}
      />
    </div>
  );
}
