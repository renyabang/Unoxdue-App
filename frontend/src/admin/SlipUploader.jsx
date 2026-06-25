import React, { useState } from "react";
import { Upload, ScanLine, Save, CheckCircle2, Loader2 } from "lucide-react";
import { api } from "./api";

const TIPSTERS = ["Il Marziano", "Sono Micuccio", "Il Ninja"];

export default function SlipUploader() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [tipster, setTipster] = useState(TIPSTERS[0]);
  const [season, setSeason] = useState("");
  const [round, setRound] = useState("");
  const [saved, setSaved] = useState(null);
  const [err, setErr] = useState("");

  const onFile = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    setFile(f); setPreview(URL.createObjectURL(f)); setData(null); setSaved(null); setErr("");
  };

  const analyze = async () => {
    if (!file) return;
    setLoading(true); setErr("");
    try {
      const r = await api.ocr(file);
      if (!r.ok) { setErr(r.error || "OCR non riuscito"); }
      else { setData(r.data); setSeason(r.suggested_season || ""); }
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  const updateSel = (idx, key, val) => {
    const sels = [...data.selections];
    sels[idx] = { ...sels[idx], [key]: val };
    setData({ ...data, selections: sels });
  };

  const save = async () => {
    setErr(""); setSaved(null);
    if (!season || !round) { setErr("Inserisci stagione e giornata"); return; }
    try {
      const r = await api.addPick({
        competition: "Serie A", season, round: parseInt(round, 10),
        tipster, type: data.type || "Multipla", total_odds: data.total_odds || "",
        selections: data.selections,
      });
      setSaved(r.public_url);
    } catch (e) { setErr(e.message); }
  };

  return (
    <div>
      <h1 className="font-anton text-3xl text-[#1a1411]">Schedine / Pronostici</h1>
      <p className="text-[#6b5d52] mt-1">Carica l'immagine di una giocata: il sistema legge i dati con OCR Vision, rimuove importi/bonus/branding e crea la pagina pronostici.</p>

      <div className="grid md:grid-cols-2 gap-6 mt-6">
        <div className="bg-white rounded-xl border border-[#ecdfce] p-5">
          <label className="flex flex-col items-center justify-center border-2 border-dashed border-[#e2d4c2] rounded-xl py-10 cursor-pointer hover:border-[#EA4E1B] transition-colors">
            <Upload className="w-8 h-8 text-[#EA4E1B]" />
            <span className="text-sm text-[#6b5d52] mt-2">Clicca per caricare l'immagine della schedina</span>
            <input type="file" accept="image/*" className="hidden" onChange={onFile} />
          </label>
          {preview && <img src={preview} alt="schedina" className="mt-4 w-full rounded-lg border border-[#ecdfce]" />}
          {file && (
            <button onClick={analyze} disabled={loading} className="mt-4 w-full inline-flex items-center justify-center gap-2 bg-[#14100e] hover:bg-[#EA4E1B] text-white text-sm font-bold uppercase tracking-wide px-4 py-3 rounded-lg disabled:opacity-60 transition-colors">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ScanLine className="w-4 h-4" />}
              {loading ? "Analisi in corso..." : "Analizza schedina"}
            </button>
          )}
          {err && <p className="text-red-500 text-sm mt-3">{err}</p>}
        </div>

        <div className="bg-white rounded-xl border border-[#ecdfce] p-5">
          {!data && <p className="text-[#9c8b7d] text-sm">I dati estratti appariranno qui per la revisione.</p>}
          {data && (
            <>
              <div className="grid grid-cols-3 gap-3 mb-4">
                <div>
                  <label className="text-xs font-semibold text-[#6b5d52] uppercase">Tipster</label>
                  <select value={tipster} onChange={(e) => setTipster(e.target.value)} className="w-full mt-1 border border-[#e2d4c2] rounded-lg px-2 py-2 text-sm">
                    {TIPSTERS.map((t) => <option key={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-[#6b5d52] uppercase">Stagione</label>
                  <input value={season} onChange={(e) => setSeason(e.target.value)} placeholder="2025-2026" className="w-full mt-1 border border-[#e2d4c2] rounded-lg px-2 py-2 text-sm" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-[#6b5d52] uppercase">Giornata</label>
                  <input value={round} onChange={(e) => setRound(e.target.value)} placeholder="38" className="w-full mt-1 border border-[#e2d4c2] rounded-lg px-2 py-2 text-sm" />
                </div>
              </div>
              <p className="text-xs font-semibold text-[#6b5d52] uppercase mb-2">Selezioni ({data.selections?.length}) · quota totale {data.total_odds}</p>
              <div className="space-y-2 max-h-72 overflow-auto pr-1">
                {data.selections?.map((s, i) => (
                  <div key={i} className="border border-[#f0e7da] rounded-lg p-2.5">
                    <input value={s.match} onChange={(e) => updateSel(i, "match", e.target.value)} className="w-full font-semibold text-sm text-[#1a1411] outline-none" />
                    <div className="flex gap-2 mt-1">
                      <input value={s.market} onChange={(e) => updateSel(i, "market", e.target.value)} className="flex-1 text-xs text-[#6b5d52] outline-none" />
                      <input value={s.pick} onChange={(e) => updateSel(i, "pick", e.target.value)} className="w-20 text-xs text-[#6b5d52] outline-none" />
                      <input value={s.odds} onChange={(e) => updateSel(i, "odds", e.target.value)} className="w-14 text-xs font-bold text-[#EA4E1B] outline-none" />
                    </div>
                  </div>
                ))}
              </div>
              <button onClick={save} className="mt-4 w-full inline-flex items-center justify-center gap-2 bg-[#EA4E1B] hover:bg-[#d3430f] text-white text-sm font-bold uppercase tracking-wide px-4 py-3 rounded-lg">
                <Save className="w-4 h-4" /> Salva giocata
              </button>
              {saved && (
                <p className="mt-3 text-sm text-green-700 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4" /> Salvato! <a href={`${process.env.REACT_APP_BACKEND_URL}/api/seo/pronostici/serie-a/${season}/giornata-${round}`} target="_blank" rel="noopener noreferrer" className="underline">Anteprima pagina</a>
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
