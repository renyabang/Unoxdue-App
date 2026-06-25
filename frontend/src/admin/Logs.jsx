import React, { useEffect, useState } from "react";
import { RefreshCw, CheckCircle2, XCircle, AlertTriangle, Info } from "lucide-react";
import { api } from "./api";

function Icon({ status }) {
  if (status === "ok") return <CheckCircle2 className="w-4 h-4 text-green-600" />;
  if (status === "error") return <XCircle className="w-4 h-4 text-red-500" />;
  if (status === "warning") return <AlertTriangle className="w-4 h-4 text-amber-500" />;
  return <Info className="w-4 h-4 text-[#9c8b7d]" />;
}

export default function Logs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try { setLogs(await api.logs(200)); } catch (e) {}
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-anton text-3xl text-[#1a1411]">Log automazioni</h1>
          <p className="text-[#6b5d52] mt-1">Storico di sync, OCR, quote e rassegna stampa con esito e retry.</p>
        </div>
        <button onClick={load} className="inline-flex items-center gap-2 text-sm font-semibold text-[#EA4E1B]"><RefreshCw className="w-4 h-4" /> Aggiorna</button>
      </div>
      <div className="mt-6 bg-white rounded-xl border border-[#ecdfce] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[#fbf7f2] text-[#6b5d52] text-left">
            <tr>
              <th className="px-4 py-3 font-semibold">Esito</th>
              <th className="px-4 py-3 font-semibold">Tipo</th>
              <th className="px-4 py-3 font-semibold">Messaggio</th>
              <th className="px-4 py-3 font-semibold">Data</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan="4" className="px-4 py-6 text-center text-[#9c8b7d]">Caricamento...</td></tr>}
            {!loading && logs.length === 0 && <tr><td colSpan="4" className="px-4 py-6 text-center text-[#9c8b7d]">Nessun log registrato.</td></tr>}
            {logs.map((l) => (
              <tr key={l.id} className="border-t border-[#f0e7da]">
                <td className="px-4 py-3"><Icon status={l.status} /></td>
                <td className="px-4 py-3 font-medium text-[#1a1411]">{l.kind}</td>
                <td className="px-4 py-3 text-[#4a3d34]">{l.message}</td>
                <td className="px-4 py-3 text-[#9c8b7d] whitespace-nowrap">{(l.created_at || "").replace("T", " ").slice(0, 16)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
