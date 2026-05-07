import type { Severity } from "@/types";

export const severityClass = (s: Severity): string => {
  switch (s) {
    case "ottimale":
      return "bg-emerald-100 text-emerald-800 ring-emerald-300";
    case "accettabile":
      return "bg-lime-100 text-lime-800 ring-lime-300";
    case "attenzione":
      return "bg-amber-100 text-amber-800 ring-amber-300";
    case "critico":
      return "bg-red-100 text-red-800 ring-red-300";
  }
};

export const severityHex = (s: Severity): string =>
  ({
    ottimale: "#16a34a",
    accettabile: "#84cc16",
    attenzione: "#f59e0b",
    critico: "#dc2626",
  } as const)[s];

export const fmtTs = (iso: string): string => {
  const d = new Date(iso);
  return d.toLocaleString("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

export const fmtTime = (iso: string): string => {
  const d = new Date(iso);
  return d.toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });
};
