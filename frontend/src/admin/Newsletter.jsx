import React, { useEffect, useState } from "react";
import {
  Mail, Loader2, Save, CheckCircle2, XCircle, Send, Eye, Download, Trash2, Users, AlertTriangle, TestTube2,
} from "lucide-react";
import { api, getToken } from "./api";

const inputCls = "w-full rounded-lg border border-[#e5d8c7] bg-[#fbf7f2] px-3 py-2.5 text-sm text-[#1a1411] focus:outline-none focus:ring-2 focus:ring-[#EA4E1B]/40 focus:border-[#EA4E1B]";

function Card({ title, icon: Icon, children, testid }) {
  return (
    <div className="mt-6 bg-white rounded-xl border border-[#ecdfce] p-5" data-testid={testid}>
      <div className="flex items-center gap-2 mb-3">
        {Icon && <Icon className="w-5 h-5 text-[#EA4E1B]" />}
        <h2 className="font-archivo font-extrabold text-[#1a1411]">{title}</h2>
      </div>
      {children}
    </div>
  );
}

function Toggle({ checked, onChange, label, hint, testid }) {
  return (
    <label className="flex items-start gap-3 cursor-pointer py-1.5">
      <button type="button" role="switch" aria-checked={checked} onClick={() => onChange(!checked)} data-testid={testid}
        className={`mt-0.5 relative w-11 h-6 rounded-full transition-colors shrink-0 ${checked ? "bg-[#EA4E1B]" : "bg-[#d9cdbe]"}`}>
        <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${checked ? "translate-x-5" : ""}`} />
      </button>
      <span><span className="block text-sm font-semibold text-[#1a1411]">{label}</span>
        {hint && <span className="block text-xs text-[#8a7a6c]">{hint}</span>}</span>
    </label>
  );
}

export default function Newsletter() {
  const [cfg, setCfg] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState("");
  const [episodes, setEpisodes] = useState([]);
  const [subs, setSubs] = useState([]);

  const [kind, setKind] = useState("episode");
  const [epSlug, setEpSlug] = useState("");
  const [liveText, setLiveText] = useState("");
  const [gSubject, setGSubject] = useState("");
  const [gHtml, setGHtml] = useState("");
  const [preview, setPreview] = useState(null);

  const load = async () => setCfg(await api.nlConfig());
  const loadLists = async () => {
    try { setEpisodes(await api.episodes()); } catch { /* */ }
    try { setSubs(await api.nlSubscribers()); } catch { /* */ }
  };
  useEffect(() => { load().catch(() => {}); loadLists(); }, []); // eslint-disable-line

  const set = (k, v) => setCfg((c) => ({ ...c, [k]: v }));
  const setTpl = (grp, k, v) => setCfg((c) => ({ ...c, templates: { ...c.templates, [grp]: { ...c.templates[grp], [k]: v } } }));

  const save = async () => {
    setSaving(true); setSaved(false);
    try {
      const c = await api.nlSaveConfig({
        sender_email: cfg.sender_email, from_name: cfg.from_name, owner_email: cfg.owner_email,
        enabled: cfg.enabled, auto_episode: cfg.auto_episode, templates: cfg.templates,
      });
      setCfg(c); setSaved(true); setTimeout(() => setSaved(false), 2500);
    } catch (e) { alert(e.message); }
    setSaving(false);
  };

  const payload = () => ({ kind, slug: epSlug, text: liveText, subject: gSubject, html: gHtml });

  const doPreview = async () => {
    setPreview(null);
    try { setPreview(await api.nlPreview(payload())); } catch (e) { setPreview({ ok: false, error: e.message }); }
  };
  const sendTest = async () => {
    setBusy("test");
    try { const r = await api.nlTest(payload()); alert(r.ok ? "Email di test inviata a " + (cfg.owner_email || "te") : "Errore: " + (r.error || "")); }
    catch (e) { alert(e.message); }
    setBusy("");
  };
  const sendCampaign = async () => {
    if (!window.confirm(`Inviare la newsletter a ${cfg.subscribers_active} iscritti attivi?`)) return;
    setBusy("send");
    try { const r = await api.nlSend(payload()); alert(r.ok || r.sent ? `Inviata a ${r.sent}/${r.total} iscritti.` : "Errore: " + (r.error || "")); }
    catch (e) { alert(e.message); }
    setBusy("");
  };
  const delSub = async (s) => { if (window.confirm(`Rimuovere ${s.email}?`)) { await api.nlSubDelete(s.id); loadLists(); } };
  const exportCsv = async () => {
    const res = await fetch(`${api.base}/admin/newsletter/subscribers/export`, { headers: { Authorization: `Bearer ${getToken()}` } });
    const blob = await res.blob(); const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "iscritti-newsletter.csv"; a.click(); URL.revokeObjectURL(url);
  };

  if (!cfg) return <div className="flex items-center gap-2 text-[#6b5d52]"><Loader2 className="w-4 h-4 animate-spin" /> Caricamento…</div>;

  const st = cfg.status || {};

  return (
    <div data-testid="newsletter-admin">
      <h1 className="font-anton text-3xl text-[#1a1411]">Newsletter</h1>
      <p className="text-[#6b5d52] mt-1">Raccogli iscritti e invia email (via Resend) all'uscita di una nuova puntata o quando vai live.</p>

      {!cfg.api_key_set && (
        <div className="mt-4 rounded-xl border border-[#e6b8a3] bg-[#fdf1ec] p-4 text-sm text-[#7a3a20]" data-testid="nl-apikey-warning">
          <p className="font-bold flex items-center gap-2"><AlertTriangle className="w-4 h-4" /> RESEND_API_KEY non ancora configurata</p>
          <p className="mt-1">Le iscrizioni funzionano già e vengono salvate. L'INVIO delle email si attiva quando la chiave Resend è impostata nell'ambiente (e il dominio unoxdue.net è verificato su Resend).</p>
        </div>
      )}

      <Card title="Configurazione" icon={Mail} testid="nl-config-card">
        <div className="flex items-center gap-2 mb-3 text-sm">
          {cfg.api_key_set
            ? <span className="inline-flex items-center gap-1.5 text-green-700 font-semibold"><CheckCircle2 className="w-4 h-4" /> Resend collegato</span>
            : <span className="inline-flex items-center gap-1.5 text-[#c2410c] font-semibold"><XCircle className="w-4 h-4" /> Resend non configurato</span>}
        </div>
        <div className="grid md:grid-cols-3 gap-4 max-w-3xl">
          <div><label className="block text-sm font-semibold text-[#1a1411]">Nome mittente</label>
            <input value={cfg.from_name || ""} onChange={(e) => set("from_name", e.target.value)} className={inputCls + " mt-1.5"} data-testid="nl-fromname" /></div>
          <div><label className="block text-sm font-semibold text-[#1a1411]">Email mittente</label>
            <input value={cfg.sender_email || ""} onChange={(e) => set("sender_email", e.target.value)} className={inputCls + " mt-1.5"} data-testid="nl-sender" /></div>
          <div><label className="block text-sm font-semibold text-[#1a1411]">Email notifiche (tue)</label>
            <input value={cfg.owner_email || ""} onChange={(e) => set("owner_email", e.target.value)} className={inputCls + " mt-1.5"} data-testid="nl-owner" /></div>
        </div>
        <div className="mt-4">
          <Toggle checked={!!cfg.enabled} onChange={(v) => set("enabled", v)} testid="nl-enabled-toggle" label="Invio attivo" hint="Interruttore generale per gli invii automatici." />
          <Toggle checked={!!cfg.auto_episode} onChange={(v) => set("auto_episode", v)} testid="nl-auto-episode-toggle" label="Auto: invia all'uscita di una nuova puntata" hint="Manda la newsletter agli iscritti quando un episodio viene pubblicato (una volta per contenuto)." />
        </div>
        <button onClick={save} disabled={saving} data-testid="nl-save-button" className="mt-4 inline-flex items-center gap-2 bg-[#14100e] hover:bg-[#EA4E1B] text-white text-sm font-bold uppercase tracking-wide px-5 py-2.5 rounded-lg disabled:opacity-60 transition-colors">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Salva
        </button>
        {saved && <span className="ml-3 inline-flex items-center gap-1.5 text-sm font-semibold text-green-700"><CheckCircle2 className="w-4 h-4" /> Salvato</span>}
      </Card>

      <Card title="Modelli email" icon={Mail} testid="nl-templates-card">
        {[["episode", "Nuova puntata"], ["live", "Avviso live"]].map(([grp, lbl]) => (
          <div key={grp} className="mb-4">
            <p className="text-sm font-semibold text-[#1a1411] mb-1.5">{lbl}</p>
            <input value={cfg.templates[grp]?.subject || ""} onChange={(e) => setTpl(grp, "subject", e.target.value)} placeholder="Oggetto" data-testid={`nl-tpl-${grp}-subject`} className={inputCls + " mb-2"} />
            <textarea value={cfg.templates[grp]?.intro || ""} onChange={(e) => setTpl(grp, "intro", e.target.value)} rows={2} placeholder="Testo introduttivo" data-testid={`nl-tpl-${grp}-intro`} className={inputCls} />
            {grp === "episode" && <p className="text-xs text-[#8a7a6c] mt-1">Nell'oggetto puoi usare <code className="bg-[#fbf7f2] px-1 rounded">{"{title}"}</code>. Titolo, copertina e link vengono aggiunti in automatico.</p>}
          </div>
        ))}
        <button onClick={save} disabled={saving} className="inline-flex items-center gap-2 bg-[#14100e] hover:bg-[#EA4E1B] text-white text-sm font-bold uppercase tracking-wide px-5 py-2.5 rounded-lg disabled:opacity-60 transition-colors">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Salva modelli
        </button>
      </Card>

      <Card title="Invia una email" icon={Send} testid="nl-send-card">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <select value={kind} onChange={(e) => setKind(e.target.value)} data-testid="nl-kind-select" className="rounded-lg border border-[#e5d8c7] bg-[#fbf7f2] px-3 py-2 text-sm">
            <option value="episode">Nuova puntata</option>
            <option value="live">Avviso live</option>
            <option value="generic">Email libera</option>
          </select>
          {kind === "episode" && (
            <select value={epSlug} onChange={(e) => setEpSlug(e.target.value)} data-testid="nl-episode-select" className="rounded-lg border border-[#e5d8c7] bg-[#fbf7f2] px-3 py-2 text-sm min-w-[260px]">
              <option value="">Scegli un contenuto…</option>
              {episodes.map((e) => <option key={e.slug} value={e.slug}>{e.type === "intervista" ? "🎤 " : "🎙️ "}{e.title}</option>)}
            </select>
          )}
        </div>
        {kind === "live" && <textarea value={liveText} onChange={(e) => setLiveText(e.target.value)} rows={2} placeholder="Testo (lascia vuoto per il default)" data-testid="nl-live-text" className={inputCls + " mb-3 max-w-xl"} />}
        {kind === "generic" && (
          <div className="max-w-xl mb-3 space-y-2">
            <input value={gSubject} onChange={(e) => setGSubject(e.target.value)} placeholder="Oggetto" data-testid="nl-generic-subject" className={inputCls} />
            <textarea value={gHtml} onChange={(e) => setGHtml(e.target.value)} rows={5} placeholder="Contenuto HTML (es. <p>Ciao...</p>)" data-testid="nl-generic-html" className={inputCls} />
          </div>
        )}
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={doPreview} data-testid="nl-preview-button" className="inline-flex items-center gap-1.5 border border-[#e5d8c7] hover:border-[#EA4E1B] text-sm font-semibold px-3 py-2 rounded-lg"><Eye className="w-4 h-4" /> Anteprima</button>
          <button onClick={sendTest} disabled={busy === "test"} data-testid="nl-test-button" className="inline-flex items-center gap-1.5 border border-[#e5d8c7] hover:border-[#EA4E1B] text-sm font-semibold px-3 py-2 rounded-lg disabled:opacity-50">
            {busy === "test" ? <Loader2 className="w-4 h-4 animate-spin" /> : <TestTube2 className="w-4 h-4" />} Invia test a te
          </button>
          <button onClick={sendCampaign} disabled={busy === "send"} data-testid="nl-send-button" className="inline-flex items-center gap-1.5 bg-[#EA4E1B] hover:bg-[#d3430f] text-white text-sm font-bold px-4 py-2 rounded-lg disabled:opacity-50">
            {busy === "send" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Invia a tutti ({cfg.subscribers_active})
          </button>
        </div>
        {preview && (preview.ok
          ? <div className="mt-4 border border-[#ecdfce] rounded-lg overflow-hidden max-w-xl" data-testid="nl-preview-box">
              <div className="bg-[#fbf7f2] px-3 py-2 text-sm font-semibold border-b border-[#ecdfce]">Oggetto: {preview.subject}</div>
              <iframe title="anteprima" srcDoc={preview.html} className="w-full h-96 bg-white" />
            </div>
          : <p className="mt-3 text-sm text-red-600" data-testid="nl-preview-error">{preview.error}</p>)}
      </Card>

      <Card title={`Iscritti · ${cfg.subscribers_active} attivi / ${cfg.subscribers_total} totali`} icon={Users} testid="nl-subs-card">
        <button onClick={exportCsv} data-testid="nl-export-button" className="mb-3 inline-flex items-center gap-1.5 border border-[#e5d8c7] hover:border-[#EA4E1B] text-sm font-semibold px-3 py-2 rounded-lg"><Download className="w-4 h-4" /> Esporta CSV</button>
        {subs.length === 0 ? <p className="text-sm text-[#8a7a6c]">Nessun iscritto ancora.</p> : (
          <div className="divide-y divide-[#f0e7da] max-h-96 overflow-auto">
            {subs.map((s) => (
              <div key={s.id} className="flex items-center justify-between py-2 text-sm">
                <div>
                  <span className={s.status === "active" ? "text-[#1a1411]" : "text-[#a89a8c] line-through"}>{s.email}</span>
                  <span className="text-xs text-[#a89a8c] ml-2">{s.source} · {new Date(s.created_at).toLocaleDateString("it-IT")}{s.status !== "active" ? " · disiscritto" : ""}</span>
                </div>
                <button onClick={() => delSub(s)} className="text-red-500 p-1"><Trash2 className="w-4 h-4" /></button>
              </div>
            ))}
          </div>
        )}
        {st.at && <p className="mt-3 text-xs text-[#8a7a6c]">Ultimo invio: "{st.subject}" → {st.sent}/{st.total} · {new Date(st.at).toLocaleString("it-IT")}{st.errors && st.errors.length ? " · errori: " + st.errors.join("; ") : ""}</p>}
      </Card>
    </div>
  );
}
