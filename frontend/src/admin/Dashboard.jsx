import React, { useEffect, useState } from "react";
import { RefreshCw, CheckCircle2, XCircle, Youtube, ScanLine, TrendingUp, Newspaper } from "lucide-react";
import { api } from "./api";

function StatusDot({ ok }) {
  return ok ? (
    <CheckCircle2 className="w-4 h-4 text-green-600" />
  ) : (
    <XCircle className="w-4 h-4 text-[#c2410c]" />
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [eps, setEps] = useState([]);
  const [preds, setPreds] = useState([]);
  const [logs, setLogs] = useState([]);
  const [syncing, setSyncing] = useState(false);
  const [msg, setMsg] = useState("");

  const load = async () => {
    try {
      const [s, e, p, l] = await Promise.all([
        api.settings(), api.episodes(), api.predictions(), api.logs(8),
      ]);
      setData(s); setEps(e); setPreds(p); setLogs(l);
    } catch (e) {}
  };
  useEffect(() => { load(); }, []);

  const sync = async () => {
    setSyncing(true); setMsg("");
    try {
      const r = await api.syncYoutube();
      setMsg(`Sync completato: ${r.created} nuovi, ${r.updated} aggiornati, ${r.found} trovati.`);
      await load();
    } catch (e) { setMsg("Errore sync: " + e.message); }
    finally { setSyncing(false); }
  };

  const integ = data?.integrations || {};
  const integitems = [
    { k: "Canale YouTube", v: integ.youtube_channel, icon: Youtube },
    { k: "OCR Vision (schedine)", v: integ.vision_ocr, icon: ScanLine },
    { k: "YouTube Data API", v: integ.youtube_api_key, icon: Youtube },
    { k: "Comparatore quote", v: integ.odds_api, icon: TrendingUp },
    { k: "Perplexity (stampa)", v: integ.perplexity, icon: Newspaper },
    { k: "Trascrizione audio", v: integ.audio_transcription, icon: ScanLine },
  ];

  return (
    <div>
      <h1 className="font-anton text-3xl text-[#1a1411]">Dashboard</h1>
      <p className="text-[#6b5d52] mt-1">Panoramica contenuti, automazioni e integrazioni.</p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
        <div className="bg-white rounded-xl border border-[#ecdfce] p-5">
          <p className="text-3xl font-anton text-[#EA4E1B]">{eps.length}</p>
          <p className="text-sm text-[#6b5d52] mt-1">Contenuti</p>
        </div>
        <div className="bg-white rounded-xl border border-[#ecdfce] p-5">
          <p className="text-3xl font-anton text-[#EA4E1B]">{eps.filter((e) => e.type === "intervista").length}</p>
          <p className="text-sm text-[#6b5d52] mt-1">Interviste</p>
        </div>
        <div className="bg-white rounded-xl border border-[#ecdfce] p-5">
          <p className="text-3xl font-anton text-[#EA4E1B]">{preds.length}</p>
          <p className="text-sm text-[#6b5d52] mt-1">Pagine pronostici</p>
        </div>
        <div className="bg-white rounded-xl border border-[#ecdfce] p-5">
          <p className="text-3xl font-anton text-[#EA4E1B]">{eps.filter((e) => e.status === "da_verificare").length}</p>
          <p className="text-sm text-[#6b5d52] mt-1">Da verificare</p>
        </div>
      </div>

      <div className="mt-6 bg-white rounded-xl border border-[#ecdfce] p-5">
        <div className="flex items-center justify-between">
          <h2 className="font-archivo font-extrabold text-[#1a1411]">Sincronizzazione YouTube</h2>
          <button onClick={sync} disabled={syncing} className="inline-flex items-center gap-2 bg-[#EA4E1B] hover:bg-[#d3430f] text-white text-sm font-bold uppercase tracking-wide px-4 py-2.5 rounded-lg disabled:opacity-60">
            <RefreshCw className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`} /> Sincronizza ora
          </button>
        </div>
        {msg && <p className="text-sm text-[#6b5d52] mt-3">{msg}</p>}
      </div>

      <div className="grid md:grid-cols-2 gap-6 mt-6">
        <div className="bg-white rounded-xl border border-[#ecdfce] p-5">
          <h2 className="font-archivo font-extrabold text-[#1a1411] mb-3">Integrazioni</h2>
          <ul className="space-y-2.5">
            {integitems.map((i) => (
              <li key={i.k} className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2 text-[#4a3d34]"><i.icon className="w-4 h-4 text-[#9c8b7d]" /> {i.k}</span>
                <span className="flex items-center gap-1.5"><StatusDot ok={i.v} /> {i.v ? "Attiva" : "Demo / assente"}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="bg-white rounded-xl border border-[#ecdfce] p-5">
          <h2 className="font-archivo font-extrabold text-[#1a1411] mb-3">Ultimi log</h2>
          <ul className="space-y-2 text-sm">
            {logs.length === 0 && <li className="text-[#9c8b7d]">Nessun log.</li>}
            {logs.map((l) => (
              <li key={l.id} className="flex items-start gap-2">
                <StatusDot ok={l.status === "ok"} />
                <span className="text-[#4a3d34]"><strong>{l.kind}</strong> — {l.message}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
