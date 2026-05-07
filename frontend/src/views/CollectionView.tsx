import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import { KPI } from "@/components/KPI";
import { SeverityBadge } from "@/components/SeverityBadge";
import type { DashboardSummary, Environment } from "@/types";

export function CollectionView() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [envs, setEnvs] = useState<Environment[]>([]);

  useEffect(() => {
    const tick = async () => {
      const [s, e] = await Promise.all([api.summary(), api.environments()]);
      setSummary(s);
      setEnvs(e);
    };
    tick();
    const id = setInterval(tick, 5000);
    return () => clearInterval(id);
  }, []);

  if (!summary) return <div className="text-slate-500">Caricamento…</div>;
  const envName = (id: string) => envs.find((e) => e.id === id)?.nome ?? id;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold">Vista Collezione</h1>
        <p className="text-sm text-slate-500">
          Stato aggregato dei manoscritti monitorati e degli ambienti.
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KPI label="Manufatti totali" value={summary.total} />
        <KPI
          label="In stato critico"
          value={summary.critico}
          tone={summary.critico > 0 ? "danger" : "success"}
        />
        <KPI
          label="In attenzione"
          value={summary.attenzione}
          tone={summary.attenzione > 0 ? "warning" : "neutral"}
        />
        <KPI
          label="Alert aperti"
          value={summary.alerts_open}
          tone={summary.alerts_open > 0 ? "warning" : "neutral"}
          hint={summary.alerts_open > 0 ? "Vai alla Vista Alert →" : undefined}
        />
      </div>

      <div className="card">
        <div className="card-title">Layout della collezione</div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {envs.map((env) => {
            const inThis = summary.manuscripts.filter((m) => m.ambiente_id === env.id);
            return (
              <div key={env.id} className="border border-slate-200 rounded-lg p-4 bg-slate-50">
                <div className="flex justify-between items-baseline mb-3">
                  <div>
                    <div className="text-sm font-semibold">{env.nome}</div>
                    <div className="text-xs text-slate-500">{env.tipo}</div>
                  </div>
                  <Link to="/ambiente" className="text-xs underline text-slate-600">
                    apri →
                  </Link>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {inThis.map((m) => (
                    <Link
                      key={m.manuscript_id}
                      to={`/manufatto?id=${m.manuscript_id}`}
                      className="block bg-white border border-slate-200 rounded-md p-3 hover:shadow"
                    >
                      <div className="flex items-center justify-between">
                        <div className="text-xs font-mono text-slate-500">{m.manuscript_id}</div>
                        <SeverityBadge severity={m.severity} />
                      </div>
                      <div className="text-sm font-medium mt-1 line-clamp-2">{m.nome}</div>
                      <div className="text-xs text-slate-500 mt-1">
                        RI<sub>tot</sub> = <span className="font-semibold">{m.RI_Totale.toFixed(1)}%</span>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {summary.alerts_open > 0 && (
        <div className="card border-amber-300 bg-amber-50">
          <div className="card-title text-amber-900">Azioni pendenti</div>
          <p className="text-sm text-amber-900">
            Ci sono <strong>{summary.alerts_open}</strong> alert aperti.{" "}
            <Link to="/alert" className="underline font-semibold">
              Vai alla Vista Alert
            </Link>
          </p>
        </div>
      )}
    </div>
  );
}
