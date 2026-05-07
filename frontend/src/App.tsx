import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/Sidebar";

export default function App() {
  return (
    <div className="min-h-screen flex">
      <Sidebar />
      <main className="flex-1 px-8 py-6">
        <Outlet />
        <footer className="mt-12 pt-4 border-t border-slate-200 text-xs text-slate-500 leading-relaxed no-print">
          Sistema VoH — CeRICT — Architettura predittiva derivata da EFAISTOS
          (Test Before Invest, Polo P.R.I.D.E.). Sensore artunified multiparametrico.
        </footer>
      </main>
    </div>
  );
}
