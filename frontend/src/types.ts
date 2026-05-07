// Tipi condivisi (rispecchiano gli schemi Pydantic del backend).

export type EnvironmentType =
  | "armadio_chiuso"
  | "biblioteca_consultazione"
  | "deposito_sotterraneo"
  | "sala_storica_pt_soppalco";

export type Severity = "ottimale" | "accettabile" | "attenzione" | "critico";

export type Quota = "piano_terra" | "soppalco";

export interface Environment {
  id: string;
  nome: string;
  tipo: EnvironmentType;
  inerzia_termo_igrometrica: "alta" | "media" | "bassa";
}

export interface Posizione {
  altezza_dal_pavimento: "<1m" | "1-2m" | ">2m";
  quota: Quota;
  parete_esterna: boolean;
  esposizione_solare: boolean;
}

export interface Manuscript {
  id: string;
  nome: string;
  tipologia_supporto: "pergamena" | "carta_stracciata" | "carta_acida" | "carta_alcalina";
  pH_stimato: number;
  DP0_stimato: number;
  inchiostro_ferro_gallico: boolean;
  pigmenti_fotosensibili: boolean;
  stato_legatura: "buono" | "fragile" | "restaurato" | "compromesso";
  deformazioni_osservate: number;
  fragilita_osservata: number;
  alterazioni_cromatiche: number;
  frequenza_consultazione: "rara" | "occasionale" | "frequente";
  ambiente_id: string;
  posizione: Posizione;
}

export interface TelemetrySample {
  timestamp: string;
  environment_id: string;
  T: number;
  RH: number;
  lux: number;
  UV: number;
  PM2_5: number;
  PM10: number;
  VOC: number;
  CO2: number;
  quota: Quota | null;
}

export interface RiskIndices {
  manuscript_id: string;
  timestamp: string;
  RI_Chimico: number;
  RI_Meccanico: number;
  RI_Insetti: number;
  RI_Muffa: number;
  RI_Fotodeterioramento: number;
  RI_Totale: number;
  severity: Severity;
}

export interface Alert {
  id: string;
  timestamp: string;
  severity: "INFO" | "MEDIA" | "ALTA" | "CRITICA";
  manuscript_id: string;
  environment_id: string;
  trigger_variable: string;
  trigger_value: number;
  RI_Totale: number;
  message: string;
  recommendation_id?: string | null;
  status: "aperto" | "preso_in_carico" | "risolto";
  note?: string | null;
}

export interface DashboardSummary {
  total: number;
  critico: number;
  attenzione: number;
  alerts_open: number;
  manuscripts: Array<{
    manuscript_id: string;
    nome: string;
    ambiente_id: string;
    RI_Totale: number;
    severity: Severity;
  }>;
}

export interface PredictionResponse {
  manuscript_id: string;
  current_RI: number;
  predicted_RI_30d: number;
  RUT_A_days: number;
  RUT_A_lower: number;
  RUT_A_upper: number;
  trajectory: Array<{ t_days: number; RI_pred: number; lower: number; upper: number }>;
  cluster: number;
}

export type Scenario = "none" | "A" | "B" | "C" | "D" | "E";
