import React, { useEffect, useState } from "react";
import {
  Youtube, RefreshCw, Loader2, Radio, KeyRound, FileText,
  CheckCircle2, XCircle, AlertTriangle, Download,
} from "lucide-react";
import { api } from "./api";

const DemoBadge = () => (
  <span data-testid="demo-badge" className="inline-flex items-center gap-1 text-[11px] font-bold uppercase tracking-wide bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
    <AlertTriangle className="w-3 h-3" /> Demo
  </span>
);

const Stat = ({ label, value, tid }) => (
  <div className="bg-[#fbf7f2] rounded-lg px-4 py-3">
    <div className="text-[#6b5d52] text-xs font-semibold uppercase tracking-wide">{label}</div>
    <div data-testid={tid} className="font-anton text-2xl text-[#1a1411] mt-0.5">{value ?? "—"}</div>
  </div>
);

const TRANS_LABELS = {
  pending: { t: "In attesa", c: "bg-amber-100 text-amber-700" },
  done: { t: "Completata", c: "bg-green-100 text-green-700" },
  unavailable: { t: "Non disponibile", c: "bg-gray-200 text-gray-600" },
  error: { t: "Errore", c: "bg-red-100 text-red-700" },
};

export default function YouTube() {
  const [stats, setStats] = useState(null);
  const [websub, setWebsub] = useState(null);
  const [oauth, setOauth] = useState(null);
  const [trans, setTrans] = useState(null);
  const [busy, setBusy] = useState("");
  const [backfillRes, setBackfillRes] = useState(null);
  const [autoPublish, setAutoPublish] = useState(true);

  const loadAll = () => {
    api.youtubeStats().then(setStats).catch(() => {});
    api.websubStatus().then(setWebsub).catch(() => {});
    api.oauthStatus().then(setOauth).catch(() => {});
    api.transcripts().then(setTrans).catch(() => {});
  };
  useEffect(loadAll, []);

  const runBackfill = async () => {
    setBusy("backfill"); setBackfillRes(null);
    try {
      const r = await api.youtubeBackfill({ max_pages: 40, auto_publish: autoPublish });
      setBackfillRes(r);
      api.youtubeStats().then(setStats).catch(() => {});
      api.transcripts().then(setTrans).catch(() => {});
    } catch (e) { setBackfillRes({ ok: false, error: e.message }); }
    setBusy("");
  };

  const subscribe = async (mode) => {
    setBusy("websub-" + mode);
    try {
      await api.websubSubscribe(mode);
      api.websubStatus().then(setWebsub).catch(() => {});
    } catch (e) { /* loggato lato server */ }
    setBusy("");
  };

  const getTranscript = async (slug) => {
    setBusy("trans-" + slug);
    try {
      await api.fetchTranscript(slug);
      api.transcripts().then(setTrans).catch(() => {});
    } catch (e) { /* noop */ }
    setBusy("");
  };

  const isDemo = stats?.demo;

  return (
    <div data-testid="youtube-page">
      <div className="flex items-center gap-3">
        <Youtube className="w-7 h-7 text-[#EA4E1B]" />
        <h1 className="font-anton text-3xl text-[#1a1411]">Archivio YouTube</h1>
        {isDemo && <DemoBadge />}
      </div>
      <p className="text-[#6b5d52] mt-1">
        Sincronizzazione completa del canale via Data API, notifiche in tempo reale (WebSub) e
        trascrizioni dai sottotitoli ufficiali. Senza chiavi API restano attive le funzioni demo (feed RSS).
      </p>

      {/* ---- Statistiche canale ---- */}
      <div className="mt-6 bg-white rounded-xl border border-[#ecdfce] p-5">
        <h2 className="font-archivo font-extrabold text-[#1a1411] mb-4">Statistiche canale</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Stat label="Video sul canale" value={stats?.video_count} tid="yt-video-count" />
          <Stat label="Iscritti" value={stats?.subscriber_count} tid="yt-subs" />
          <Stat label="Visualizzazioni" value={stats?.view_count} tid="yt-views" />
          <Stat label="Importati in archivio" value={stats?.imported} tid="yt-imported" />
        </div>
        {isDemo && <p className="text-amber-700 text-sm mt-3">{stats?.note}</p>}

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button data-testid="yt-backfill-btn" onClick={runBackfill} disabled={busy === "backfill"}
            className="inline-flex items-center gap-2 bg-[#EA4E1B] hover:bg-[#d3430f] text-white text-sm font-bold uppercase tracking-wide px-4 py-2.5 rounded-lg disabled:opacity-60 transition-colors">
            {busy === "backfill" ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            Importa archivio completo
          </button>
          <label className="inline-flex items-center gap-2 text-sm text-[#4a3d34]">
            <input data-testid="yt-autopublish" type="checkbox" checked={autoPublish}
              onChange={(e) => setAutoPublish(e.target.checked)} className="accent-[#EA4E1B]" />
            Pubblica automaticamente i nuovi contenuti
          </label>
        </div>

        {backfillRes && (
          <div data-testid="yt-backfill-result" className="mt-4 text-sm bg-[#fbf7f2] rounded-lg p-3 text-[#4a3d34]">
            {backfillRes.ok ? (
              <>
                {backfillRes.demo && <DemoBadge />}{" "}
                <span className="font-semibold">{backfillRes.created ?? 0}</span> nuovi,{" "}
                <span className="font-semibold">{backfillRes.updated ?? 0}</span> aggiornati
                {typeof backfillRes.skipped_shorts === "number" && <> , {backfillRes.skipped_shorts} short saltati</>}
                {backfillRes.pages && <> — {backfillRes.pages} pagine</>}
                {backfillRes.note && <p className="text-amber-700 mt-1">{backfillRes.note}</p>}
              </>
            ) : (
              <span className="text-red-600">Errore: {backfillRes.error}</span>
            )}
          </div>
        )}
      </div>

      {/* ---- WebSub ---- */}
      <div className="mt-6 bg-white rounded-xl border border-[#ecdfce] p-5">
        <div className="flex items-center gap-2 mb-3">
          <Radio className="w-5 h-5 text-[#EA4E1B]" />
          <h2 className="font-archivo font-extrabold text-[#1a1411]">Notifiche in tempo reale (WebSub)</h2>
        </div>
        <div className="text-sm text-[#4a3d34] space-y-1">
          <div><span className="text-[#6b5d52]">Callback:</span> <code data-testid="websub-callback" className="text-xs bg-[#fbf7f2] px-2 py-1 rounded break-all">{websub?.callback}</code></div>
          <div><span className="text-[#6b5d52]">Topic:</span> <code className="text-xs bg-[#fbf7f2] px-2 py-1 rounded break-all">{websub?.topic}</code></div>
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <button data-testid="websub-subscribe-btn" onClick={() => subscribe("subscribe")} disabled={busy === "websub-subscribe"}
            className="inline-flex items-center gap-2 bg-[#14100e] hover:bg-[#EA4E1B] text-white text-sm font-bold uppercase tracking-wide px-4 py-2.5 rounded-lg disabled:opacity-60 transition-colors">
            {busy === "websub-subscribe" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Radio className="w-4 h-4" />} Iscrivi
          </button>
          <button data-testid="websub-unsubscribe-btn" onClick={() => subscribe("unsubscribe")} disabled={busy === "websub-unsubscribe"}
            className="inline-flex items-center gap-2 border border-[#ecdfce] text-[#4a3d34] hover:bg-[#fbf7f2] text-sm font-bold uppercase tracking-wide px-4 py-2.5 rounded-lg disabled:opacity-60 transition-colors">
            Disiscrivi
          </button>
        </div>

        {websub?.subscriptions?.length > 0 && (
          <div data-testid="websub-subs" className="mt-4 text-sm">
            {websub.subscriptions.map((s, i) => (
              <div key={i} className="flex items-center gap-2 text-[#4a3d34]">
                <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded-full ${s.status === "verified" ? "bg-green-100 text-green-700" : s.status === "error" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}`}>{s.status}</span>
                <span className="text-[#6b5d52]">HTTP {s.http_status ?? "—"}{s.expires_at ? ` · scade ${s.expires_at.slice(0, 10)}` : ""}</span>
              </div>
            ))}
          </div>
        )}

        <h3 className="font-semibold text-[#1a1411] mt-5 mb-2 text-sm uppercase tracking-wide">Eventi recenti</h3>
        <div data-testid="websub-events" className="space-y-1 max-h-56 overflow-auto">
          {(websub?.events || []).length === 0 && <p className="text-[#6b5d52] text-sm">Nessun evento WebSub registrato.</p>}
          {(websub?.events || []).map((e, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-[#4a3d34] border-t border-[#f0e7da] py-1.5">
              {e.status === "ok" ? <CheckCircle2 className="w-3.5 h-3.5 text-green-600 mt-0.5" /> : e.status === "error" ? <XCircle className="w-3.5 h-3.5 text-red-600 mt-0.5" /> : <AlertTriangle className="w-3.5 h-3.5 text-amber-600 mt-0.5" />}
              <span className="text-[#9b8a7b] tabular-nums">{(e.created_at || "").slice(0, 19).replace("T", " ")}</span>
              <span>{e.message}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ---- OAuth + trascrizioni ---- */}
      <div className="mt-6 bg-white rounded-xl border border-[#ecdfce] p-5">
        <div className="flex items-center gap-2 mb-3">
          <KeyRound className="w-5 h-5 text-[#EA4E1B]" />
          <h2 className="font-archivo font-extrabold text-[#1a1411]">Sottotitoli e trascrizioni (OAuth)</h2>
          {oauth && (oauth.configured
            ? <span className="text-[11px] font-bold uppercase bg-green-100 text-green-700 px-2 py-0.5 rounded-full">OAuth attivo</span>
            : <span data-testid="oauth-demo" className="text-[11px] font-bold uppercase bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">OAuth non configurato</span>)}
        </div>
        <p className="text-[#6b5d52] text-sm">{oauth?.note}</p>

        {trans?.counts && (
          <div className="mt-3 flex flex-wrap gap-2">
            {Object.entries(trans.counts).map(([k, v]) => (
              <span key={k} className={`text-xs font-bold uppercase px-2.5 py-1 rounded-full ${(TRANS_LABELS[k] || {}).c || "bg-gray-100 text-gray-600"}`}>
                {(TRANS_LABELS[k] || {}).t || k}: {v}
              </span>
            ))}
          </div>
        )}

        <div className="mt-4 bg-[#fbf7f2] rounded-lg border border-[#f0e7da] overflow-hidden">
          <table className="w-full text-sm">
            <thead className="text-[#6b5d52] text-left">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Contenuto</th>
                <th className="px-4 py-2.5 font-semibold">Trascrizione</th>
                <th className="px-4 py-2.5 font-semibold text-right">Azione</th>
              </tr>
            </thead>
            <tbody data-testid="transcripts-table">
              {(trans?.episodes || []).slice(0, 30).map((e) => {
                const lbl = TRANS_LABELS[e.transcription_status] || { t: e.transcription_status, c: "bg-gray-100 text-gray-600" };
                return (
                  <tr key={e.slug} className="border-t border-[#f0e7da]">
                    <td className="px-4 py-2.5 text-[#1a1411] font-medium">{e.title}</td>
                    <td className="px-4 py-2.5">
                      <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded-full ${lbl.c}`}>{lbl.t}</span>
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <button data-testid={`transcript-fetch-${e.slug}`} onClick={() => getTranscript(e.slug)}
                        disabled={busy === "trans-" + e.slug}
                        className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-[#EA4E1B] hover:text-[#d3430f] disabled:opacity-50">
                        {busy === "trans-" + e.slug ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                        Recupera
                      </button>
                    </td>
                  </tr>
                );
              })}
              {(trans?.episodes || []).length === 0 && (
                <tr><td colSpan={3} className="px-4 py-4 text-[#6b5d52]">Nessun contenuto con video YouTube.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
