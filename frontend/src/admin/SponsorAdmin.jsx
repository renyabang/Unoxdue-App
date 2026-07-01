import React, { useEffect, useState } from "react";
import {
  Handshake, Loader2, Save, CheckCircle2, Plus, Trash2, Mail, ExternalLink, Inbox, FileText,
} from "lucide-react";
import { api } from "./api";

function Tab({ active, onClick, children, testid, count }) {
  return (
    <button onClick={onClick} data-testid={testid}
      className={`px-4 py-2 rounded-lg text-sm font-bold transition-colors ${active ? "bg-[#14100e] text-white" : "bg-white border border-[#e5d8c7] text-[#4a3d34] hover:border-[#EA4E1B]"}`}>
      {children}{typeof count === "number" && <span className="ml-1.5 text-xs opacity-70">({count})</span>}
    </button>
  );
}

const inputCls = "w-full rounded-lg border border-[#e5d8c7] bg-[#fbf7f2] px-3 py-2.5 text-sm text-[#1a1411] focus:outline-none focus:ring-2 focus:ring-[#EA4E1B]/40 focus:border-[#EA4E1B]";

function ListEditor({ items, onChange, fields, addLabel, testid }) {
  const upd = (i, k, v) => onChange(items.map((it, j) => (j === i ? { ...it, [k]: v } : it)));
  const add = () => onChange([...items, Object.fromEntries(fields.map((f) => [f.key, ""]))]);
  const del = (i) => onChange(items.filter((_, j) => j !== i));
  return (
    <div data-testid={testid}>
      {items.map((it, i) => (
        <div key={i} className="flex gap-2 items-start mb-2">
          {fields.map((f) => (
            f.area ? (
              <textarea key={f.key} value={it[f.key] || ""} onChange={(e) => upd(i, f.key, e.target.value)} placeholder={f.ph} rows={2} className={inputCls + " flex-1"} />
            ) : (
              <input key={f.key} value={it[f.key] || ""} onChange={(e) => upd(i, f.key, e.target.value)} placeholder={f.ph} className={inputCls + (f.small ? " w-40" : " flex-1")} />
            )
          ))}
          <button onClick={() => del(i)} className="text-red-500 p-2 shrink-0"><Trash2 className="w-4 h-4" /></button>
        </div>
      ))}
      <button onClick={add} className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#EA4E1B] hover:underline"><Plus className="w-4 h-4" /> {addLabel}</button>
    </div>
  );
}

function StringListEditor({ items, onChange, addLabel, testid }) {
  const upd = (i, v) => onChange(items.map((it, j) => (j === i ? v : it)));
  const add = () => onChange([...items, ""]);
  const del = (i) => onChange(items.filter((_, j) => j !== i));
  return (
    <div data-testid={testid}>
      {items.map((it, i) => (
        <div key={i} className="flex gap-2 items-start mb-2">
          <textarea value={it || ""} onChange={(e) => upd(i, e.target.value)} rows={2} className={inputCls + " flex-1"} />
          <button onClick={() => del(i)} className="text-red-500 p-2 shrink-0"><Trash2 className="w-4 h-4" /></button>
        </div>
      ))}
      <button onClick={add} className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#EA4E1B] hover:underline"><Plus className="w-4 h-4" /> {addLabel}</button>
    </div>
  );
}

function ContentTab() {
  const [c, setC] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.sponsorContent().then((r) => {
      const d = r.defaults || {};
      const cur = r.content || {};
      setC({ ...d, ...cur, intro: cur.intro || d.intro, stats: cur.stats || d.stats, audience: cur.audience || d.audience });
    }).catch(() => {});
  }, []);

  const set = (k, v) => setC((x) => ({ ...x, [k]: v }));

  const save = async () => {
    setSaving(true); setSaved(false);
    try { await api.sponsorSaveContent(c); setSaved(true); setTimeout(() => setSaved(false), 2500); }
    catch (e) { alert(e.message); }
    setSaving(false);
  };

  if (!c) return <div className="flex items-center gap-2 text-[#6b5d52] mt-6"><Loader2 className="w-4 h-4 animate-spin" /> Caricamento…</div>;

  return (
    <div className="mt-6 max-w-3xl space-y-5" data-testid="sponsor-content-tab">
      <div>
        <label className="block text-sm font-semibold text-[#1a1411] mb-1.5">Email di contatto</label>
        <input value={c.contact_email || ""} onChange={(e) => set("contact_email", e.target.value)} className={inputCls} data-testid="sponsor-email-input" />
      </div>
      <div>
        <label className="block text-sm font-semibold text-[#1a1411] mb-1.5">Frase hero (sottotitolo)</label>
        <textarea value={c.hero_lead || ""} onChange={(e) => set("hero_lead", e.target.value)} rows={2} className={inputCls} />
      </div>
      <div>
        <label className="block text-sm font-semibold text-[#1a1411] mb-1.5">Paragrafi "Chi siamo"</label>
        <StringListEditor items={c.intro || []} onChange={(v) => set("intro", v)} addLabel="Aggiungi paragrafo" testid="sponsor-intro-editor" />
      </div>
      <div>
        <label className="block text-sm font-semibold text-[#1a1411] mb-1.5">Numeri / statistiche (numero + etichetta)</label>
        <p className="text-xs text-[#8a7a6c] mb-2">Consiglio: usa valori reali quando li hai (es. "55.000" + "Visualizzazioni YouTube"). Evita numeri gonfiati.</p>
        <ListEditor items={c.stats || []} onChange={(v) => set("stats", v)} addLabel="Aggiungi statistica" testid="sponsor-stats-editor"
          fields={[{ key: "num", small: true, ph: "Numero" }, { key: "label", ph: "Etichetta" }]} />
      </div>
      <div>
        <label className="block text-sm font-semibold text-[#1a1411] mb-1.5">Pubblico (titolo + descrizione)</label>
        <ListEditor items={c.audience || []} onChange={(v) => set("audience", v)} addLabel="Aggiungi voce" testid="sponsor-audience-editor"
          fields={[{ key: "title", ph: "Titolo" }, { key: "text", area: true, ph: "Descrizione" }]} />
      </div>
      <div className="flex items-center gap-3">
        <button onClick={save} disabled={saving} data-testid="sponsor-content-save" className="inline-flex items-center gap-2 bg-[#14100e] hover:bg-[#EA4E1B] text-white text-sm font-bold uppercase tracking-wide px-5 py-2.5 rounded-lg disabled:opacity-60 transition-colors">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Salva contenuti
        </button>
        {saved && <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-green-700"><CheckCircle2 className="w-4 h-4" /> Salvato</span>}
      </div>
      <p className="text-xs text-[#8a7a6c]">Pacchetti, formati e note legali sono fissi (già impostati come concordato). Chiedi pure per modificarli.</p>
    </div>
  );
}

const STATUS = { nuovo: { l: "Nuovo", c: "bg-[#EA4E1B] text-white" }, gestito: { l: "Gestito", c: "bg-green-600 text-white" }, archiviato: { l: "Archiviato", c: "bg-[#8a7a6c] text-white" } };

function LeadsTab({ onCount }) {
  const [leads, setLeads] = useState(null);
  const load = async () => { try { const l = await api.sponsorLeads(); setLeads(l); onCount(l.length); } catch { setLeads([]); } };
  useEffect(() => { load(); }, []); // eslint-disable-line

  const cycle = async (lead) => {
    const order = ["nuovo", "gestito", "archiviato"];
    const next = order[(order.indexOf(lead.status || "nuovo") + 1) % order.length];
    await api.sponsorLeadStatus(lead.id, next); load();
  };
  const del = async (lead) => { if (window.confirm("Eliminare questa richiesta?")) { await api.sponsorLeadDelete(lead.id); load(); } };

  if (!leads) return <div className="flex items-center gap-2 text-[#6b5d52] mt-6"><Loader2 className="w-4 h-4 animate-spin" /> Caricamento…</div>;
  if (leads.length === 0) return <div className="mt-6 text-center py-12 bg-white rounded-xl border border-[#ecdfce]" data-testid="sponsor-leads-empty"><Inbox className="w-10 h-10 mx-auto text-[#d9cdbe]" /><p className="mt-2 text-[#8a7a6c]">Nessuna richiesta ancora.</p></div>;

  return (
    <div className="mt-6 space-y-3" data-testid="sponsor-leads-tab">
      {leads.map((l) => {
        const st = STATUS[l.status] || STATUS.nuovo;
        return (
          <div key={l.id} className="bg-white rounded-xl border border-[#ecdfce] p-4" data-testid="sponsor-lead-row">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div>
                <p className="font-bold text-[#1a1411]">{l.company || "—"} <span className="font-normal text-[#6b5d52]">· {l.name}</span></p>
                <p className="text-sm text-[#6b5d52] flex items-center gap-3 mt-0.5 flex-wrap">
                  <a href={`mailto:${l.email}`} className="inline-flex items-center gap-1 text-[#EA4E1B] hover:underline"><Mail className="w-3.5 h-3.5" />{l.email}</a>
                  {l.phone && <span>{l.phone}</span>}
                  {l.budget && <span>💶 {l.budget}</span>}
                  {l.category && <span>🏷️ {l.category}</span>}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => cycle(l)} data-testid="sponsor-lead-status" className={`text-xs font-bold px-2.5 py-1 rounded-full ${st.c}`}>{st.l}</button>
                <button onClick={() => del(l)} className="text-red-500 p-1.5"><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>
            {l.message && <p className="text-sm text-[#4a3d34] mt-2 bg-[#fbf7f2] rounded-lg p-2.5">{l.message}</p>}
            <p className="text-xs text-[#a89a8c] mt-2">{new Date(l.created_at).toLocaleString("it-IT")}</p>
          </div>
        );
      })}
    </div>
  );
}

export default function SponsorAdmin() {
  const [tab, setTab] = useState("content");
  const [leadCount, setLeadCount] = useState(undefined);
  return (
    <div data-testid="sponsor-admin">
      <div className="flex items-center gap-2 mb-1">
        <Handshake className="w-6 h-6 text-[#EA4E1B]" />
        <h1 className="font-anton text-3xl text-[#1a1411]">Collabora / Sponsor</h1>
      </div>
      <p className="text-[#6b5d52] mb-4">Gestisci la pagina B2B (/collaborazioni) e le richieste dei brand.
        <a href="/collaborazioni/" target="_blank" rel="noopener" className="inline-flex items-center gap-1 text-[#EA4E1B] hover:underline ml-2" data-testid="sponsor-view-page">Vedi pagina <ExternalLink className="w-3.5 h-3.5" /></a>
        <a href="/api/sponsor/media-kit.pdf" target="_blank" rel="noopener" className="inline-flex items-center gap-1 text-[#EA4E1B] hover:underline ml-3"><FileText className="w-3.5 h-3.5" /> Media kit</a>
      </p>
      <div className="flex gap-2">
        <Tab active={tab === "content"} onClick={() => setTab("content")} testid="sponsor-tab-content">Contenuti pagina</Tab>
        <Tab active={tab === "leads"} onClick={() => setTab("leads")} testid="sponsor-tab-leads" count={leadCount}>Richieste</Tab>
      </div>
      {tab === "content" ? <ContentTab /> : <LeadsTab onCount={setLeadCount} />}
    </div>
  );
}
