import React, { useEffect, useState } from "react";
import {
  Sparkles, Loader2, Eye, CheckCircle2, RefreshCw, AlertTriangle, X, FileText,
  Clock, Quote, ChevronUp, ChevronDown, Trash2, Plus, Save, Pencil,
} from "lucide-react";
import { api } from "./api";

const STATUS_BADGE = {
  published: { label: "Pubblicato", cls: "bg-green-100 text-green-700" },
  preview: { label: "Anteprima", cls: "bg-amber-100 text-amber-700" },
  none: { label: "Da generare", cls: "bg-[#efe4d6] text-[#9c8b7d]" },
};

function Field({ label, children }) {
  return (
    <div className="mb-3">
      <p className="text-[11px] font-bold uppercase tracking-wide text-[#9c8b7d]">{label}</p>
      <div className="text-sm text-[#1a1411] mt-0.5">{children}</div>
    </div>
  );
}

function SectionEditor({ sections, setSections }) {
  const update = (i, patch) => setSections(sections.map((s, idx) => (idx === i ? { ...s, ...patch } : s)));
  const move = (i, dir) => {
    const j = i + dir;
    if (j < 0 || j >= sections.length) return;
    const arr = [...sections];
    [arr[i], arr[j]] = [arr[j], arr[i]];
    setSections(arr);
  };
  const remove = (i) => setSections(sections.filter((_, idx) => idx !== i));
  const add = () => setSections([...sections, { id: `nuova-${Date.now()}`, level: 2, heading: "Nuova sezione", paragraphs: [""], source_segment_ids: [], confidence: 0.6 }]);

  const headings = sections.map((s) => (s.heading || "").trim().toLowerCase());
  return (
    <div data-testid="section-editor">
      {sections.map((s, i) => {
        const dupe = headings.indexOf((s.heading || "").trim().toLowerCase()) !== i;
        const empty = !(s.heading || "").trim();
        const badH3First = i === 0 && s.level === 3;
        return (
          <div key={i} className="border border-[#ecdfce] rounded-xl p-3 mb-3 bg-[#fbf7f2]/40" data-testid={`section-edit-${i}`}>
            <div className="flex items-center gap-2 mb-2">
              <select value={s.level} onChange={(e) => update(i, { level: Number(e.target.value) })} data-testid={`section-level-${i}`} className="border border-[#ecdfce] rounded-md px-2 py-1 text-xs font-bold bg-white">
                <option value={2}>H2</option>
                <option value={3}>H3</option>
              </select>
              <input value={s.heading} onChange={(e) => update(i, { heading: e.target.value })} data-testid={`section-heading-${i}`} className={`flex-1 border rounded-md px-2 py-1 text-sm bg-white ${empty || dupe || badH3First ? "border-red-400" : "border-[#ecdfce]"}`} placeholder="Titolo sezione" />
              <button onClick={() => move(i, -1)} className="p-1 rounded hover:bg-white" title="Su"><ChevronUp className="w-4 h-4" /></button>
              <button onClick={() => move(i, 1)} className="p-1 rounded hover:bg-white" title="Giù"><ChevronDown className="w-4 h-4" /></button>
              <button onClick={() => remove(i)} data-testid={`section-remove-${i}`} className="p-1 rounded hover:bg-red-50 text-red-500" title="Rimuovi"><Trash2 className="w-4 h-4" /></button>
            </div>
            {(badH3First || dupe || empty) && <p className="text-xs text-red-600 mb-1">{empty ? "Titolo vuoto. " : ""}{dupe ? "Titolo duplicato. " : ""}{badH3First ? "La prima sezione non può essere H3." : ""}</p>}
            {s.paragraphs.map((p, pi) => (
              <textarea key={pi} value={p} onChange={(e) => update(i, { paragraphs: s.paragraphs.map((x, xi) => (xi === pi ? e.target.value : x)) })} data-testid={`section-para-${i}-${pi}`} rows={2} className="w-full border border-[#ecdfce] rounded-md px-2 py-1 text-sm bg-white mt-1" />
            ))}
            <div className="flex items-center justify-between mt-1.5">
              <button onClick={() => update(i, { paragraphs: [...s.paragraphs, ""] })} className="text-xs text-[#EA4E1B] font-semibold inline-flex items-center gap-1"><Plus className="w-3 h-3" /> Paragrafo</button>
              <span className="text-[11px] text-[#9c8b7d]">conf. {(s.confidence ?? 0).toFixed(2)} {s.source_segment_ids?.length ? `· ${s.source_segment_ids.join(", ")}` : "· nessun segmento"}{(s.confidence ?? 1) < 0.7 ? " ⚠️" : ""}</span>
            </div>
          </div>
        );
      })}
      <button onClick={add} data-testid="section-add-btn" className="text-sm font-semibold border border-dashed border-[#ecdfce] rounded-lg px-3 py-2 w-full hover:border-[#EA4E1B] inline-flex items-center justify-center gap-1.5"><Plus className="w-4 h-4" /> Aggiungi sezione</button>
    </div>
  );
}

function PreviewPanel({ slug, onClose, onPublished }) {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState("load");
  const [err, setErr] = useState("");
  const [editing, setEditing] = useState(false);
  const [sections, setSections] = useState([]);

  const load = async () => {
    setBusy("load"); setErr("");
    try { const d = await api.transcriptSeoPreview(slug); setData(d); setSections((d.preview?.summary_sections) || []); }
    catch (e) { setErr(e.message); }
    finally { setBusy(""); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [slug]);

  const regen = async () => { setBusy("gen"); setErr(""); try { await api.transcriptSeoGenerate(slug); await load(); setEditing(false); } catch (e) { setErr(e.message); setBusy(""); } };
  const saveSections = async () => { setBusy("save"); setErr(""); try { const r = await api.transcriptSeoSaveSections(slug, sections); setSections(r.summary_sections); setEditing(false); await load(); } catch (e) { setErr(e.message); setBusy(""); } };
  const publish = async () => { setBusy("pub"); setErr(""); try { await api.transcriptSeoPublish(slug); onPublished(); onClose(); } catch (e) { setErr(e.message); setBusy(""); } };

  const p = data?.preview;
  const meta = p?.meta || {};
  const sectionErrors = (() => {
    const errs = [];
    const heads = sections.map((s) => (s.heading || "").trim().toLowerCase());
    sections.forEach((s, i) => {
      if (!(s.heading || "").trim()) errs.push(`Sezione ${i + 1}: titolo vuoto`);
      if (heads.indexOf(heads[i]) !== i && heads[i]) errs.push(`Sezione ${i + 1}: titolo duplicato`);
      if (i === 0 && s.level === 3) errs.push("La prima sezione non può essere H3");
      if (!(s.paragraphs || []).some((x) => (x || "").trim())) errs.push(`Sezione ${i + 1}: nessun paragrafo`);
    });
    return [...new Set(errs)];
  })();
  const hasErrors = editing && sectionErrors.length > 0;
  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-start justify-center overflow-y-auto py-8 px-4" data-testid="seo-preview-modal">
      <div className="bg-white rounded-2xl w-full max-w-3xl shadow-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#efe4d6] sticky top-0 bg-white rounded-t-2xl z-10">
          <h3 className="font-anton text-xl text-[#1a1411]">Anteprima SEO</h3>
          <div className="flex items-center gap-2">
            <button onClick={regen} disabled={!!busy} data-testid="seo-regen-btn" className="inline-flex items-center gap-1.5 text-sm font-semibold border border-[#ecdfce] rounded-lg px-3 py-1.5 hover:border-[#EA4E1B] disabled:opacity-50">
              {busy === "gen" ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />} Rigenera
            </button>
            <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-[#fbf7f2]" data-testid="seo-close-btn"><X className="w-5 h-5" /></button>
          </div>
        </div>

        <div className="px-6 py-5">
          {busy === "load" && <div className="flex items-center gap-2 text-[#6b5d52]"><Loader2 className="w-5 h-5 animate-spin" /> Carico…</div>}
          {err && <p className="text-red-600 text-sm mb-3">{err}</p>}
          {!busy && !p && !err && (
            <div className="text-center py-8">
              <p className="text-[#6b5d52] mb-4">Nessuna anteprima ancora generata.</p>
              <button onClick={regen} disabled={!!busy} data-testid="seo-generate-first-btn" className="inline-flex items-center gap-2 bg-[#EA4E1B] hover:bg-[#d3430f] text-white font-bold uppercase tracking-wide text-sm px-5 py-3 rounded-full disabled:opacity-50">
                {busy === "gen" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />} Genera anteprima
              </button>
            </div>
          )}

          {p && (
            <div data-testid="seo-preview-content">
              <div className="flex flex-wrap items-center gap-2 mb-3 text-xs">
                <span className="bg-[#fbf7f2] border border-[#ecdfce] rounded-full px-3 py-1">Modello: <b>{meta.model}</b></span>
                {meta.fallback_used && <span className="bg-amber-100 text-amber-700 rounded-full px-3 py-1">Fallback</span>}
                <span className="bg-[#fbf7f2] border border-[#ecdfce] rounded-full px-3 py-1">~${meta.cost_estimate}</span>
                <span className="bg-[#fbf7f2] border border-[#ecdfce] rounded-full px-3 py-1">intro {meta.intro_words}p</span>
                <span className="bg-[#fbf7f2] border border-[#ecdfce] rounded-full px-3 py-1">sommario {meta.summary_words}p</span>
                <span className="bg-[#fbf7f2] border border-[#ecdfce] rounded-full px-3 py-1">{meta.n_sections} sez · {meta.n_h2} H2</span>
                <span className="bg-[#fbf7f2] border border-[#ecdfce] rounded-full px-3 py-1">{meta.n_chapters} cap · {meta.n_quotes} cit</span>
                {meta.needs_review && <span className="inline-flex items-center gap-1 bg-red-100 text-red-700 rounded-full px-3 py-1"><AlertTriangle className="w-3.5 h-3.5" /> Da verificare</span>}
              </div>
              {meta.needs_review && (meta.review_reasons || []).length > 0 && (
                <ul className="text-xs text-red-600 mb-3 list-disc pl-5">{meta.review_reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
              )}

              <Field label="Tipo / Ospite">{p.type}{p.guest_name ? ` · ${p.guest_name}` : ""}</Field>
              <Field label="H1">{p.h1}</Field>
              <Field label={`SEO title (${(p.seo_title || "").length})`}>{p.seo_title}</Field>
              <Field label={`Meta description (${(p.meta_description || "").length})`}>{p.meta_description}</Field>
              <Field label="Introduzione">{p.excerpt}</Field>

              <div className="flex items-center justify-between mt-4 mb-1">
                <p className="text-[11px] font-bold uppercase tracking-wide text-[#9c8b7d]">Sommario strutturato (H2/H3)</p>
                {!editing ? (
                  <button onClick={() => setEditing(true)} data-testid="seo-edit-sections-btn" className="text-xs font-semibold text-[#EA4E1B] inline-flex items-center gap-1"><Pencil className="w-3.5 h-3.5" /> Modifica</button>
                ) : (
                  <button onClick={saveSections} disabled={!!busy || hasErrors} data-testid="seo-save-sections-btn" className="text-xs font-bold text-white bg-green-600 hover:bg-green-700 rounded-lg px-3 py-1.5 inline-flex items-center gap-1 disabled:opacity-50" title={hasErrors ? "Correggi gli errori di struttura prima di salvare" : ""}>{busy === "save" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />} Salva sezioni</button>
                )}
              </div>

              {hasErrors && (
                <ul className="text-xs text-red-600 mb-2 list-disc pl-5" data-testid="section-errors">{sectionErrors.map((e, i) => <li key={i}>{e}</li>)}</ul>
              )}

              {editing ? (
                <SectionEditor sections={sections} setSections={setSections} />
              ) : (
                <div className="border border-[#efe4d6] rounded-xl p-4">
                  {(p.summary_sections || []).map((s, i) => (
                    <div key={i} className={s.level === 3 ? "ml-4" : ""}>
                      <p className={`mt-3 ${s.level === 3 ? "text-base font-bold" : "text-lg font-extrabold"} text-[#1a1411]`}>{s.level === 3 ? "↳ " : ""}{s.heading}{(s.confidence ?? 1) < 0.7 ? <span className="text-amber-600 text-xs ml-1">(bassa conf.)</span> : null}</p>
                      {(s.paragraphs || []).map((para, pi) => <p key={pi} className="text-sm text-[#4a3d34] mt-1 leading-relaxed">{para}</p>)}
                    </div>
                  ))}
                  {(!p.summary_sections || p.summary_sections.length === 0) && <p className="text-sm text-[#9c8b7d]">Nessuna sezione.</p>}
                </div>
              )}

              <div className="mt-4">
                <Field label="Entità (persone · squadre · competizioni)">
                  <div className="text-xs text-[#6b5d52] space-y-1">
                    <div><b>Persone:</b> {(p.entities?.people || []).join(", ") || "—"}</div>
                    <div><b>Squadre:</b> {(p.entities?.teams || []).join(", ") || "—"}</div>
                    <div><b>Competizioni:</b> {(p.entities?.competitions || []).join(", ") || "—"}</div>
                  </div>
                </Field>
              </div>

              <Field label="Capitoli (timestamp reali)">
                <div className="border border-[#efe4d6] rounded-xl divide-y divide-[#efe4d6]">
                  {(p.chapters || []).map((c, i) => (
                    <div key={i} className="flex items-start gap-3 px-3 py-2">
                      <span className="text-[#EA4E1B] font-bold tabular-nums min-w-[52px] inline-flex items-center gap-1"><Clock className="w-3.5 h-3.5" />{c.time}</span>
                      <span><b>{c.label}</b>{c.description ? <span className="block text-xs text-[#6b5d52]">{c.description}</span> : null}</span>
                    </div>
                  ))}
                  {(!p.chapters || p.chapters.length === 0) && <p className="text-sm text-[#9c8b7d] px-3 py-2">Nessun capitolo.</p>}
                </div>
              </Field>

              {(p.quotes || []).length > 0 && (
                <Field label="Citazioni verificate">
                  {(p.quotes || []).map((q, i) => (
                    <blockquote key={i} className="border-l-2 border-[#EA4E1B] pl-3 py-1 italic text-[#4a3d34] mb-2 text-sm">
                      <Quote className="w-3 h-3 inline mr-1 text-[#EA4E1B]" />{q.text}{q.time ? <span className="not-italic text-xs text-[#9c8b7d]"> [{q.time}]</span> : null}{q.speaker ? <span className="not-italic text-xs text-[#9c8b7d]"> — {q.speaker}</span> : null}
                    </blockquote>
                  ))}
                </Field>
              )}
            </div>
          )}
        </div>

        {p && (
          <div className="px-6 py-4 border-t border-[#efe4d6] flex items-center justify-end gap-2 sticky bottom-0 bg-white rounded-b-2xl">
            <button onClick={onClose} className="text-sm font-semibold px-4 py-2 rounded-lg hover:bg-[#fbf7f2]">Chiudi</button>
            <button onClick={publish} disabled={!!busy || editing} data-testid="seo-publish-btn" title={editing ? "Salva prima le sezioni" : ""} className="inline-flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white font-bold uppercase tracking-wide text-sm px-5 py-2.5 rounded-full disabled:opacity-50">
              {busy === "pub" ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />} Pubblica anteprima
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function TranscriptSEO() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [openSlug, setOpenSlug] = useState(null);
  const [msg, setMsg] = useState("");

  const load = async () => {
    setLoading(true);
    try { const r = await api.transcriptSeoStatus(); setItems(r.episodes || []); setMsg(""); }
    catch (e) { setMsg(`Errore nel caricamento: ${e.message}`); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const generate = async (slug) => {
    setBusy(slug); setMsg("");
    try { await api.transcriptSeoGenerate(slug); setMsg("Anteprima generata."); await load(); setOpenSlug(slug); }
    catch (e) { setMsg(e.message); } finally { setBusy(""); }
  };
  const batch = async () => {
    setBusy("batch"); setMsg("");
    try { const r = await api.transcriptSeoBatch({ only_missing: true, limit: 15 }); setMsg(`Batch: ${r.succeeded} ok, ${r.failed} falliti.`); await load(); }
    catch (e) { setMsg(e.message); } finally { setBusy(""); }
  };

  return (
    <div data-testid="transcript-seo-page">
      <div className="flex items-center justify-between flex-wrap gap-3 mb-6">
        <div>
          <h1 className="font-anton text-3xl text-[#1a1411] flex items-center gap-2"><FileText className="w-7 h-7 text-[#EA4E1B]" /> Trascrizioni · SEO</h1>
          <p className="text-[#6b5d52] text-sm mt-1">Genera contenuti SEO (sommario H2/H3, capitoli, entità, citazioni) dai sottotitoli reali. Anteprima e modifica prima di pubblicare.</p>
        </div>
        <button onClick={batch} disabled={!!busy} data-testid="seo-batch-btn" className="inline-flex items-center gap-2 bg-[#1a1411] hover:bg-[#EA4E1B] text-white font-bold uppercase tracking-wide text-sm px-5 py-3 rounded-full disabled:opacity-50">
          {busy === "batch" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />} Genera anteprime mancanti
        </button>
      </div>

      {msg && <div data-testid="seo-msg" className="mb-4 text-sm bg-[#fbf7f2] border border-[#ecdfce] rounded-lg px-3 py-2 text-[#4a3d34]">{msg}</div>}

      {loading ? (
        <div className="flex items-center gap-2 text-[#6b5d52]"><Loader2 className="w-5 h-5 animate-spin" /> Carico…</div>
      ) : (
        <div className="bg-white border border-[#ecdfce] rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-[#fbf7f2] text-[#9c8b7d] text-xs uppercase tracking-wide">
              <tr>
                <th className="text-left px-5 py-3 font-bold">Contenuto</th>
                <th className="text-left px-5 py-3 font-bold">Tipo</th>
                <th className="text-left px-5 py-3 font-bold">Stato SEO</th>
                <th className="text-right px-5 py-3 font-bold">Azioni</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#efe4d6]">
              {items.map((e) => {
                const badge = STATUS_BADGE[e.seo_status] || STATUS_BADGE.none;
                return (
                  <tr key={e.slug} data-testid={`seo-row-${e.slug}`} className="hover:bg-[#fbf7f2]/60">
                    <td className="px-5 py-3 text-[#1a1411] font-semibold max-w-md">{e.title}</td>
                    <td className="px-5 py-3 text-[#6b5d52] capitalize">{e.type}</td>
                    <td className="px-5 py-3">
                      <span className={`text-[11px] font-bold uppercase px-2.5 py-1 rounded-full ${badge.cls}`}>{badge.label}</span>
                      {e.seo_status !== "published" && e.quality_status === "approved_short" && <span className="ml-1.5 inline-flex items-center text-[11px] font-bold text-emerald-700" title="Sotto target ma copertura completa (no padding)">✓ corto</span>}
                      {e.seo_status !== "published" && e.quality_status === "approved" && <span className="ml-1.5 inline-flex items-center text-[11px] font-bold text-emerald-700">✓ ok</span>}
                      {e.seo_status !== "published" && (e.quality_status === "needs_review" || (e.needs_review && !e.quality_status)) && <span className="ml-1.5 inline-flex items-center gap-0.5 text-[11px] font-bold text-red-700"><AlertTriangle className="w-3 h-3" /> rev</span>}
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center justify-end gap-2">
                        {e.has_preview ? (
                          <button onClick={() => setOpenSlug(e.slug)} data-testid={`seo-view-${e.slug}`} className="inline-flex items-center gap-1.5 text-sm font-semibold border border-[#ecdfce] rounded-lg px-3 py-1.5 hover:border-[#EA4E1B]"><Eye className="w-4 h-4" /> Anteprima</button>
                        ) : (
                          <button onClick={() => generate(e.slug)} disabled={busy === e.slug} data-testid={`seo-gen-${e.slug}`} className="inline-flex items-center gap-1.5 text-sm font-semibold bg-[#EA4E1B] hover:bg-[#d3430f] text-white rounded-lg px-3 py-1.5 disabled:opacity-50">
                            {busy === e.slug ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />} Genera
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {items.length === 0 && <tr><td colSpan={4} className="px-5 py-8 text-center text-[#9c8b7d]">Nessun contenuto con trascrizione disponibile.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {openSlug && <PreviewPanel slug={openSlug} onClose={() => setOpenSlug(null)} onPublished={load} />}
    </div>
  );
}
