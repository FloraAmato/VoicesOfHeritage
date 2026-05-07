import type { Severity } from "@/types";
import { severityClass } from "@/lib/format";

const LABEL: Record<Severity, string> = {
  ottimale: "Ottimale",
  accettabile: "Accettabile",
  attenzione: "Attenzione",
  critico: "Critico",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ring-1 ${severityClass(
        severity,
      )}`}
    >
      ● {LABEL[severity]}
    </span>
  );
}
