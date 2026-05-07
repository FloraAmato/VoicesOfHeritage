import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { Alert } from "@/types";
import { fmtTs } from "@/lib/format";

const SEV_COLOR: Record<Alert["severity"], string> = {
  INFO: "bg-slate-100 text-slate-800 ring-slate-300",
  MEDIA: "bg-amber-100 text-amber-800 ring-amber-300",
  ALTA: "bg-orange-100 text-orange-800 ring-orange-300",
  CRITICA: "bg-red-100 text-red-800 ring-red-300",
};

export function AlertsView() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [filter, setFilter] = useState<string>("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [recos, setRecos] = useState<Record<string, any>>({});

  const refresh = () => api.alerts(filter || undefined).then(setAlerts);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, [filter]);

  const toggle = async (id: string) => {
    if (expanded === id) {
      setExpanded(null);
      return;
    }
    setExpanded(id);
    if (!recos[id]) {
      try {
        const r = await api.recommendations(id);
        setRecos((prev) => ({ ...prev, [id]: r }));
      } catch { /* ignore */ }
    }
  };

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end gap-4 justify-between">
        <div>
          <h1 className="text-2xl font-bold">Vista Alert</h1>
          <p className="text-sm text-slate-500">Cronologia e gestione degli alert.</p>
        </div>
        <select
          className="border border-slate-300 rounded-md px-3 py-1.5 text-sm bg-white"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="">Tutti</option>
          <option value="aperto">Aperti</option>
          <option value="preso_in_carico">In carico</option>
          <option value="risolto">Risolti</option>
        </select>
      </header>

      {alerts.length === 0 ? (
        <div className="card text-sm text-slate-500">
          Nessun alert {filter ? `con stato "${filter}"` : ""}. Lancia uno scenario demo per generarne.
        </div>
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase text-slate-500 bg-slate-50">
              <tr>
                <th className="px-4 py-2">Timestamp</th>
                <th>Severità</th>
                <th>Manoscritto</th>
                <th>Ambiente</th>
                <th>Trigger</th>
                <th>RI Tot</th>
                <th>Stato</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a) => (
                <>
                  <tr key={a.id} className="border-b border-slate-100">
                    <td className="px-4 py-2">{fmtTs(a.timestamp)}</td>
                    <td>
                      <span className={`px-2 py-0.5 rounded ring-1 text-xs font-semibold ${SEV_COLOR[a.severity]}`}>
                        {a.severity}
                      </span>
                    </td>
                    <td className="font-mono text-xs">{a.manuscript_id}</td>
                    <td className="font-mono text-xs">{a.environment_id}</td>
                    <td>
                      {a.trigger_variable} = <strong>{a.trigger_value.toFixed(1)}</strong>
                    </td>
                    <td>{a.RI_Totale.toFixed(1)}%</td>
                    <td className="text-xs">{a.status}</td>
                    <td className="px-4 py-2 text-right space-x-2">
                      <button className="btn-ghost text-xs" onClick={() => toggle(a.id)}>
                        {expanded === a.id ? "chiudi" : "dettagli"}
                      </button>
                      {a.status === "aperto" && (
                        <button
                          className="btn-primary text-xs"
                          onClick={async () => {
                            await api.ackAlert(a.id, "preso_in_carico");
                            refresh();
                          }}
                        >
                          ack
                        </button>
                      )}
                      {a.status === "preso_in_carico" && (
                        <button
                          className="btn-primary text-xs"
                          onClick={async () => {
                            await api.ackAlert(a.id, "risolto");
                            refresh();
                          }}
                        >
                          risolvi
                        </button>
                      )}
                    </td>
                  </tr>
                  {expanded === a.id && (
                    <tr className="border-b border-slate-100 bg-slate-50">
                      <td colSpan={8} className="px-6 py-3 text-sm">
                        <div className="font-semibold mb-1">{a.message}</div>
                        {recos[a.id] ? (
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-2">
                            <RecoBlock title="Azioni immediate (24h)" items={recos[a.id].azioni_immediate} />
                            <RecoBlock title="Verifiche tecniche (settimana)" items={recos[a.id].verifiche_tecniche} />
                            <RecoBlock title="Piano medio termine (mese)" items={recos[a.id].piano_medio_termine} />
                          </div>
                        ) : (
                          <div className="text-xs text-slate-500">Caricamento raccomandazioni…</div>
                        )}
                        {a.note && (
                          <div className="mt-2 text-xs text-slate-600">Nota: {a.note}</div>
                        )}
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function RecoBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="bg-white rounded-md p-3 border border-slate-200">
      <div className="text-xs font-semibold uppercase text-slate-500 mb-2">{title}</div>
      <ul className="text-xs space-y-1 list-disc list-inside">
        {items.map((it, i) => (
          <li key={i}>{it}</li>
        ))}
      </ul>
    </div>
  );
}
