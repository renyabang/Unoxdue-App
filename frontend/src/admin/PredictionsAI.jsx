import React, { useEffect, useState } from "react";
import {
  Sparkles, Loader2, RefreshCw, Eye, CheckCircle2, XCircle, RotateCcw, Send,
  AlertTriangle, ExternalLink, Save, ShieldCheck,
} from "lucide-react";
import { api } from "./api";

const STATUS_BADGE = {
  ai_preview: ["Anteprima AI", "bg-amber-100 text-amber-700"],
  in_review: ["In revisione", "bg-blue-100 text-blue-700"],
  approved: ["Approvata", "bg-green-100 text-green-700"],
  rejected: ["Rifiutata", "bg-red-100 text-red-700"],
  published: ["Pubblicata", "bg-[#14100e] text-white"],
};

function StatusBadge({ s }) {
  const b = STATUS_BADGE[s] || [s || "—", "bg-gray-100 text-gray-600"];
  return <span className={`text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full ${b[1]}`}>{b[0]}</span>;
}

export default function PredictionsAI() {
  const [drafts, setDrafts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [detail, setDetail] = useState(null);
  const [safety, setSafety] = useState(null);
  const [edit, setEdit] = useState(null); // editable fields object
  const [genSeason, setGenSeason] = useState("2025-2026");
  const [genRound, setGenRound] = useState("");

  const refresh = async () => {
    setLoading(true);
    try { const r = await api.predAiList(); setDrafts(r.drafts || []); } catch (e) { /* noop */ }
    setLoading(false);
  };
  useEffect(() => { refresh(); }, []);

  const openDetail = async (d) => {
    setBusy(`open-${d.season}-${d.round}`); setSafety(null); setEdit(null);
    try {
      const r = await api.predAiDetail(d.season, d.round);
      if (r.ok) { setDetail(r); const ad = r.ai_draft || {}; setEdit({ intro: ad.intro || "", context: ad.context || "", picks_summary: ad.picks_summary || "", results_note: ad.results_note || "", disclaimer: ad.disclaimer || "" }); }
    } catch (e) { /* noop */ }
    setBusy("");
  };

  const act = async (fn, key, after) => {
    setBusy(key);
    try { const r = await fn(); if (after) await after(r); await refresh(); } catch (e) { alert(e.message); }
    setBusy("");
  };

  const generate = () => {
    const rn = parseInt(genRound, 10);
    if (!genSeason || !rn) { alert("Inserisci stagione e giornata"); return; }
    act(() => api.predAiGenerate(genSeason, rn), "gen", async (r) => { if (r.ok) await openDetail({ season: genSeason, round: rn }); else alert(r.error || "Errore generazione"); });
  };

  const saveEdit = () => {
    if (!detail) return;
    act(() => api.predAiEdit(detail.season, detail.round, edit, detail.ai_draft.matches), `save-${detail.season}-${detail.round}`, async (r) => { if (r.ok) await openDetail(detail); });
  };
  const setStatus = (action) => act(() => api.predAiStatus(detail.season, detail.round, action), `st-${action}`, async () => await openDetail(detail));
  const regenerate = () => act(() => api.predAiRegenerate(detail.season, detail.round), "regen", async (r) => { if (r.ok) await openDetail(detail); });
  const runSafety = () => act(async () => { const s = await api.predAiSafety(detail.season, detail.round); setSafety(s); return s; }, "safety");
  const publish = async () => {
    if (!window.confirm(`Confermi la PUBBLICAZIONE della giornata ${detail.round} (${detail.season})? L'azione rende pubblica la pagina.`)) return;
    setBusy("pub");
    try {
      const r = await api.predAiPublish(detail.season, detail.round);
      if (r.ok) { alert("Pubblicata: " + r.public_url); await openDetail(detail); await refresh(); }
      else { setSafety({ ok: true, passed: false, checks: r.checks, sources_reachability: r.sources_reachability }); alert(r.error || "Controlli non superati"); }
    } catch (e) { alert(e.message); }
    setBusy("");
  };

  const ad = detail?.ai_draft || {};

  return (
    <div data-testid="predictions-ai-page">
      <div className="flex items-center gap-3 mb-1">
        <Sparkles className="w-6 h-6 text-[#EA4E1B]" />
        <h1 className="font-anton text-3xl text-[#1a1411]">Bozze AI Pronostici</h1>
      </div>
      <p className="text-[#6b5d52] text-sm mb-6">Pipeline Perplexity + LLM attorno alle giocate reali. Nessuna pubblicazione o approvazione automatica: revisione e promozione sono sempre manuali.</p>

      {/* Generatore */}
      <div className="bg-white border border-[#ecdfce] rounded-2xl p-4 mb-6 flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-[11px] font-semibold uppercase tracking-wide text-[#9c8b7d]">Stagione</label>
          <input data-testid="pred-ai-season-input" value={genSeason} onChange={(e) => setGenSeason(e.target.value)} className="mt-1 border border-[#e2d4c2] rounded-lg px-3 py-2 text-sm w-32" placeholder="2025-2026" />
        </div>
        <div>
          <label className="block text-[11px] font-semibold uppercase tracking-wide text-[#9c8b7d]">Giornata</label>
          <input data-testid="pred-ai-round-input" value={genRound} onChange={(e) => setGenRound(e.target.value)} className="mt-1 border border-[#e2d4c2] rounded-lg px-3 py-2 text-sm w-24" placeholder="38" />
        </div>
        <button data-testid="pred-ai-generate-btn" onClick={generate} disabled={busy === "gen"} className="inline-flex items-center gap-2 bg-[#EA4E1B] hover:bg-[#d3430f] text-white text-sm font-bold uppercase tracking-wide px-4 py-2.5 rounded-lg disabled:opacity-60">
          {busy === "gen" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />} Genera bozza
        </button>
        <p className="text-[11px] text-[#9c8b7d] flex-1 min-w-[200px]">Solo per giornate reali con selezioni caricate. La generazione usa Perplexity + LLM (~30-60s).</p>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Lista */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-archivo font-extrabold text-[#1a1411]">Bozze ({drafts.length})</h2>
            <button onClick={refresh} className="text-[#6b5d52] hover:text-[#EA4E1B]"><RefreshCw className="w-4 h-4" /></button>
          </div>
          {loading ? <Loader2 className="w-5 h-5 animate-spin text-[#EA4E1B]" /> : (
            <div className="space-y-3" data-testid="pred-ai-list">
              {drafts.length === 0 && <p className="text-[#9c8b7d] text-sm">Nessuna bozza. Genera la prima qui sopra.</p>}
              {drafts.map((d) => (
                <div key={`${d.season}-${d.round}`} className="bg-white border border-[#ecdfce] rounded-2xl p-4">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-archivo font-extrabold text-[#1a1411]">{d.competition} {d.season} · {d.round}ª</p>
                    <StatusBadge s={d.ai_status} />
                  </div>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-2 text-[12px] text-[#6b5d52]">
                    <span>Generata: {d.generated_at ? new Date(d.generated_at).toLocaleString("it-IT") : "—"}</span>
                    <span>Fonti: {d.sources_count}</span>
                    <span>Costo: ${d.cost ?? 0}</span>
                    <span>Similarità: {d.similarity ?? 0} {d.similarity_passed ? "✓" : "⚠"}</span>
                    <span>Contenuto: {d.episode_url ? "episodio collegato" : "—"}</span>
                    <span>Giocate: {d.picks_count}</span>
                  </div>
                  {d.warnings?.length > 0 && (
                    <p className="text-[11px] text-amber-700 mt-1.5 flex items-start gap-1"><AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" /> {d.warnings.join(" · ")}</p>
                  )}
                  <button data-testid={`pred-ai-open-${d.season}-${d.round}`} onClick={() => openDetail(d)} disabled={busy === `open-${d.season}-${d.round}`} className="mt-3 inline-flex items-center gap-1.5 text-sm font-bold uppercase tracking-wide text-[#EA4E1B] hover:text-[#d3430f]">
                    {busy === `open-${d.season}-${d.round}` ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />} Apri anteprima
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Anteprima / editor */}
        <div>
          {!detail ? <p className="text-[#9c8b7d] text-sm">Seleziona una bozza per l'anteprima.</p> : (
            <div className="bg-white border border-[#ecdfce] rounded-2xl p-5" data-testid="pred-ai-detail">
              <div className="flex items-center justify-between gap-2 mb-3">
                <h2 className="font-archivo font-extrabold text-[#1a1411]">{detail.competition} {detail.season} · {detail.round}ª</h2>
                <StatusBadge s={ad.ai_status} />
              </div>

              {/* Giocate reali utilizzate */}
              <div className="bg-[#fbf7f2] border border-[#efe4d6] rounded-xl p-3 mb-4">
                <p className="text-[11px] font-bold uppercase tracking-wide text-[#9c8b7d] mb-1">Pronostici reali utilizzati ({detail.picks_used?.length || 0})</p>
                {(detail.picks_used || []).map((p, i) => (
                  <p key={i} className="text-[12px] text-[#4a3d34]"><b>{p.tipster}</b> ({p.type}, {p.total_odds}): {(p.selections || []).map((s) => `${s.match} ${s.pick}@${s.odds}`).join("; ")}</p>
                ))}
                <p className="text-[10px] text-[#9c8b7d] mt-1">L'AI non modifica mai le giocate reali.</p>
              </div>

              {/* Editor sezioni */}
              {edit && ["intro", "context", "picks_summary", "results_note", "disclaimer"].map((f) => (
                <div key={f} className="mb-3">
                  <label className="block text-[11px] font-bold uppercase tracking-wide text-[#6b5d52] mb-1">{f.replace("_", " ")}</label>
                  <textarea data-testid={`pred-ai-field-${f}`} value={edit[f]} onChange={(e) => setEdit({ ...edit, [f]: e.target.value })} rows={f === "intro" || f === "context" || f === "picks_summary" ? 3 : 2} className="w-full border border-[#e2d4c2] rounded-lg px-3 py-2 text-sm" />
                </div>
              ))}

              {/* Partite */}
              {ad.matches?.length > 0 && (
                <div className="mb-3">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-[#6b5d52] mb-1">Partite ({ad.matches.length})</p>
                  <div className="space-y-1 max-h-40 overflow-y-auto text-[12px] text-[#4a3d34]">
                    {ad.matches.map((m, i) => <p key={i}><b>{m.match}</b>: {m.comment}</p>)}
                  </div>
                </div>
              )}

              {/* Fonti */}
              <div className="mb-3">
                <p className="text-[11px] font-bold uppercase tracking-wide text-[#6b5d52] mb-1">Fonti esterne ({ad.sources?.length || 0})</p>
                {(ad.sources || []).map((s, i) => (
                  <a key={i} href={s.url} target="_blank" rel="noopener noreferrer" className="block text-[12px] text-[#EA4E1B] hover:underline truncate"><ExternalLink className="w-3 h-3 inline mr-1" />{s.publisher || s.url}{s.date ? ` · ${s.date}` : ""}</a>
                ))}
                {ad.external_facts && <details className="mt-1"><summary className="text-[11px] text-[#9c8b7d] cursor-pointer">Fatti esterni associati</summary><p className="text-[12px] text-[#6b5d52] mt-1 whitespace-pre-line">{ad.external_facts}</p></details>}
              </div>

              {/* Bassa confidence */}
              {ad.low_confidence?.length > 0 && (
                <div className="mb-3 bg-amber-50 border border-amber-200 rounded-xl p-3" data-testid="pred-ai-lowconf">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-amber-700 mb-1">Frasi a bassa confidence ({ad.low_confidence.length})</p>
                  {ad.low_confidence.map((l, i) => <p key={i} className="text-[12px] text-amber-800">[{l.where}] {l.text}</p>)}
                </div>
              )}

              {/* Confronto con pubblicato */}
              {detail.published_editorial && (
                <details className="mb-3"><summary className="text-[11px] font-bold uppercase tracking-wide text-[#6b5d52] cursor-pointer">Confronto con il contenuto pubblicato</summary>
                  <p className="text-[12px] text-[#6b5d52] mt-1 whitespace-pre-line">{detail.published_editorial.context}</p>
                </details>
              )}

              {/* Controlli sicurezza */}
              {safety?.checks && (
                <div className="mb-3 bg-[#fbf7f2] border border-[#efe4d6] rounded-xl p-3" data-testid="pred-ai-safety">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-[#6b5d52] mb-1">Controlli pre-pubblicazione {safety.passed ? "✅" : "⛔"}</p>
                  {Object.entries(safety.checks).map(([k, v]) => (
                    <p key={k} className="text-[12px]">{v ? <CheckCircle2 className="w-3.5 h-3.5 inline text-green-600" /> : <XCircle className="w-3.5 h-3.5 inline text-red-600" />} {k.replace(/_/g, " ")}</p>
                  ))}
                </div>
              )}

              {/* Azioni */}
              <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t border-[#f0e7da]">
                <button data-testid="pred-ai-save-btn" onClick={saveEdit} disabled={busy.startsWith("save")} className="inline-flex items-center gap-1.5 border border-[#e2d4c2] text-[#4a3d34] hover:bg-[#fbf7f2] text-xs font-bold uppercase tracking-wide px-2.5 py-1.5 rounded-lg disabled:opacity-60"><Save className="w-3.5 h-3.5" /> Salva modifiche</button>
                <button data-testid="pred-ai-approve-btn" onClick={() => setStatus("approve")} disabled={busy === "st-approve"} className="inline-flex items-center gap-1.5 bg-green-600 hover:bg-green-700 text-white text-xs font-bold uppercase tracking-wide px-2.5 py-1.5 rounded-lg disabled:opacity-60"><CheckCircle2 className="w-3.5 h-3.5" /> Approva</button>
                <button data-testid="pred-ai-reject-btn" onClick={() => setStatus("reject")} disabled={busy === "st-reject"} className="inline-flex items-center gap-1.5 border border-red-300 text-red-600 hover:bg-red-50 text-xs font-bold uppercase tracking-wide px-2.5 py-1.5 rounded-lg disabled:opacity-60"><XCircle className="w-3.5 h-3.5" /> Rifiuta</button>
                <button data-testid="pred-ai-review-btn" onClick={() => setStatus("review")} disabled={busy === "st-review"} className="inline-flex items-center gap-1.5 border border-[#e2d4c2] text-[#4a3d34] hover:bg-[#fbf7f2] text-xs font-bold uppercase tracking-wide px-2.5 py-1.5 rounded-lg disabled:opacity-60"><RotateCcw className="w-3.5 h-3.5" /> In revisione</button>
                <button data-testid="pred-ai-regenerate-btn" onClick={regenerate} disabled={busy === "regen"} className="inline-flex items-center gap-1.5 border border-[#e2d4c2] text-[#4a3d34] hover:bg-[#fbf7f2] text-xs font-bold uppercase tracking-wide px-2.5 py-1.5 rounded-lg disabled:opacity-60">{busy === "regen" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />} Rigenera</button>
                <button data-testid="pred-ai-safety-btn" onClick={runSafety} disabled={busy === "safety"} className="inline-flex items-center gap-1.5 border border-[#e2d4c2] text-[#4a3d34] hover:bg-[#fbf7f2] text-xs font-bold uppercase tracking-wide px-2.5 py-1.5 rounded-lg disabled:opacity-60">{busy === "safety" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />} Verifica</button>
                <button data-testid="pred-ai-publish-btn" onClick={publish} disabled={busy === "pub"} className="inline-flex items-center gap-1.5 bg-[#14100e] hover:bg-black text-white text-xs font-bold uppercase tracking-wide px-2.5 py-1.5 rounded-lg disabled:opacity-60">{busy === "pub" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />} Promuovi a pubblicato</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
