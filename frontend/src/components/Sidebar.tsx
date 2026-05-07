import { NavLink } from "react-router-dom";
import clsx from "clsx";

const items = [
  { to: "/", label: "Vista Collezione", icon: "📚" },
  { to: "/ambiente", label: "Vista Ambiente", icon: "🌡" },
  { to: "/manufatto", label: "Vista Manufatto", icon: "📜" },
  { to: "/predittiva", label: "Vista Predittiva", icon: "🔮" },
  { to: "/alert", label: "Vista Alert", icon: "🚨" },
  { to: "/demo", label: "Demo Scenarios", icon: "🎬" },
  { to: "/linee-guida", label: "Linee Guida", icon: "📖" },
];

export function Sidebar() {
  return (
    <aside className="w-64 shrink-0 border-r border-slate-200 bg-white h-screen sticky top-0 flex flex-col no-print">
      <div className="px-5 py-5 border-b border-slate-200">
        <div className="text-base font-bold text-slate-900">VoH</div>
        <div className="text-xs text-slate-500">Voices of Heritage</div>
        <div className="text-[10px] text-slate-400 mt-1">CeRICT — Conservatorio di Benevento</div>
      </div>
      <nav className="px-3 py-4 space-y-1 flex-1">
        {items.map((it) => (
          <NavLink
            key={it.to}
            to={it.to}
            end={it.to === "/"}
            className={({ isActive }) =>
              clsx("nav-link", isActive && "nav-link-active")
            }
          >
            <span aria-hidden>{it.icon}</span>
            <span>{it.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="px-4 py-3 text-[10px] text-slate-400 border-t border-slate-200 leading-snug">
        Sistema VoH — CeRICT.<br />
        Architettura predittiva derivata da EFAISTOS<br />
        (Test Before Invest, Polo P.R.I.D.E.).<br />
        Sensore artunified multiparametrico.
      </div>
    </aside>
  );
}
