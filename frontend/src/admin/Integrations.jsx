import React, { useEffect, useState } from "react";
import { CheckCircle2, XCircle, Search, Loader2, BarChart3 } from "lucide-react";
import { api } from "./api";

const ROWS = [
  { key: "youtube_channel", label: "Canale YouTube (feed pubblico)", env: "YOUTUBE_CHANNEL_ID", real: "Sync nuovi video dal feed RSS (attivo)." },
  { key: "vision_ocr", label: "OCR schedine (OpenAI Vision)", env: "EMERGENT_LLM_KEY", real: "Lettura schedine via Emergent LLM key (attivo)." },
  { key: "youtube_api_key", label: "YouTube Data API", env: "YOUTUBE_API_KEY", real: "Archivio completo + durate + WebSub. Senza chiave: solo feed RSS recente." },
  { key: "youtube_oauth", label: "YouTube OAuth (sottotitoli)", env: "GOOGLE_OAUTH_CLIENT_ID / SECRET / REFRESH_TOKEN", real: "Download sottotitoli ufficiali per le trascrizioni reali." },
  { key: "odds_api", label: "Comparatore quote esterno (disattivato)", env: "ODDS_API_URL / ODDS_API_KEY", real: "Funzione futura: NON usata. Le quote provengono dall'OCR della grafica comparativa del team." },
  { key: "perplexity", label: "Rassegna stampa (Perplexity)", env: "PERPLEXITY_API_KEY", real: "Ricerca automatica menzioni stampa." },
  { key: "audio_transcription", label: "Trascrizione audio", env: "OPENAI_AUDIO_API_KEY", real: "Trascrizione quando mancano i sottotitoli." },
];

function Field({ label, hint, placeholder, value, onChange, testid }) {
  return (
    <div>
      <label className="block text-sm font-semibold text-[#1a1411]">{label}</label>
      <input
        type="text"
        value={value || ""}
        onChange={onChange}
        placeholder={placeholder}
        data-testid={testid}
        spellCheck={false}
        className="mt-1.5 w-full rounded-lg border border-[#e5d8c7] bg-[#fbf7f2] px-3 py-2.5 text-sm text-[#1a1411] focus:outline-none focus:ring-2 focus:ring-[#EA4E1B]/40 focus:border-[#EA4E1B] transition-colors"
      />
      <p className="mt-1 text-xs text-[#8a7a6c]">{hint}</p>
    </div>
  );
}

export default function Integrations() {
  const [integ, setInteg] = useState({});
  const [press, setPress] = useState(null);
  const [searching, setSearching] = useState(false);
  const [seo, setSeo] = useState({ ga_measurement_id: "", google_site_verification: "", bing_site_verification: "" });
  const [savingSeo, setSavingSeo] = useState(false);
  const [savedSeo, setSavedSeo] = useState(false);

  useEffect(() => { api.settings().then((s) => setInteg(s.integrations || {})).catch(() => {}); }, []);
  useEffect(() => { api.seoTools().then((d) => setSeo({ ga_measurement_id: d.ga_measurement_id || "", google_site_verification: d.google_site_verification || "", bing_site_verification: d.bing_site_verification || "" })).catch(() => {}); }, []);

  const setSeoField = (k) => (e) => setSeo((s) => ({ ...s, [k]: e.target.value }));
  const saveSeo = async () => {
    setSavingSeo(true); setSavedSeo(false);
    try { await api.updateSeoTools(seo); setSavedSeo(true); setTimeout(() => setSavedSeo(false), 2500); }
    catch (e) { alert(e.message); }
    setSavingSeo(false);
  };

  const testPress = async () => {
    setSearching(true);
    try { setPress(await api.pressSearch("UnoXdue podcast")); } catch (e) { setPress({ error: e.message }); }
    setSearching(false);
  };

  return (
    <div>
      <h1 className="font-anton text-3xl text-[#1a1411]">Integrazioni</h1>
      <p className="text-[#6b5d52] mt-1">Le credenziali si configurano nelle variabili ambiente del server (mai in chat). Le integrazioni senza chiave restano in modalità demo.</p>

      <div className="mt-6 bg-white rounded-xl border border-[#ecdfce] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[#fbf7f2] text-[#6b5d52] text-left">
            <tr>
              <th className="px-4 py-3 font-semibold">Stato</th>
              <th className="px-4 py-3 font-semibold">Integrazione</th>
              <th className="px-4 py-3 font-semibold">Variabile ambiente</th>
              <th className="px-4 py-3 font-semibold">Funzione</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((r) => (
              <tr key={r.key} className="border-t border-[#f0e7da]">
                <td className="px-4 py-3">{integ[r.key] ? <CheckCircle2 className="w-4 h-4 text-green-600" /> : <XCircle className="w-4 h-4 text-[#c2410c]" />}</td>
                <td className="px-4 py-3 font-medium text-[#1a1411]">{r.label}</td>
                <td className="px-4 py-3"><code className="text-xs bg-[#fbf7f2] px-2 py-1 rounded">{r.env}</code></td>
                <td className="px-4 py-3 text-[#6b5d52]">{r.real}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-6 bg-white rounded-xl border border-[#ecdfce] p-5" data-testid="seo-tools-card">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-[#EA4E1B]" />
          <h2 className="font-archivo font-extrabold text-[#1a1411]">Strumenti SEO — Analytics e verifiche</h2>
          {seo.ga_measurement_id ? (
            <span className="ml-1 inline-flex items-center gap-1 text-xs font-bold text-green-700 bg-green-50 px-2 py-0.5 rounded-full"><CheckCircle2 className="w-3.5 h-3.5" /> Analytics attivo</span>
          ) : (
            <span className="ml-1 inline-flex items-center gap-1 text-xs font-bold text-[#8a7a6c] bg-[#fbf7f2] px-2 py-0.5 rounded-full">Analytics non configurato</span>
          )}
        </div>
        <p className="text-sm text-[#6b5d52] mt-1">Incolla i codici e premi Salva: si applicano subito sul sito pubblico, senza riavviare il server. Lascia un campo vuoto per disattivarlo.</p>

        <div className="mt-5 space-y-4 max-w-2xl">
          <Field
            label="Google Analytics 4 — ID misurazione"
            hint="Formato G-XXXXXXXXXX. In GA4 → Amministrazione → Flussi di dati → seleziona il flusso web."
            placeholder="G-XXXXXXXXXX"
            value={seo.ga_measurement_id}
            onChange={setSeoField("ga_measurement_id")}
            testid="seo-ga-input"
          />
          <Field
            label="Google Search Console — codice di verifica"
            hint='Da "Tag HTML": copia solo il valore dentro content="...". In alternativa puoi verificare via record DNS TXT.'
            placeholder="es. abcdEFgh1234..."
            value={seo.google_site_verification}
            onChange={setSeoField("google_site_verification")}
            testid="seo-gsc-input"
          />
          <Field
            label="Bing Webmaster Tools — codice di verifica"
            hint='Da "Meta tag": copia il valore content="...". Più semplice: in Bing scegli "Importa da Google Search Console" (zero codice).'
            placeholder="es. 1A2B3C4D..."
            value={seo.bing_site_verification}
            onChange={setSeoField("bing_site_verification")}
            testid="seo-bing-input"
          />
        </div>

        <div className="mt-5 flex items-center gap-3">
          <button onClick={saveSeo} disabled={savingSeo} data-testid="seo-save-button" className="inline-flex items-center gap-2 bg-[#14100e] hover:bg-[#EA4E1B] text-white text-sm font-bold uppercase tracking-wide px-5 py-2.5 rounded-lg disabled:opacity-60 transition-colors">
            {savingSeo ? <Loader2 className="w-4 h-4 animate-spin" /> : null} Salva
          </button>
          {savedSeo && <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-green-700" data-testid="seo-saved-indicator"><CheckCircle2 className="w-4 h-4" /> Salvato e attivo</span>}
        </div>

        <p className="mt-4 text-xs text-[#8a7a6c]">Dopo aver salvato e verificato la proprietà, ricordati di inviare la sitemap <code className="bg-[#fbf7f2] px-1.5 py-0.5 rounded">/sitemap.xml</code> su Search Console e Bing.</p>
      </div>

      <div className="mt-6 bg-white rounded-xl border border-[#ecdfce] p-5">
        <div className="flex items-center justify-between">
          <h2 className="font-archivo font-extrabold text-[#1a1411]">Test rassegna stampa</h2>
          <button onClick={testPress} disabled={searching} className="inline-flex items-center gap-2 bg-[#14100e] hover:bg-[#EA4E1B] text-white text-sm font-bold uppercase tracking-wide px-4 py-2.5 rounded-lg disabled:opacity-60 transition-colors">
            {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />} Cerca menzioni
          </button>
        </div>
        {press && (
          <pre className="mt-4 text-xs bg-[#fbf7f2] p-3 rounded-lg overflow-auto max-h-60 text-[#4a3d34]">{JSON.stringify(press, null, 2)}</pre>
        )}
      </div>
    </div>
  );
}
