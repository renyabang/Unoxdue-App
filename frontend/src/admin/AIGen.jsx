import React, { useEffect, useState } from "react";
import { Sparkles, Loader2, Save, Wand2, Info } from "lucide-react";
import { api } from "./api";

function Toggle({ checked, onChange, disabled, testid }) {
  return (
    <button type="button" role="switch" aria-checked={checked} disabled={disabled} data-testid={testid}
      onClick={() => !disabled && onChange(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${disabled ? "opacity-40 cursor-not-allowed" : ""}`}
      style={{ backgroundColor: checked ? "#EA4E1B" : "#d9cbba" }}>
      <span className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${checked ? "translate-x-5" : "translate-x-0.5"}`} />
    </button>
  );
}

function Row({ label, hint, children }) {
  return (
    <div className="flex items-center justify-between gap-4 py-3 border-b border-[#f0e7da] last:border-0">
      <div>
        <p className="text-[#1a1411] font-medium text-sm">{label}</p>
        {hint && <p className="text-[#9c8b7d] text-xs mt-0.5">{hint}</p>}
      </div>
      {children}
    </div>
  );
}

export default function AIGen() {
  const [s, setS] = useState(null);
  const [usage, setUsage] = useState({ daily: 0, monthly: 0 });
  const [saving, setSaving] = useState(false);
  const [batchBusy, setBatchBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const load = async () => {
    try {
      const r = await api.aiSettings();
      setS(r.settings); setUsage(r.usage || { daily: 0, monthly: 0 });
    } catch (e) { setMsg("Errore caricamento: " + e.message); }
  };
  useEffect(() => { load(); }, []);

  const setField = (k, v) => setS((p) => ({ ...p, [k]: v }));
  const setComp = (k, v) => setS((p) => ({ ...p, components: { ...p.components, [k]: v } }));

  const save = async () => {
    setSaving(true); setMsg("");
    try {
      const r = await api.updateAiSettings(s);
      setS(r.settings); setMsg("Impostazioni AI salvate.");
    } catch (e) { setMsg("Errore salvataggio: " + e.message); }
    finally { setSaving(false); }
  };

  const batch = async () => {
    setBatchBusy(true); setMsg("");
    try {
      const r = await api.aiProcessBatch({ only_missing: true, limit: 15 });
      setMsg(`Batch AI: ${r.succeeded} ok, ${r.failed} falliti su ${r.processed}. ${r.remaining_hint || ""}`);
      await load();
    } catch (e) { setMsg("Errore batch: " + e.message); }
    finally { setBatchBusy(false); }
  };

  if (!s) return <div className="text-[#9c8b7d]">Caricamento...</div>;

  return (
    <div data-testid="ai-page" className="max-w-3xl">
      <div className="flex items-center gap-2">
        <Sparkles className="w-6 h-6 text-[#EA4E1B]" />
        <h1 className="font-anton text-3xl text-[#1a1411]">AI / SEO</h1>
      </div>
      <p className="text-[#6b5d52] mt-1">Classificazione, SEO e sommario provvisori generati da titolo + descrizione. Niente trascrizioni o citazioni finché non c'è una fonte reale.</p>

      {msg && <p data-testid="ai-msg" className="text-sm text-[#4a3d34] mt-3 bg-[#f4ebe1] border border-[#ecdfce] rounded-lg px-3 py-2">{msg}</p>}

      <div className="mt-6 grid sm:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-[#ecdfce] p-4">
          <p className="text-xs text-[#9c8b7d] uppercase tracking-wide">Uso oggi</p>
          <p className="text-2xl font-anton text-[#EA4E1B]">{usage.daily}<span className="text-base text-[#9c8b7d]"> / {s.daily_limit}</span></p>
        </div>
        <div className="bg-white rounded-xl border border-[#ecdfce] p-4">
          <p className="text-xs text-[#9c8b7d] uppercase tracking-wide">Uso questo mese</p>
          <p className="text-2xl font-anton text-[#EA4E1B]">{usage.monthly}<span className="text-base text-[#9c8b7d]"> / {s.monthly_limit}</span></p>
        </div>
      </div>

      <div className="mt-6 bg-white rounded-xl border border-[#ecdfce] p-5">
        <h2 className="font-archivo font-extrabold text-[#1a1411] mb-2">Automazione</h2>
        <Row label="Generazione AI attiva" hint="Interruttore globale">
          <Toggle checked={!!s.enabled} onChange={(v) => setField("enabled", v)} testid="toggle-enabled" />
        </Row>
        <Row label="Automatico durante la sync YouTube" hint="Elabora i nuovi episodi/interviste importati">
          <Toggle checked={!!s.auto_on_sync} onChange={(v) => setField("auto_on_sync", v)} testid="toggle-auto-sync" />
        </Row>
        <Row label="Elabora anche gli Short" hint="Di norma gli Short non vengono elaborati">
          <Toggle checked={!!s.auto_shorts} onChange={(v) => setField("auto_shorts", v)} testid="toggle-auto-shorts" />
        </Row>
      </div>

      <div className="mt-6 bg-white rounded-xl border border-[#ecdfce] p-5">
        <h2 className="font-archivo font-extrabold text-[#1a1411] mb-2">Componenti</h2>
        <Row label="Classificazione" hint="episodio / intervista / short + ospite">
          <Toggle checked={!!s.components.classification} onChange={(v) => setComp("classification", v)} testid="toggle-classification" />
        </Row>
        <Row label="Riassunto e argomenti" hint="Sommario provvisorio + topics da titolo/descrizione">
          <Toggle checked={!!s.components.summary} onChange={(v) => setComp("summary", v)} testid="toggle-summary" />
        </Row>
        <Row label="SEO" hint="Title tag, meta description, H1">
          <Toggle checked={!!s.components.seo} onChange={(v) => setComp("seo", v)} testid="toggle-seo" />
        </Row>
        <Row label="Structured data" hint="Keyword per i dati strutturati">
          <Toggle checked={!!s.components.structured_data} onChange={(v) => setComp("structured_data", v)} testid="toggle-structured" />
        </Row>
        <Row label="Trascrizione (futura)" hint="Disponibile con sottotitoli/audio reali (Step 3 + OAuth)">
          <Toggle checked={false} onChange={() => {}} disabled testid="toggle-transcription" />
        </Row>
      </div>

      <div className="mt-6 bg-white rounded-xl border border-[#ecdfce] p-5">
        <h2 className="font-archivo font-extrabold text-[#1a1411] mb-2">Limiti e modello</h2>
        <div className="grid sm:grid-cols-3 gap-4 mt-2">
          <label className="text-sm">
            <span className="text-[#6b5d52]">Limite giornaliero</span>
            <input type="number" value={s.daily_limit} onChange={(e) => setField("daily_limit", parseInt(e.target.value || "0"))} data-testid="input-daily-limit"
              className="w-full mt-1 border border-[#ecdfce] rounded-lg px-3 py-2 outline-none focus:border-[#EA4E1B]" />
          </label>
          <label className="text-sm">
            <span className="text-[#6b5d52]">Limite mensile</span>
            <input type="number" value={s.monthly_limit} onChange={(e) => setField("monthly_limit", parseInt(e.target.value || "0"))} data-testid="input-monthly-limit"
              className="w-full mt-1 border border-[#ecdfce] rounded-lg px-3 py-2 outline-none focus:border-[#EA4E1B]" />
          </label>
          <label className="text-sm">
            <span className="text-[#6b5d52]">Modello</span>
            <input value={s.model} readOnly data-testid="input-model"
              className="w-full mt-1 border border-[#ecdfce] rounded-lg px-3 py-2 bg-[#fbf7f2] text-[#6b5d52]" />
          </label>
        </div>
      </div>

      <div className="mt-6 flex items-center gap-3">
        <button onClick={save} disabled={saving} data-testid="ai-save-btn"
          className="inline-flex items-center gap-2 bg-[#EA4E1B] hover:bg-[#d3430f] text-white font-bold uppercase tracking-wide px-5 py-3 rounded-lg disabled:opacity-60 transition-colors">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Salva impostazioni
        </button>
        <button onClick={batch} disabled={batchBusy} data-testid="ai-batch-btn-settings"
          className="inline-flex items-center gap-2 bg-[#14100e] hover:bg-[#EA4E1B] text-white font-bold uppercase tracking-wide px-5 py-3 rounded-lg disabled:opacity-60 transition-colors">
          {batchBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />} Elabora archivio ora
        </button>
      </div>

      <div className="mt-6 flex items-start gap-2 bg-[#fff7ed] border border-amber-200 rounded-xl px-4 py-3">
        <Info className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-[#6b5d52]">I contenuti restano con <code className="bg-white px-1 rounded">transcription_status: pending</code>. Trascrizioni, citazioni e capitoli con minutaggio verranno aggiunti automaticamente solo quando saranno disponibili sottotitoli o audio reali (Step 3 + YouTube OAuth). I contenuti falliti passano a "Da verificare".</p>
      </div>
    </div>
  );
}
