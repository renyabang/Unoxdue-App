import React, { useState } from "react";
import { Upload, ScanLine, Save, CheckCircle2, Loader2, AlertTriangle, Plus, X, FileText } from "lucide-react";
import { api } from "./api";

const TIPSTERS = ["Il Marziano", "Sono Micuccio", "Il Ninja"];
const DISCLAIMER = "Quote rilevate dalla grafica comparativa fornita dal team al momento della pubblicazione. Le quote possono variare.";

const ConfBadge = ({ value }) => {
  if (value == null) return null;
  const pct = Math.round(value * 100);
  const low = value < 0.6;
  return (
    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${low ? "bg-[#fde7d6] text-[#c2410c]" : "bg-green-100 text-green-700"}`}>
      {pct}%
    </span>
  );
};

export default function SlipUploader() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [uploadId, setUploadId] = useState(null);
  const [sourceImage, setSourceImage] = useState(null);
  const [rawText, setRawText] = useState("");
  const [showRaw, setShowRaw] = useState(false);
  const [tipster, setTipster] = useState(TIPSTERS[0]);
  const [season, setSeason] = useState("");
  const [round, setRound] = useState("");
  const [saved, setSaved] = useState(null);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  const onFile = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    setFile(f); setPreview(URL.createObjectURL(f));
    setData(null); setSaved(null); setErr(""); setRawText(""); setUploadId(null);
  };

  const analyze = async () => {
    if (!file) return;
    setLoading(true); setErr("");
    try {
      const r = await api.ocr(file);
      if (!r.ok) { setErr(r.error || "OCR non riuscito"); }
      else {
        setData(r.data);
        setUploadId(r.upload_id);
        setSourceImage(r.uploaded_file);
        setRawText(r.raw_text || "");
        setSeason(r.suggested_season || "");
        if (r.data.round) setRound(String(r.data.round));
        if (r.data.tipster && TIPSTERS.includes(r.data.tipster)) setTipster(r.data.tipster);
      }
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  };

  const updateSel = (idx, key, val) => {
    const sels = [...data.selections];
    sels[idx] = { ...sels[idx], [key]: val };
    if (key === "odds" && val) sels[idx].needs_review = false;
    setData({ ...data, selections: sels });
  };
  const updateBook = (si, bi, key, val) => {
    const sels = [...data.selections];
    const books = [...(sels[si].bookmakers || [])];
    books[bi] = { ...books[bi], [key]: val, needs_review: false };
    sels[si] = { ...sels[si], bookmakers: books };
    setData({ ...data, selections: sels });
  };
  const addBook = (si) => {
    const sels = [...data.selections];
    const books = [...(sels[si].bookmakers || []), { bookmaker: "", odds: "", confidence: null, needs_review: false }];
    sels[si] = { ...sels[si], bookmakers: books };
    setData({ ...data, selections: sels });
  };
  const removeBook = (si, bi) => {
    const sels = [...data.selections];
    sels[si] = { ...sels[si], bookmakers: (sels[si].bookmakers || []).filter((_, i) => i !== bi) };
    setData({ ...data, selections: sels });
  };

  const save = async () => {
    setErr(""); setSaved(null);
    if (!season || !round) { setErr("Inserisci stagione e giornata"); return; }
    const needs_review = data.selections.some((s) => !s.odds || s.needs_review);
    setSaving(true);
    try {
      const r = await api.addPick({
        competition: data.competition || "Serie A", season, round: parseInt(round, 10),
        tipster, type: data.type || "Multipla", total_odds: data.total_odds || "",
        selections: data.selections,
        source_image: sourceImage, ocr_upload_id: uploadId,
        mapping_version: data.mapping_version, needs_review,
      });
      setSaved(r.public_url);
    } catch (e) { setErr(e.message); }
    finally { setSaving(false); }
  };

  return (
    <div data-testid="schedine-page">
      <h1 className="font-anton text-3xl text-[#1a1411]">Schedine / Pronostici</h1>
      <p className="text-[#6b5d52] mt-1">Carica la grafica comparativa del team: l'OCR estrae quote per bookmaker, mercati e selezioni, rimuove importi/bonus/branding e prepara la pagina pronostici. Le quote pubblicate restano quelle della grafica.</p>

      <div className="grid lg:grid-cols-2 gap-6 mt-6">
        {/* ------- Colonna sinistra: upload + sorgente + OCR ------- */}
        <div className="bg-white rounded-xl border border-[#ecdfce] p-5">
          <label className="flex flex-col items-center justify-center border-2 border-dashed border-[#e2d4c2] rounded-xl py-10 cursor-pointer hover:border-[#EA4E1B] transition-colors">
            <Upload className="w-8 h-8 text-[#EA4E1B]" />
            <span className="text-sm text-[#6b5d52] mt-2">Clicca per caricare la grafica comparativa</span>
            <input data-testid="slip-file-input" type="file" accept="image/*" className="hidden" onChange={onFile} />
          </label>
          {preview && <img src={preview} alt="grafica" data-testid="slip-preview" className="mt-4 w-full rounded-lg border border-[#ecdfce]" />}
          {file && (
            <button data-testid="slip-analyze-btn" onClick={analyze} disabled={loading} className="mt-4 w-full inline-flex items-center justify-center gap-2 bg-[#14100e] hover:bg-[#EA4E1B] text-white text-sm font-bold uppercase tracking-wide px-4 py-3 rounded-lg disabled:opacity-60 transition-colors">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ScanLine className="w-4 h-4" />}
              {loading ? "Analisi in corso..." : "Analizza grafica"}
            </button>
          )}
          {err && <p data-testid="slip-error" className="text-red-500 text-sm mt-3">{err}</p>}

          {rawText && (
            <div className="mt-4">
              <button onClick={() => setShowRaw(!showRaw)} className="inline-flex items-center gap-2 text-xs font-semibold text-[#6b5d52] hover:text-[#1a1411]">
                <FileText className="w-3.5 h-3.5" /> {showRaw ? "Nascondi" : "Mostra"} testo OCR (audit)
              </button>
              {showRaw && <pre data-testid="slip-raw-ocr" className="mt-2 text-[11px] bg-[#fbf7f2] p-3 rounded-lg overflow-auto max-h-48 text-[#4a3d34] whitespace-pre-wrap">{rawText}</pre>}
            </div>
          )}
        </div>

        {/* ------- Colonna destra: revisione ------- */}
        <div className="bg-white rounded-xl border border-[#ecdfce] p-5">
          {!data && <p className="text-[#9c8b7d] text-sm">I dati estratti appariranno qui per la revisione.</p>}
          {data && (
            <>
              {data.needs_review && (
                <div data-testid="slip-review-warning" className="flex items-start gap-2 bg-[#fde7d6] border border-[#f6c9a8] rounded-lg px-3 py-2 mb-4">
                  <AlertTriangle className="w-4 h-4 text-[#c2410c] flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-[#9a3412]">Alcuni campi hanno bassa affidabilità: controlla e correggi i valori evidenziati prima di salvare. Nessun valore è stato inventato.</p>
                </div>
              )}
              <div className="grid grid-cols-3 gap-3 mb-4">
                <div>
                  <label className="text-xs font-semibold text-[#6b5d52] uppercase">Tipster</label>
                  <select data-testid="slip-tipster" value={tipster} onChange={(e) => setTipster(e.target.value)} className="w-full mt-1 border border-[#e2d4c2] rounded-lg px-2 py-2 text-sm">
                    {TIPSTERS.map((t) => <option key={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-[#6b5d52] uppercase">Stagione</label>
                  <input data-testid="slip-season" value={season} onChange={(e) => setSeason(e.target.value)} placeholder="2025-2026" className="w-full mt-1 border border-[#e2d4c2] rounded-lg px-2 py-2 text-sm" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-[#6b5d52] uppercase">Giornata</label>
                  <input data-testid="slip-round" value={round} onChange={(e) => setRound(e.target.value)} placeholder="38" className="w-full mt-1 border border-[#e2d4c2] rounded-lg px-2 py-2 text-sm" />
                </div>
              </div>

              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-semibold text-[#6b5d52] uppercase">Selezioni ({data.selections?.length})</p>
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-[#6b5d52]">Quota totale</span>
                  <input data-testid="slip-total-odds" value={data.total_odds} onChange={(e) => setData({ ...data, total_odds: e.target.value })} className="w-16 text-sm font-bold text-[#EA4E1B] border border-[#e2d4c2] rounded px-1.5 py-1 text-center" />
                </div>
              </div>

              <div className="space-y-3 max-h-[28rem] overflow-auto pr-1" data-testid="slip-selections">
                {data.selections?.map((s, i) => (
                  <div key={i} className={`border rounded-lg p-3 ${s.needs_review ? "border-[#f6c9a8] bg-[#fffaf6]" : "border-[#f0e7da]"}`} data-testid={`slip-sel-${i}`}>
                    <div className="flex items-center justify-between gap-2">
                      <input value={s.match} onChange={(e) => updateSel(i, "match", e.target.value)} placeholder="Partita" className="flex-1 font-semibold text-sm text-[#1a1411] outline-none bg-transparent" />
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        <ConfBadge value={s.confidence} />
                        {s.needs_review && <span className="text-[10px] font-bold uppercase text-[#c2410c] bg-[#fde7d6] px-1.5 py-0.5 rounded">Da verificare</span>}
                      </div>
                    </div>
                    <div className="flex gap-2 mt-1.5">
                      <input value={s.market} onChange={(e) => updateSel(i, "market", e.target.value)} placeholder="Mercato" className="flex-1 text-xs text-[#6b5d52] outline-none border border-[#f0e7da] rounded px-1.5 py-1" />
                      <input value={s.pick} onChange={(e) => updateSel(i, "pick", e.target.value)} placeholder="Esito" className="w-20 text-xs text-[#6b5d52] outline-none border border-[#f0e7da] rounded px-1.5 py-1" />
                      <input value={s.odds} onChange={(e) => updateSel(i, "odds", e.target.value)} placeholder="Quota" className="w-16 text-xs font-bold text-[#EA4E1B] outline-none border border-[#f0e7da] rounded px-1.5 py-1 text-center" data-testid={`slip-sel-odds-${i}`} />
                    </div>
                    {/* Confronto bookmaker */}
                    <div className="mt-2 pl-2 border-l-2 border-[#efe4d6]">
                      <p className="text-[10px] font-semibold text-[#9c8b7d] uppercase tracking-wide mb-1">Confronto bookmaker</p>
                      <div className="space-y-1">
                        {(s.bookmakers || []).map((b, bi) => (
                          <div key={bi} className="flex items-center gap-1.5" data-testid={`slip-book-${i}-${bi}`}>
                            <input value={b.bookmaker} onChange={(e) => updateBook(i, bi, "bookmaker", e.target.value)} placeholder="Bookmaker" className={`flex-1 text-xs outline-none border rounded px-1.5 py-1 ${b.needs_review ? "border-[#f6c9a8] bg-[#fffaf6]" : "border-[#f0e7da]"}`} />
                            <input value={b.odds} onChange={(e) => updateBook(i, bi, "odds", e.target.value)} placeholder="Quota" className={`w-16 text-xs font-bold text-[#1a1411] outline-none border rounded px-1.5 py-1 text-center ${b.needs_review ? "border-[#f6c9a8] bg-[#fffaf6]" : "border-[#f0e7da]"}`} />
                            <ConfBadge value={b.confidence} />
                            <button onClick={() => removeBook(i, bi)} className="text-[#c2410c] hover:text-red-700"><X className="w-3.5 h-3.5" /></button>
                          </div>
                        ))}
                      </div>
                      <button onClick={() => addBook(i)} data-testid={`slip-add-book-${i}`} className="mt-1 inline-flex items-center gap-1 text-[11px] font-semibold text-[#EA4E1B] hover:text-[#d3430f]">
                        <Plus className="w-3 h-3" /> Aggiungi bookmaker
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              <p className="text-[11px] text-[#9c8b7d] mt-3 leading-relaxed">{DISCLAIMER}</p>

              <button data-testid="slip-save-btn" onClick={save} disabled={saving} className="mt-3 w-full inline-flex items-center justify-center gap-2 bg-[#EA4E1B] hover:bg-[#d3430f] text-white text-sm font-bold uppercase tracking-wide px-4 py-3 rounded-lg disabled:opacity-60 transition-colors">
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} {saving ? "Salvataggio..." : "Salva giocata"}
              </button>
              {saved && (
                <p data-testid="slip-saved" className="mt-3 text-sm text-green-700 flex items-center gap-2">
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
