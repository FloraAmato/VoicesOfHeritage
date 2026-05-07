import { useEffect, useState } from "react";
import { api } from "@/api/client";

interface GuidelineEnv {
  id: string;
  titolo: string;
  profilo_criticita: string;
  variabili_critiche: string[];
  soglie_operative: Record<string, string>;
  alert_tipici: string[];
  buone_pratiche: string[];
}

const GUIDELINES: GuidelineEnv[] = [
  {
    id: "armadio_chiuso",
    titolo: "Armadio climatizzato",
    profilo_criticita:
      "Inerzia termo-igrometrica alta. Rischio chimico dominante per accumulo VOC endogeni; rischio biologico secondario. Le aperture sono il principale evento perturbante.",
    variabili_critiche: ["PM/VOC (peso 0.9)", "rischio_insetti (0.7)", "rischio_muffa_LIM (0.6)"],
    soglie_operative: {
      "T": "16–22 °C, ΔT24h < 1.5 °C",
      "RH": "45–55%, ΔRH24h < 5%",
      "VOC": "ricambio aria se > 500 ppb persistenti",
      "lux": "buio in chiusura; max 50 lux a porte aperte",
    },
    alert_tipici: [
      "Saturazione VOC > 1000 ppb (Scenario C) → ventilazione 30 min/g per 7 gg",
      "Apertura prolungata > 4h → bilancio igrometrico alterato",
    ],
    buone_pratiche: [
      "Ricambio aria controllato post-apertura (60 min con HVAC dedicato)",
      "Carbone attivo / scavengers per VOC catalitici",
      "Schede di consultazione con tracking aperture",
      "Verifica trimestrale guarnizioni e tenuta",
    ],
  },
  {
    id: "biblioteca_consultazione",
    titolo: "Biblioteca di consultazione",
    profilo_criticita:
      "Inerzia media. Picchi luminosi durante l'apertura, oscillazioni RH/T da affluenza. Il fotodeterioramento è il rischio dominante per pigmenti sensibili.",
    variabili_critiche: ["illuminamento (1.0)", "dRH_24h (0.8)", "RH_media_30gg (0.7)", "dT_24h (0.7)"],
    soglie_operative: {
      "T": "19–22 °C, ΔT24h < 2.5 °C",
      "RH": "45–55%, ΔRH24h < 8%",
      "lux": "max 50 per pigmenti sensibili / 150 generale; UV < 30 µW/lm",
      "Dose settimanale": "< 500 lux·h su miniato",
    },
    alert_tipici: [
      "Esposizione luminosa > soglia (Scenario D) → rotazione manufatto / filtri UV",
      "Affluenza alta → verifica HVAC e turni di consultazione",
    ],
    buone_pratiche: [
      "Filtri UV su finestre + tendaggi a luce diffusa",
      "Leggii con illuminazione localizzata a LED dimmerati",
      "Rotazione esposizione manufatti miniati ogni 6–12 mesi",
      "Controllo accessi con prenotazione",
    ],
  },
  {
    id: "deposito_sotterraneo",
    titolo: "Deposito sotterraneo",
    profilo_criticita:
      "Inerzia alta in T, RH cronicamente sopra soglia. Rischio biologico dominante (muffa, insetti). Il rischio meccanico è basso, il chimico moderato.",
    variabili_critiche: ["RH_media_30gg (0.9)", "rischio_muffa_LIM (1.0)", "rischio_insetti (0.9)"],
    soglie_operative: {
      "T": "14–18 °C stabile",
      "RH": "< 60%, mai > 65% per più di 24h",
      "Ore sopra LIM Sedlbauer/anno": "< 260 (≈3%)",
      "PM10": "< 40 µg/m³",
    },
    alert_tipici: [
      "Picco RH > 65% per 48h+ (Scenario A) → ispezione visiva e verifica deumidificatori",
      "Trappole entomologiche con catture > 2/mese",
    ],
    buone_pratiche: [
      "Deumidificatori ridondanti + setpoint 55%",
      "Barriere al vapore su pareti contro-terra",
      "Trappole entomologiche con monitoraggio mensile",
      "Incapsulamento in scatole conservative passive per pezzi di pregio",
    ],
  },
  {
    id: "sala_storica_pt_soppalco",
    titolo: "Sala storica monumentale (P.T. + Soppalco)",
    profilo_criticita:
      "Inerzia bassa, ampia escursione stagionale, stratificazione termica P.T./soppalco. Il rischio meccanico è il dominante; rischio fotodeterioramento secondario per esposizioni dirette.",
    variabili_critiche: [
      "dRH_24h (1.0)", "gradiente_verticale_T (1.0)", "dT_24h (0.9)",
      "illuminamento (0.9)", "T_media_24h (0.8)",
    ],
    soglie_operative: {
      "T": "16–24 °C, ΔT24h < 2.5 °C",
      "RH": "45–60%, ΔRH24h < 8%",
      "Gradiente verticale T": "< 2.5 °C tra P.T. e soppalco",
      "lux": "max 150 generale; max 50 per miniati",
    },
    alert_tipici: [
      "Oscillazioni T rapide (Scenario B) → verifica HVAC e ventilazione",
      "Stratificazione > 2.5 °C (Scenario E) → redistribuzione manufatti più fragili al P.T.",
    ],
    buone_pratiche: [
      "HVAC con sensori in più punti (P.T. + soppalco)",
      "Ventilazione attiva per ridurre stratificazione",
      "Manufatti più fragili al piano terra (T più stabile)",
      "Manutenzione programmata serramenti (riduzione infiltrazioni)",
    ],
  },
];

const COMPARATIVE_TABLE: Array<{ ambiente: string; chimico: string; meccanico: string; muffa: string; insetti: string; foto: string; aria: string }> = [
  { ambiente: "Armadio chiuso", chimico: "alto", meccanico: "basso", muffa: "medio", insetti: "medio", foto: "basso", aria: "alto" },
  { ambiente: "Biblioteca", chimico: "medio", meccanico: "medio", muffa: "basso", insetti: "basso", foto: "alto", aria: "medio" },
  { ambiente: "Deposito sotterraneo", chimico: "medio", meccanico: "basso", muffa: "alto", insetti: "alto", foto: "basso", aria: "medio" },
  { ambiente: "Sala storica P.T./soppalco", chimico: "medio", meccanico: "alto", muffa: "medio", insetti: "medio", foto: "alto", aria: "medio" },
];

const RISK_COLOR = (l: string) =>
  l === "alto"
    ? "bg-red-100 text-red-800"
    : l === "medio"
    ? "bg-amber-100 text-amber-800"
    : "bg-emerald-100 text-emerald-800";

export function GuidelinesView() {
  const [active, setActive] = useState(GUIDELINES[0].id);
  const [weights, setWeights] = useState<Record<string, Record<string, number>>>({});

  useEffect(() => {
    api.weightsAll().then(setWeights);
  }, []);

  const cur = GUIDELINES.find((g) => g.id === active)!;
  const w = weights[active] ?? {};

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">Linee Guida</h1>
          <p className="text-sm text-slate-500">
            Linee guida operative per i 4 contesti ambientali (D4.2.2.2 §10).
          </p>
        </div>
        <button className="btn-ghost no-print" onClick={() => window.print()}>
          🖨 Stampa PDF
        </button>
      </header>

      <div className="flex gap-2 flex-wrap no-print">
        {GUIDELINES.map((g) => (
          <button
            key={g.id}
            className={`btn ${active === g.id ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setActive(g.id)}
          >
            {g.titolo}
          </button>
        ))}
      </div>

      <div className="card print-page">
        <h2 className="text-xl font-bold mb-3">{cur.titolo}</h2>
        <section className="mb-4">
          <h3 className="text-sm font-semibold uppercase text-slate-500 mb-1">Profilo di criticità</h3>
          <p className="text-sm">{cur.profilo_criticita}</p>
        </section>

        <section className="mb-4">
          <h3 className="text-sm font-semibold uppercase text-slate-500 mb-1">Variabili critiche prioritarie</h3>
          <ul className="text-sm list-disc list-inside">
            {cur.variabili_critiche.map((v, i) => (
              <li key={i}>{v}</li>
            ))}
          </ul>
          {Object.keys(w).length > 0 && (
            <div className="mt-2 grid grid-cols-3 gap-2 text-xs bg-slate-50 p-3 rounded-md">
              {Object.entries(w).map(([var_, val]) => (
                <div key={var_} className="flex justify-between">
                  <span>{var_}</span>
                  <strong className={val >= 0.9 ? "text-red-700" : val >= 0.7 ? "text-amber-700" : ""}>
                    {val.toFixed(2)}
                  </strong>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="mb-4">
          <h3 className="text-sm font-semibold uppercase text-slate-500 mb-1">Soglie operative</h3>
          <table className="text-sm w-full">
            <tbody>
              {Object.entries(cur.soglie_operative).map(([k, v]) => (
                <tr key={k} className="border-b border-slate-100">
                  <td className="py-1 pr-3 text-slate-500">{k}</td>
                  <td className="py-1">{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="mb-4">
          <h3 className="text-sm font-semibold uppercase text-slate-500 mb-1">Alert e consigli tipici</h3>
          <ul className="text-sm list-disc list-inside">
            {cur.alert_tipici.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </section>

        <section>
          <h3 className="text-sm font-semibold uppercase text-slate-500 mb-1">Buone pratiche conservative</h3>
          <ul className="text-sm list-disc list-inside">
            {cur.buone_pratiche.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
        </section>
      </div>

      <div className="card print-page">
        <div className="card-title">Tabella sinottica — rischi dominanti per contesto (D4.2.2.2 Tab.6)</div>
        <table className="w-full text-sm">
          <thead className="text-xs uppercase text-slate-500">
            <tr>
              <th className="text-left py-2">Ambiente</th>
              <th>Chimico</th>
              <th>Meccanico</th>
              <th>Muffa</th>
              <th>Insetti</th>
              <th>Fotodet.</th>
              <th>Qualità aria</th>
            </tr>
          </thead>
          <tbody>
            {COMPARATIVE_TABLE.map((r) => (
              <tr key={r.ambiente} className="border-b border-slate-100">
                <td className="py-2 font-medium">{r.ambiente}</td>
                {[r.chimico, r.meccanico, r.muffa, r.insetti, r.foto, r.aria].map((v, i) => (
                  <td key={i} className="text-center">
                    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${RISK_COLOR(v)}`}>{v}</span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
