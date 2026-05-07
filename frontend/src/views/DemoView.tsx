import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { Environment, Scenario } from "@/types";

const SCENARIOS: Array<{ id: Scenario; name: string; trigger: string; effect: string; envType: string }> = [
  {
    id: "A",
    name: "Picco RH",
    trigger: "RH > 65% per 48h+ in deposito sotterraneo",
    effect: "RI_Muffa da attenzione a critica, cluster 1→2/3",
    envType: "deposito_sotterraneo",
  },
  {
    id: "B",
    name: "Oscillazioni T rapide",
    trigger: "ΔT24h > 4 °C per 3 giorni in sala storica P.T.",
    effect: "RI_Meccanico oltre critica, anomalia EN 15757",
    envType: "sala_storica_pt_soppalco",
  },
  {
    id: "C",
    name: "Saturazione VOC",
    trigger: "VOC > 1000 ppb in armadio chiuso",
    effect: "Cluster 2, aumento peso rischio chimico",
    envType: "armadio_chiuso",
  },
  {
    id: "D",
    name: "Esposizione luminosa",
    trigger: "Dose settimanale > 500 lux·ore in biblioteca su miniato",
    effect: "RI_Fotodeterioramento → classe Alto",
    envType: "biblioteca_consultazione",
  },
  {
    id: "E",
    name: "Stratificazione termica",
    trigger: "Gradiente T pavimento-soppalco > 2.5 °C",
    effect: "Modello identifica differenziale al soppalco",
    envType: "sala_storica_pt_soppalco",
  },
];

export function DemoView() {
  const [envs, setEnvs] = useState<Environment[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api.environments().then(setEnvs);
  }, []);

  const run = async (s: typeof SCENARIOS[number]) => {
    const target = envs.find((e) => e.tipo === s.envType);
    if (!target) return;
    setBusy(true);
    setMsg("");
    try {
      await api.triggerScenario(target.id, s.id, 72);
      setMsg(
        `Scenario ${s.id} avviato su ${target.nome}. Apri la Vista Ambiente e la Vista Predittiva per osservare l'evoluzione.`,
      );
    } catch (e: any) {
      setMsg(`Errore: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const reset = async () => {
    setBusy(true);
    await api.resetScenarios();
    setMsg("Tutti gli ambienti riportati a regime nominale.");
    setBusy(false);
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold">Demo Scenarios</h1>
        <p className="text-sm text-slate-500">
          Cinque scenari A–E (D4.2.2.2 Tab.4): inietta un trigger, osserva la migrazione di
          cluster e l'alert generato.
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {SCENARIOS.map((s) => (
          <div key={s.id} className="card">
            <div className="flex items-baseline justify-between">
              <div className="text-sm font-bold">
                Scenario {s.id} — {s.name}
              </div>
              <button className="btn-primary" onClick={() => run(s)} disabled={busy}>
                Avvia
              </button>
            </div>
            <div className="text-xs text-slate-500 mt-1">{s.envType}</div>
            <div className="mt-3 text-sm">
              <div>
                <span className="text-slate-500 text-xs">Trigger:</span> {s.trigger}
              </div>
              <div>
                <span className="text-slate-500 text-xs">Effetto:</span> {s.effect}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-2 items-center">
        <button className="btn-ghost" onClick={reset} disabled={busy}>
          Reset tutti gli ambienti
        </button>
        {msg && <span className="text-sm text-slate-600">{msg}</span>}
      </div>
    </div>
  );
}
