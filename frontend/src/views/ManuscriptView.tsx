import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";
import { api } from "@/api/client";
import { SeverityBadge } from "@/components/SeverityBadge";
import type { Manuscript, RiskIndices } from "@/types";
import { fmtTs } from "@/lib/format";

export function ManuscriptView() {
  const [params, setParams] = useSearchParams();
  const [manuscripts, setManuscripts] = useState<Manuscript[]>([]);
  const [m, setM] = useState<Manuscript | null>(null);
  const [idx, setIdx] = useState<RiskIndices | null>(null);
  const [history, setHistory] = useState<RiskIndices[]>([]);

  const id = params.get("id") ?? "";

  useEffect(() => {
    api.manuscripts().then((all) => {
      setManuscripts(all);
      if (!id && all.length) setParams({ id: all[0].id });
    });
  }, []);

  useEffect(() => {
    if (!id) return;
    api.manuscript(id).then(setM);
    api.indices(id).then(setIdx);
    api.indicesHistory(id, 20).then(setHistory);
    const tick = setInterval(() => {
      api.indices(id).then(setIdx);
    }, 5000);
    return () => clearInterval(tick);
  }, [id]);

  const radarData = useMemo(() => {
    if (!idx) return [];
    return [
      { metric: "Chimico", value: idx.RI_Chimico },
      { metric: "Meccanico", value: idx.RI_Meccanico * 10 }, // rescale 0-100 view
      { metric: "Insetti", value: idx.RI_Insetti },
      { metric: "Muffa", value: idx.RI_Muffa * 10 },
      { metric: "Fotodet.", value: Math.min(100, (idx.RI_Fotodeterioramento / 130) * 100) },
    ];
  }, [idx]);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end gap-4 justify-between">
        <div>
          <h1 className="text-2xl font-bold">Vista Manufatto</h1>
          <p className="text-sm text-slate-500">Scheda codicologica e indici di rischio.</p>
        </div>
        <select
          className="border border-slate-300 rounded-md px-3 py-1.5 text-sm bg-white"
          value={id}
          onChange={(e) => setParams({ id: e.target.value })}
        >
          {manuscripts.map((mm) => (
            <option key={mm.id} value={mm.id}>
              {mm.id} — {mm.nome}
            </option>
          ))}
        </select>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <div className="card-title">Scheda codicologica</div>
          {m && (
            <dl className="grid grid-cols-2 gap-y-2 text-sm">
              <dt className="text-slate-500">ID</dt>
              <dd className="font-mono">{m.id}</dd>
              <dt className="text-slate-500">Nome</dt>
              <dd>{m.nome}</dd>
              <dt className="text-slate-500">Supporto</dt>
              <dd>{m.tipologia_supporto}</dd>
              <dt className="text-slate-500">pH stimato</dt>
              <dd>{m.pH_stimato}</dd>
              <dt className="text-slate-500">DP₀</dt>
              <dd>{m.DP0_stimato}</dd>
              <dt className="text-slate-500">Inchiostro ferro-gallico</dt>
              <dd>{m.inchiostro_ferro_gallico ? "sì" : "no"}</dd>
              <dt className="text-slate-500">Pigmenti fotosensibili</dt>
              <dd>{m.pigmenti_fotosensibili ? "sì" : "no"}</dd>
              <dt className="text-slate-500">Stato legatura</dt>
              <dd>{m.stato_legatura}</dd>
              <dt className="text-slate-500">Deformazioni</dt>
              <dd>{m.deformazioni_osservate}/3</dd>
              <dt className="text-slate-500">Fragilità</dt>
              <dd>{m.fragilita_osservata}/3</dd>
              <dt className="text-slate-500">Alterazioni cromatiche</dt>
              <dd>{m.alterazioni_cromatiche}/3</dd>
              <dt className="text-slate-500">Frequenza consultazione</dt>
              <dd>{m.frequenza_consultazione}</dd>
              <dt className="text-slate-500">Posizione</dt>
              <dd>
                {m.posizione.altezza_dal_pavimento}, {m.posizione.quota}
                {m.posizione.parete_esterna ? ", parete est." : ""}
                {m.posizione.esposizione_solare ? ", sole" : ""}
              </dd>
              <dt className="text-slate-500">Ambiente</dt>
              <dd className="font-mono">{m.ambiente_id}</dd>
            </dl>
          )}
        </div>

        <div className="card">
          <div className="flex justify-between items-baseline">
            <div className="card-title m-0">Indici di rischio</div>
            {idx && <SeverityBadge severity={idx.severity} />}
          </div>
          {idx && (
            <>
              <div className="text-center my-3">
                <div className="text-xs uppercase tracking-wide text-slate-500">
                  RI<sub>Totale</sub>
                </div>
                <div className="text-5xl font-bold">{idx.RI_Totale.toFixed(1)}%</div>
              </div>
              <ResponsiveContainer width="100%" height={250}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#cbd5e1" />
                  <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11 }} />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 9 }} />
                  <Radar
                    dataKey="value"
                    stroke="#0f172a"
                    fill="#0f172a"
                    fillOpacity={0.3}
                  />
                </RadarChart>
              </ResponsiveContainer>
              <div className="grid grid-cols-2 gap-y-1 text-xs mt-2">
                <div>RI Chimico: <strong>{idx.RI_Chimico.toFixed(1)}%</strong></div>
                <div>RI Meccanico: <strong>{idx.RI_Meccanico.toFixed(2)}%</strong></div>
                <div>RI Insetti: <strong>{idx.RI_Insetti.toFixed(1)}%</strong></div>
                <div>RI Muffa: <strong>{idx.RI_Muffa.toFixed(2)}%</strong></div>
                <div className="col-span-2">
                  RI Fotodet.: <strong>ΔE* {idx.RI_Fotodeterioramento.toFixed(1)}</strong>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-title">Cronologia ultime misurazioni</div>
        {history.length === 0 ? (
          <p className="text-sm text-slate-500">
            Nessuna misurazione storicizzata. Verrà popolata dal motore live.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase text-slate-500 border-b">
              <tr>
                <th className="py-1">Timestamp</th>
                <th>Chimico</th>
                <th>Meccanico</th>
                <th>Insetti</th>
                <th>Muffa</th>
                <th>RI Tot</th>
                <th>Severità</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h, i) => (
                <tr key={i} className="border-b border-slate-100">
                  <td className="py-1">{fmtTs(h.timestamp)}</td>
                  <td>{h.RI_Chimico.toFixed(1)}</td>
                  <td>{h.RI_Meccanico.toFixed(2)}</td>
                  <td>{h.RI_Insetti.toFixed(1)}</td>
                  <td>{h.RI_Muffa.toFixed(2)}</td>
                  <td>
                    <strong>{h.RI_Totale.toFixed(1)}</strong>
                  </td>
                  <td><SeverityBadge severity={h.severity} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
