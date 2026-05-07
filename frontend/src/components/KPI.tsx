import clsx from "clsx";

interface Props {
  label: string;
  value: number | string;
  hint?: string;
  tone?: "neutral" | "warning" | "danger" | "success";
}

const TONE = {
  neutral: "bg-white text-slate-900",
  success: "bg-emerald-50 text-emerald-900 border-emerald-200",
  warning: "bg-amber-50 text-amber-900 border-amber-200",
  danger: "bg-red-50 text-red-900 border-red-200",
};

export function KPI({ label, value, hint, tone = "neutral" }: Props) {
  return (
    <div className={clsx("card", TONE[tone])}>
      <div className="text-xs uppercase tracking-wide text-slate-500 font-semibold">{label}</div>
      <div className="text-3xl font-bold mt-1">{value}</div>
      {hint && <div className="text-xs text-slate-500 mt-1">{hint}</div>}
    </div>
  );
}
