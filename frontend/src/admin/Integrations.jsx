import React, { useEffect, useState } from "react";
import { CheckCircle2, XCircle, Search, Loader2 } from "lucide-react";
import { api } from "./api";

const ROWS = [
  { key: "youtube_channel", label: "Canale YouTube (feed pubblico)", env: "YOUTUBE_CHANNEL_ID", real: "Sync nuovi video dal feed RSS (attivo)." },
  { key: "vision_ocr", label: "OCR schedine (OpenAI Vision)", env: "EMERGENT_LLM_KEY", real: "Lettura schedine via Emergent LLM key (attivo)." },
  { key: "youtube_api_key", label: "YouTube Data API", env: "YOUTUBE_API_KEY", real: "Dettagli extra (durata, playlist). Opzionale." },
  { key: "odds_api", label: "Comparatore quote", env: "ODDS_API_URL / ODDS_API_KEY", real: "Quote reali dal comparatore." },
  { key: "perplexity", label: "Rassegna stampa (Perplexity)", env: "PERPLEXITY_API_KEY", real: "Ricerca automatica menzioni stampa." },
  { key: "audio_transcription", label: "Trascrizione audio", env: "OPENAI_AUDIO_API_KEY", real: "Trascrizione quando mancano i sottotitoli." },
];

export default function Integrations() {
  const [integ, setInteg] = useState({});
  const [press, setPress] = useState(null);
  const [searching, setSearching] = useState(false);

  useEffect(() => { api.settings().then((s) => setInteg(s.integrations || {})).catch(() => {}); }, []);

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
