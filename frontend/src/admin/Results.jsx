import React, { useEffect, useState } from "react";
import {
  Trophy, RefreshCw, Loader2, Save, CheckCircle2, AlertTriangle, History, Eye,
} from "lucide-react";
import { api } from "./api";

const ST = {
  pending: { t: "In attesa", c: "bg-amber-100 text-amber-700" },
  won: { t: "Vinta", c: "bg-green-100 text-green-700" },
  lost: { t: "Persa", c: "bg-red-100 text-red-700" },
  void: { t: "Void", c: "bg-gray-200 text-gray-600" },
  postponed: { t: "Rinviata", c: "bg-amber-100 text-amber-700" },
  suspended: { t: "Sospesa", c: "bg-amber-100 text-amber-700" },
  cancelled: { t: "Annullata", c: "bg-gray-200 text-gray-600" },
  manual_review: { t: "Da verificare", c: "bg-[#fde7d6] text-[#c2410c]" },
};
const STATUSES = Object.keys(ST);

const Badge = ({ s, tid }) => {
  const o = ST[s] || { t: s, c: "bg-gray-100 text-gray-600" };
  return <span data-testid={tid} className={`text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full ${o.c}`}>{o.t}</span>;
};

export default function Results() {
  const [status, setStatus] = useState(null);
  const [minValid, setMinValid] = useState(1);
  const [preds, setPreds] = useState([]);
  const [sel, setSel] = useState("");
  const [view, setView] = useState(null);
  const [busy, setBusy] = useState("");
  const [summary, setSummary] = useState(null);
  const [dryRun, setDryRun] = useState(null);

  useEffect(() => {
    api.resultsStatus().then((s) => { setStatus(s); setMinValid(s.settings?.publish_min_valid || 1); }).catch(() => {});
    api.adminPredictions().then((list) => {
      setPreds(list || []);
      if (list && list.length) setSel(`${list[0].season}|${list[0].round}`);
    }).catch(() => {});
  }, []);

  const loadView = (key) => {
    if (!key) return;
    const [season, round] = key.split("|");
    api.resultsView(season, round).then(setView).catch(() => setView(null));
  };
  useEffect(() => { loadView(sel); /* eslint-disable-next-line */ }, [sel]);

  const saveSettings = async (v) => {
    setMinValid(v);
    try { await api.resultsSettings({ publish_min_valid: v }); } catch (e) { /* noop */ }
  };

  const runSettle = async () => {
    if (!sel) return;
    const [season, round] = sel.split("|");
    setBusy("settle"); setSummary(null);
    try {
      const r = await api.resultsSettle({ season, round: parseInt(round, 10) });
      setSummary(r); setDryRun(null);
      loadView(sel);
    } catch (e) { setSummary({ ok: false, error: e.message }); }
    setBusy("");
  };

  const runDryRun = async () => {
    if (!sel) return;
    const [season, round] = sel.split("|");
    setBusy("dry"); setSummary(null);
    try {
      const r = await api.resultsSettle({ season, round: parseInt(round, 10), dry_run: true });
      setDryRun(r);
    } catch (e) { setDryRun({ ok: false, error: e.message }); }
    setBusy("");
  };

  const correct = async (pi, si, newStatus) => {
    const [season, round] = sel.split("|");
    setBusy(`correct-${pi}-${si}`);
    try {
      await api.resultsCorrect({ season, round: parseInt(round, 10), pick_index: pi, selection_index: si, new_status: newStatus, note: "Correzione manuale da admin" });
      loadView(sel);
    } catch (e) { /* noop */ }
    setBusy("");
  };

  const pred = view?.prediction;
  const demo = status?.provider?.demo;

  return (
    <div data-testid="results-page">
      <div className="flex items-center gap-3">
        <Trophy className="w-7 h-7 text-[#EA4E1B]" />
        <h1 className="font-anton text-3xl text-[#1a1411]">Risultati & Settlement</h1>
        {demo && <span data-testid="results-demo-badge" className="inline-flex items-center gap-1 text-[11px] font-bold uppercase tracking-wide bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full"><AlertTriangle className="w-3 h-3" /> Fixture (demo)</span>}
      </div>
      <p className="text-[#6b5d52] mt-1">Esiti calcolati dai risultati ufficiali (mai dall'AI). Le quote restano quelle della grafica del team. Storico versionato e correzioni con audit.</p>

      {/* Impostazioni */}
      <div className="mt-6 grid md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-[#ecdfce] p-5">
          <h2 className="font-archivo font-extrabold text-[#1a1411] mb-2">Provider risultati</h2>
          <p className="text-sm text-[#4a3d34]">Attivo: <code className="text-xs bg-[#fbf7f2] px-2 py-0.5 rounded">{status?.provider?.active}</code></p>
          {demo && <p className="text-amber-700 text-xs mt-2">{status?.provider?.note}</p>}
        </div>
        <div className="bg-white rounded-xl border border-[#ecdfce] p-5">
          <h2 className="font-archivo font-extrabold text-[#1a1411] mb-2">Pubblicazione condizionata</h2>
          <label className="text-xs font-semibold text-[#6b5d52] uppercase">Pubblica con almeno N giocate valide</label>
          <select data-testid="results-minvalid" value={minValid} onChange={(e) => saveSettings(parseInt(e.target.value, 10))} className="w-full mt-1 border border-[#e2d4c2] rounded-lg px-2 py-2 text-sm">
            <option value={1}>1 giocata valida</option>
            <option value={2}>2 giocate valide</option>
            <option value={3}>3 giocate valide</option>
          </select>
        </div>
      </div>

      {/* Selettore giornata + settle */}
      <div className="mt-6 bg-white rounded-xl border border-[#ecdfce] p-5">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[220px]">
            <label className="text-xs font-semibold text-[#6b5d52] uppercase">Giornata</label>
            <select data-testid="results-pred-select" value={sel} onChange={(e) => setSel(e.target.value)} className="w-full mt-1 border border-[#e2d4c2] rounded-lg px-2 py-2 text-sm">
              {preds.map((p) => <option key={`${p.season}|${p.round}`} value={`${p.season}|${p.round}`}>{`${p.competition || "Serie A"} ${p.season} · ${p.round}ª giornata (${(p.picks || []).length} giocate)`}</option>)}
            </select>
          </div>
          <button data-testid="results-dryrun-btn" onClick={runDryRun} disabled={busy === "dry" || busy === "settle" || !sel} className="inline-flex items-center gap-2 bg-white border border-[#e2d4c2] hover:border-[#EA4E1B] text-[#1a1411] text-sm font-bold uppercase tracking-wide px-4 py-2.5 rounded-lg disabled:opacity-60 transition-colors">
            {busy === "dry" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />} Anteprima (dry-run)
          </button>
          <button data-testid="results-settle-btn" onClick={runSettle} disabled={busy === "settle" || !sel} className="inline-flex items-center gap-2 bg-[#EA4E1B] hover:bg-[#d3430f] text-white text-sm font-bold uppercase tracking-wide px-4 py-2.5 rounded-lg disabled:opacity-60 transition-colors">
            {busy === "settle" ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />} Calcola e scrivi
          </button>
        </div>
        {dryRun && (
          <div data-testid="results-dryrun" className="mt-4 text-sm bg-[#fff8f1] border border-[#f0d9c4] rounded-lg p-3 text-[#4a3d34]">
            {dryRun.ok ? (
              <div>
                <p className="flex flex-wrap items-center gap-2 font-semibold"><Eye className="w-4 h-4 text-[#EA4E1B]" /> Anteprima settlement ({dryRun.provider}{dryRun.demo ? " · demo" : ""}) — <span className="text-[#9c8b7d] font-normal">nessuna scrittura nel DB</span> · eventi {dryRun.events_fetched} · API {dryRun.api_calls}{dryRun.retries ? ` · retry ${dryRun.retries}` : ""}:
                  {Object.entries(dryRun.summary || {}).map(([k, v]) => <span key={k} className="ml-1"><Badge s={k} /> {v}</span>)}
                </p>
                <div className="mt-2 space-y-2">
                  {(dryRun.detail || []).length === 0 && <p className="text-[#9c8b7d] italic">Nessuna giocata da analizzare.</p>}
                  {(dryRun.detail || []).map((d, i) => (
                    <div key={i} className="border border-[#f0d9c4] rounded-lg p-2 bg-white">
                      <p className="font-bold text-[#1a1411] flex items-center gap-2">{d.tipster || "Giocata"} <Badge s={d.status} /></p>
                      <ul className="mt-1 space-y-0.5">
                        {d.selections.map((s, j) => (
                          <li key={j} className="text-xs flex flex-wrap items-center gap-2">
                            <span className="text-[#6b5d52]">{s.match} · {s.market} · <b>{s.pick}</b></span>
                            <Badge s={s.settlement.status} />
                            {s.score && <span className="text-[#9c8b7d]">{s.score.home}-{s.score.away}</span>}
                            {!s.mapped && <span className="text-red-600">non mappata</span>}
                            {s.settlement.reason && <span className="text-[#9c8b7d] italic">{s.settlement.reason}</span>}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
                <button onClick={runSettle} disabled={busy === "settle"} data-testid="results-apply-btn" className="mt-3 inline-flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white text-sm font-bold uppercase tracking-wide px-4 py-2 rounded-lg disabled:opacity-60">
                  {busy === "settle" ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />} Applica e scrivi
                </button>
              </div>
            ) : <span className="text-red-600">Errore: {dryRun.error}</span>}
          </div>
        )}
        {summary && (
          <div data-testid="results-summary" className="mt-4 text-sm bg-[#fbf7f2] rounded-lg p-3 text-[#4a3d34]">
            {summary.ok ? (
              <span className="flex flex-wrap items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600" /> Settlement eseguito ({summary.provider}{summary.demo ? " · demo" : ""}):
                {Object.entries(summary.summary || {}).map(([k, v]) => <Badge key={k} s={k} />)}
                {Object.entries(summary.summary || {}).length === 0 && <span>nessuna giocata.</span>}
                {summary.published && <span className="ml-2 text-[#6b5d52]">Pagina: <b>{summary.published.status}</b> ({summary.published.valid_picks}/{summary.published.min_valid})</span>}
              </span>
            ) : <span className="text-red-600">Errore: {summary.error}</span>}
          </div>
        )}
      </div>

      {/* Dettaglio giocate */}
      {pred && (
        <div className="mt-6 space-y-4" data-testid="results-picks">
          {pred.last_settlement && (
            <p className="text-xs text-[#6b5d52] flex items-center gap-1.5"><History className="w-3.5 h-3.5" /> Ultimo settlement: {pred.last_settlement.computed_at?.slice(0, 19).replace("T", " ")} · provider {pred.last_settlement.provider} · storico: {(pred.settlement_history || []).length} versioni · correzioni: {(pred.settlement_audit || []).length}</p>
          )}
          {(pred.picks || []).map((pk, pi) => (
            <div key={pi} className="bg-white rounded-xl border border-[#ecdfce] overflow-hidden" data-testid={`results-pick-${pi}`}>
              <div className="flex items-center justify-between px-5 py-3 bg-[#14100e]">
                <span className="text-white font-archivo font-extrabold">{pk.tipster} <span className="text-[#EA4E1B] text-xs">({(pk.selections || []).length})</span></span>
                {pk.settlement?.status && <Badge s={pk.settlement.status} tid={`results-pick-status-${pi}`} />}
              </div>
              <div className="divide-y divide-[#f0e7da]">
                {(pk.selections || []).map((s, si) => {
                  const st = s.settlement || {};
                  return (
                    <div key={si} className="px-5 py-3 flex flex-wrap items-center justify-between gap-3" data-testid={`results-sel-${pi}-${si}`}>
                      <div className="min-w-0">
                        <p className="font-semibold text-sm text-[#1a1411]">{s.match} {st.manual && <span className="text-[10px] text-[#c2410c] font-bold uppercase">(manuale)</span>}</p>
                        <p className="text-xs text-[#6b5d52]">{s.market} · {s.pick} · quota {s.odds || "—"} {st.reason && <span className="text-[#9c8b7d]">· {st.reason}</span>}</p>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <Badge s={st.status || "pending"} tid={`results-sel-status-${pi}-${si}`} />
                        <select data-testid={`results-correct-${pi}-${si}`} value="" onChange={(e) => e.target.value && correct(pi, si, e.target.value)} disabled={busy === `correct-${pi}-${si}`} className="text-xs border border-[#e2d4c2] rounded px-1.5 py-1">
                          <option value="">Correggi…</option>
                          {STATUSES.map((x) => <option key={x} value={x}>{ST[x].t}</option>)}
                        </select>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
