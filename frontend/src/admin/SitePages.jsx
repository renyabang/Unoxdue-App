import React, { useEffect, useState } from "react";
import { FileText, Loader2, Save, Plus, Trash2, RotateCcw } from "lucide-react";
import { api } from "./api";

const ICONS = [
  { v: "radio", l: "Radio (dirette)" },
  { v: "clapperboard", l: "Clapperboard (video)" },
  { v: "target", l: "Target (pronostici)" },
  { v: "users", l: "Users (team)" },
  { v: "mic", l: "Microfono (interviste)" },
];

const TA = "w-full border border-[#ecdfce] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#EA4E1B]";

function ListBlock({ title, items, render, onAdd, onDel, testid }) {
  return (
    <section className="bg-white rounded-xl border border-[#ecdfce] p-5" data-testid={testid}>
      <div className="flex items-center justify-between mb-2">
        <h2 className="font-archivo font-extrabold text-[#1a1411]">{title}</h2>
        <button onClick={onAdd} className="inline-flex items-center gap-1 text-sm text-[#EA4E1B] font-semibold"><Plus className="w-4 h-4" /> Aggiungi</button>
      </div>
      {items.map((v, i) => (
        <div key={i} className="flex gap-2 mb-2 items-start">
          <div className="flex-1">{render(v, i)}</div>
          <button onClick={() => onDel(i)} className="text-red-500 mt-2" aria-label="Rimuovi"><Trash2 className="w-4 h-4" /></button>
        </div>
      ))}
    </section>
  );
}

export default function SitePages() {
  const [content, setContent] = useState(null);
  const [defaults, setDefaults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.ilPodcastContent();
      setDefaults(r.defaults);
      const stored = r.content || {};
      const eff = { ...r.defaults };
      Object.keys(r.defaults).forEach((k) => { if (stored[k]) eff[k] = stored[k]; });
      setContent(eff);
    } catch (e) { setMsg("Errore caricamento: " + e.message); }
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const save = async () => {
    setSaving(true); setMsg("");
    try { await api.saveIlPodcastContent(content); setMsg("Contenuti salvati. La pagina /il-podcast/ è aggiornata."); }
    catch (e) { setMsg("Errore salvataggio: " + e.message); }
    finally { setSaving(false); }
  };
  const resetDefaults = () => {
    if (!window.confirm("Ripristinare i testi predefiniti? Le modifiche non salvate andranno perse.")) return;
    setContent(JSON.parse(JSON.stringify(defaults)));
  };

  if (loading || !content) return <p className="text-[#9c8b7d]" data-testid="sitepages-loading">Caricamento...</p>;

  const upd = (k, v) => setContent((c) => ({ ...c, [k]: v }));
  const updList = (k, i, v) => setContent((c) => ({ ...c, [k]: c[k].map((x, j) => (j === i ? v : x)) }));
  const addList = (k, v) => setContent((c) => ({ ...c, [k]: [...c[k], v] }));
  const delList = (k, i) => setContent((c) => ({ ...c, [k]: c[k].filter((_, j) => j !== i) }));

  return (
    <div data-testid="sitepages-page">
      <div className="flex items-center gap-2">
        <FileText className="w-6 h-6 text-[#EA4E1B]" />
        <h1 className="font-anton text-3xl text-[#1a1411]">Pagine — Il podcast</h1>
      </div>
      <p className="text-[#6b5d52] mt-1">Modifica i testi della pagina <code>/il-podcast/</code> (claim su dirette, cadenza, piattaforme, FAQ). Il design resta invariato.</p>

      <div className="mt-6 space-y-6 max-w-4xl">
        <section className="bg-white rounded-xl border border-[#ecdfce] p-5">
          <h2 className="font-archivo font-extrabold text-[#1a1411] mb-2">Introduzione (hero)</h2>
          <textarea rows={3} className={TA} value={content.hero_lead} onChange={(e) => upd("hero_lead", e.target.value)} data-testid="ilp-hero-lead" />
        </section>

        <ListBlock title="Paragrafi «Cos'è UnoXdue»" testid="ilp-about-block" items={content.about}
          render={(v, i) => <textarea rows={3} className={TA} value={v} onChange={(e) => updList("about", i, e.target.value)} data-testid={`ilp-about-${i}`} />}
          onAdd={() => addList("about", "")} onDel={(i) => delList("about", i)} />

        <ListBlock title="Paragrafi «Come è fatta una puntata»" testid="ilp-format-block" items={content.format_text}
          render={(v, i) => <textarea rows={3} className={TA} value={v} onChange={(e) => updList("format_text", i, e.target.value)} data-testid={`ilp-format-${i}`} />}
          onAdd={() => addList("format_text", "")} onDel={(i) => delList("format_text", i)} />

        <section className="bg-white rounded-xl border border-[#ecdfce] p-5" data-testid="ilp-features-block">
          <div className="flex items-center justify-between mb-2">
            <h2 className="font-archivo font-extrabold text-[#1a1411]">Caratteristiche (format)</h2>
            <button onClick={() => addList("features", { icon: "radio", title: "", text: "" })} className="inline-flex items-center gap-1 text-sm text-[#EA4E1B] font-semibold"><Plus className="w-4 h-4" /> Aggiungi</button>
          </div>
          {content.features.map((f, i) => (
            <div key={i} className="border border-[#f0e7da] rounded-lg p-3 mb-2" data-testid={`ilp-feature-${i}`}>
              <div className="flex gap-2 mb-2">
                <select value={f.icon} onChange={(e) => updList("features", i, { ...f, icon: e.target.value })} className="border border-[#ecdfce] rounded px-2 py-1 text-sm">
                  {ICONS.map((ic) => <option key={ic.v} value={ic.v}>{ic.l}</option>)}
                </select>
                <input value={f.title} onChange={(e) => updList("features", i, { ...f, title: e.target.value })} placeholder="Titolo" className="flex-1 border border-[#ecdfce] rounded px-2 py-1 text-sm" />
                <button onClick={() => delList("features", i)} className="text-red-500" aria-label="Rimuovi"><Trash2 className="w-4 h-4" /></button>
              </div>
              <textarea rows={2} className={TA} value={f.text} onChange={(e) => updList("features", i, { ...f, text: e.target.value })} placeholder="Testo" />
            </div>
          ))}
        </section>

        <section className="bg-white rounded-xl border border-[#ecdfce] p-5" data-testid="ilp-faqs-block">
          <div className="flex items-center justify-between mb-2">
            <h2 className="font-archivo font-extrabold text-[#1a1411]">FAQ (visibili e in JSON-LD)</h2>
            <button onClick={() => addList("faqs", { q: "", a: "" })} className="inline-flex items-center gap-1 text-sm text-[#EA4E1B] font-semibold"><Plus className="w-4 h-4" /> Aggiungi</button>
          </div>
          {content.faqs.map((f, i) => (
            <div key={i} className="border border-[#f0e7da] rounded-lg p-3 mb-2" data-testid={`ilp-faq-${i}`}>
              <div className="flex gap-2 mb-2">
                <input value={f.q} onChange={(e) => updList("faqs", i, { ...f, q: e.target.value })} placeholder="Domanda" className="flex-1 border border-[#ecdfce] rounded px-2 py-1 text-sm" />
                <button onClick={() => delList("faqs", i)} className="text-red-500" aria-label="Rimuovi"><Trash2 className="w-4 h-4" /></button>
              </div>
              <textarea rows={2} className={TA} value={f.a} onChange={(e) => updList("faqs", i, { ...f, a: e.target.value })} placeholder="Risposta" />
            </div>
          ))}
        </section>

        <div className="flex items-center gap-3 flex-wrap">
          <button onClick={save} disabled={saving} data-testid="ilp-save" className="inline-flex items-center gap-2 bg-[#EA4E1B] hover:bg-[#d3430f] text-white font-bold uppercase tracking-wide px-5 py-2.5 rounded-lg disabled:opacity-60">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Salva
          </button>
          <button onClick={resetDefaults} data-testid="ilp-reset" className="inline-flex items-center gap-2 border border-[#ecdfce] text-[#1a1411] font-bold px-4 py-2.5 rounded-lg"><RotateCcw className="w-4 h-4" /> Ripristina default</button>
          {msg && <span className="text-sm text-[#4a3d34]" data-testid="ilp-msg">{msg}</span>}
        </div>
      </div>
    </div>
  );
}
