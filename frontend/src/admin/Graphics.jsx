import React, { useEffect, useState, useRef } from "react";
import { Image as ImageIcon, Loader2, RefreshCw, Download, Link2, Pencil, Save, X, Radio, AlertTriangle, ImagePlus, Upload, RotateCcw } from "lucide-react";
import { api } from "./api";

const FORMATS = [
  { key: "horizontal", label: "Orizzontale" },
  { key: "square", label: "Quadrato 1:1" },
  { key: "vertical", label: "Verticale 9:16" },
];

const LIVE_TARGETS = [
  { v: "twitch", l: "Twitch" },
  { v: "youtube", l: "Live YouTube" },
  { v: "latest_episode", l: "Ultimo episodio" },
  { v: "custom", l: "URL personalizzata" },
];

function LiveCard() {
  const [live, setLive] = useState({ target: "twitch", url: "" });
  const [resolved, setResolved] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api.getLive().then((r) => { setLive(r.live); setResolved(r.resolved); }).catch(() => {});
  }, []);

  const save = async () => {
    setSaving(true); setMsg("");
    try { const r = await api.setLive(live); setResolved(r.resolved); setMsg("Destinazione /live/ aggiornata."); }
    catch (e) { setMsg("Errore: " + e.message); }
    finally { setSaving(false); }
  };

  return (
    <div className="bg-white rounded-xl border border-[#ecdfce] p-5" data-testid="live-card">
      <div className="flex items-center gap-2"><Radio className="w-5 h-5 text-[#EA4E1B]" />
        <h2 className="font-archivo font-extrabold text-[#1a1411]">Destinazione QR / <code className="text-sm">/live/</code></h2></div>
      <p className="text-[#6b5d52] text-sm mt-1">Cambia dove punta il QR senza rigenerare le immagini già pubblicate.</p>
      <div className="flex flex-wrap items-end gap-3 mt-4">
        <label className="text-sm">
          <span className="text-[#6b5d52]">Punta a</span>
          <select value={live.target} onChange={(e) => setLive({ ...live, target: e.target.value })} data-testid="live-target"
            className="block mt-1 border border-[#ecdfce] rounded-lg px-3 py-2 outline-none focus:border-[#EA4E1B] min-w-[200px]">
            {LIVE_TARGETS.map((t) => <option key={t.v} value={t.v}>{t.l}</option>)}
          </select>
        </label>
        {live.target === "custom" && (
          <label className="text-sm flex-1 min-w-[240px]">
            <span className="text-[#6b5d52]">URL</span>
            <input value={live.url || ""} onChange={(e) => setLive({ ...live, url: e.target.value })} placeholder="https://..." data-testid="live-url"
              className="block w-full mt-1 border border-[#ecdfce] rounded-lg px-3 py-2 outline-none focus:border-[#EA4E1B]" />
          </label>
        )}
        <button onClick={save} disabled={saving} data-testid="live-save"
          className="inline-flex items-center gap-2 bg-[#EA4E1B] hover:bg-[#d3430f] text-white font-bold uppercase tracking-wide px-4 py-2.5 rounded-lg disabled:opacity-60">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Salva
        </button>
      </div>
      {resolved && <p className="text-xs text-[#9c8b7d] mt-3">Attualmente reindirizza a: <span className="text-[#EA4E1B] font-semibold break-all">{resolved}</span></p>}
      {msg && <p className="text-sm text-[#4a3d34] mt-2" data-testid="live-msg">{msg}</p>}
    </div>
  );
}

function PickCard({ pred, pick, idx, onChanged }) {
  const key = `${pred.season}-${pred.round}-${idx}`;
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(null);
  const [msg, setMsg] = useState("");
  const [bust, setBust] = useState(Date.now());
  const g = pick.graphics;
  const hasErr = g && g.errors && Object.keys(g.errors).length > 0;

  const generate = async () => {
    setBusy(true); setMsg("");
    try {
      const r = await api.generateGraphics({ season: pred.season, round: pred.round, pick_index: idx });
      setBust(Date.now());
      setMsg(r.ok ? "Grafiche generate." : "Errore: " + JSON.stringify(r.errors || r.error));
      onChanged && onChanged();
    } catch (e) { setMsg("Errore: " + e.message); }
    finally { setBusy(false); }
  };

  const startEdit = () => {
    setDraft({ type: pick.type || "", total_odds: pick.total_odds || "",
      selections: (pick.selections || []).map((s) => ({ ...s })) });
    setEditing(true);
  };
  const saveEdit = async () => {
    setBusy(true); setMsg("");
    try {
      await api.editPick({ season: pred.season, round: pred.round, pick_index: idx,
        type: draft.type, total_odds: draft.total_odds, selections: draft.selections });
      setEditing(false); setMsg("Dati aggiornati. Ora puoi rigenerare.");
      onChanged && onChanged();
    } catch (e) { setMsg("Errore salvataggio: " + e.message); }
    finally { setBusy(false); }
  };
  const setSel = (i, k, v) => setDraft((d) => {
    const sels = d.selections.map((s, j) => (j === i ? { ...s, [k]: v } : s));
    return { ...d, selections: sels };
  });

  const copy = (url) => { navigator.clipboard?.writeText(url); setMsg("URL copiato: " + url); };

  return (
    <div className="bg-white rounded-xl border border-[#ecdfce] p-4" data-testid={`pick-card-${key}`}>
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <p className="font-archivo font-extrabold text-[#1a1411]">{pick.tipster}</p>
          <p className="text-xs text-[#6b5d52]">{pick.type} · {(pick.selections || []).length} selezioni · quota {pick.total_odds || "n.d."}</p>
        </div>
        <div className="flex items-center gap-2">
          {g && !hasErr && <span className="text-xs font-bold px-2 py-1 rounded-full bg-emerald-100 text-emerald-700">Generato</span>}
          {hasErr && <span className="text-xs font-bold px-2 py-1 rounded-full bg-red-100 text-red-700 inline-flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> Errore</span>}
          <button onClick={startEdit} disabled={busy} data-testid={`pick-edit-${key}`}
            className="inline-flex items-center gap-1 text-sm text-[#6b5d52] hover:text-[#EA4E1B]"><Pencil className="w-4 h-4" /> Modifica</button>
          <button onClick={generate} disabled={busy} data-testid={`pick-generate-${key}`}
            className="inline-flex items-center gap-2 bg-[#14100e] hover:bg-[#EA4E1B] text-white text-sm font-bold uppercase tracking-wide px-3 py-2 rounded-lg disabled:opacity-60">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />} {g ? "Rigenera" : "Genera"}
          </button>
        </div>
      </div>

      {editing && draft && (
        <div className="mt-4 bg-[#fbf7f2] border border-[#ecdfce] rounded-lg p-3" data-testid={`pick-editor-${key}`}>
          <div className="flex gap-3 mb-2">
            <input value={draft.type} onChange={(e) => setDraft({ ...draft, type: e.target.value })} placeholder="Tipo"
              className="border border-[#ecdfce] rounded px-2 py-1 text-sm w-40" />
            <input value={draft.total_odds} onChange={(e) => setDraft({ ...draft, total_odds: e.target.value })} placeholder="Quota totale"
              className="border border-[#ecdfce] rounded px-2 py-1 text-sm w-32" />
          </div>
          {draft.selections.map((s, i) => (
            <div key={i} className="grid grid-cols-12 gap-2 mb-1.5">
              <input value={s.match || ""} onChange={(e) => setSel(i, "match", e.target.value)} placeholder="Partita" className="col-span-4 border border-[#ecdfce] rounded px-2 py-1 text-sm" />
              <input value={s.market || ""} onChange={(e) => setSel(i, "market", e.target.value)} placeholder="Mercato" className="col-span-4 border border-[#ecdfce] rounded px-2 py-1 text-sm" />
              <input value={s.pick || ""} onChange={(e) => setSel(i, "pick", e.target.value)} placeholder="Esito" className="col-span-2 border border-[#ecdfce] rounded px-2 py-1 text-sm" />
              <input value={s.odds || ""} onChange={(e) => setSel(i, "odds", e.target.value)} placeholder="Quota" className="col-span-2 border border-[#ecdfce] rounded px-2 py-1 text-sm" />
            </div>
          ))}
          <div className="flex gap-2 mt-2">
            <button onClick={saveEdit} disabled={busy} data-testid={`pick-save-${key}`} className="inline-flex items-center gap-1 bg-[#EA4E1B] text-white text-sm font-bold px-3 py-1.5 rounded"><Save className="w-4 h-4" /> Salva dati</button>
            <button onClick={() => setEditing(false)} className="inline-flex items-center gap-1 text-[#6b5d52] text-sm px-3 py-1.5"><X className="w-4 h-4" /> Annulla</button>
          </div>
        </div>
      )}

      {g && (
        <div className="grid sm:grid-cols-3 gap-4 mt-4">
          {FORMATS.map((f) => {
            const data = g.formats && g.formats[f.key];
            const err = g.errors && g.errors[f.key];
            return (
              <div key={f.key} className="border border-[#f0e7da] rounded-lg p-2" data-testid={`fmt-${f.key}-${key}`}>
                <p className="text-xs font-semibold text-[#6b5d52] mb-1">{f.label}</p>
                {data ? (
                  <>
                    <img src={`${data.webp}?t=${bust}`} alt={f.label} className="w-full rounded border border-[#ecdfce] bg-[#14100e]" />
                    <div className="flex items-center gap-2 mt-2 flex-wrap">
                      <a href={`${data.png}?t=${bust}`} target="_blank" rel="noopener noreferrer" download className="inline-flex items-center gap-1 text-xs font-semibold text-[#1a1411] hover:text-[#EA4E1B]"><Download className="w-3.5 h-3.5" /> PNG</a>
                      <a href={`${data.webp}?t=${bust}`} target="_blank" rel="noopener noreferrer" download className="inline-flex items-center gap-1 text-xs font-semibold text-[#1a1411] hover:text-[#EA4E1B]"><Download className="w-3.5 h-3.5" /> WebP</a>
                      <button onClick={() => copy(data.png)} className="inline-flex items-center gap-1 text-xs font-semibold text-[#1a1411] hover:text-[#EA4E1B]"><Link2 className="w-3.5 h-3.5" /> URL</button>
                    </div>
                  </>
                ) : (
                  <div className="text-xs text-red-600 py-6 text-center">{err ? "Errore di rendering" : "Non generato"}<br />
                    <button onClick={generate} className="mt-1 text-[#EA4E1B] font-semibold">Riprova</button></div>
                )}
              </div>
            );
          })}
        </div>
      )}
      {msg && <p className="text-xs text-[#4a3d34] mt-3 break-all" data-testid={`pick-msg-${key}`}>{msg}</p>}
    </div>
  );
}

function CoverCard({ pred, onChanged }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [bust, setBust] = useState(Date.now());
  const fileRef = useRef(null);
  const cover = pred.cover || {};
  const fmts = cover.formats || {};
  const hor = fmts.horizontal || {};
  const sq = fmts.square || {};
  const tb = fmts.thumb || {};
  const isManual = cover.source === "manual";
  const hasErr = cover.errors && Object.keys(cover.errors).length > 0;
  const kb = (b) => (b ? (b / 1024).toFixed(0) + " KB" : "");

  const gen = async (force) => {
    setBusy(true); setMsg("");
    try {
      const r = await api.coverGenerate({ season: pred.season, round: pred.round, force: !!force });
      setBust(Date.now());
      setMsg(
        r.skipped === "manual" ? "Copertina manuale presente: usa «Ripristina automatica» per sostituirla." :
        r.skipped === "unchanged" ? "Nessuna modifica: copertina già aggiornata (idempotente)." :
        r.ok ? "Copertina generata." : "Errore: " + JSON.stringify(r.errors || r.error)
      );
      onChanged && onChanged();
    } catch (e) { setMsg("Errore: " + e.message); }
    finally { setBusy(false); }
  };

  const revert = async () => {
    if (isManual && !window.confirm("Sostituire la copertina manuale con quella automatica?")) return;
    setBusy(true); setMsg("");
    try {
      const r = await api.coverRevert({ season: pred.season, round: pred.round });
      setBust(Date.now());
      setMsg(r.ok ? "Copertina automatica ripristinata." : "Errore.");
      onChanged && onChanged();
    } catch (e) { setMsg("Errore: " + e.message); }
    finally { setBusy(false); }
  };

  const onManualPick = async (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    if (cover.source && !window.confirm("Caricare una copertina manuale? Sostituirà quella attuale e non verrà più rigenerata automaticamente.")) {
      e.target.value = ""; return;
    }
    setBusy(true); setMsg("");
    try {
      await api.coverManual(pred.season, pred.round, f);
      setBust(Date.now());
      setMsg("Copertina manuale caricata.");
      onChanged && onChanged();
    } catch (err) { setMsg("Errore: " + err.message); }
    finally { setBusy(false); e.target.value = ""; }
  };

  return (
    <div className="bg-white rounded-xl border border-[#ecdfce] p-4 mb-4" data-testid={`cover-card-${pred.season}-${pred.round}`}>
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <ImageIcon className="w-5 h-5 text-[#EA4E1B]" />
          <h3 className="font-archivo font-extrabold text-[#1a1411]">Copertina pronostico</h3>
          {cover.source && <span data-testid={`cover-source-${pred.season}-${pred.round}`} className={`text-xs font-bold px-2 py-1 rounded-full ${isManual ? "bg-violet-100 text-violet-700" : "bg-emerald-100 text-emerald-700"}`}>{isManual ? "Manuale" : "Automatica"}</span>}
          {hasErr && <span className="text-xs font-bold px-2 py-1 rounded-full bg-red-100 text-red-700 inline-flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> Errore parziale</span>}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button onClick={() => gen(false)} disabled={busy} data-testid={`cover-generate-${pred.season}-${pred.round}`}
            className="inline-flex items-center gap-2 bg-[#14100e] hover:bg-[#EA4E1B] text-white text-sm font-bold uppercase tracking-wide px-3 py-2 rounded-lg disabled:opacity-60">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <ImagePlus className="w-4 h-4" />} {cover.source ? "Genera" : "Genera copertina"}
          </button>
          <button onClick={() => gen(true)} disabled={busy} data-testid={`cover-regen-${pred.season}-${pred.round}`}
            className="inline-flex items-center gap-2 border border-[#ecdfce] hover:border-[#EA4E1B] text-[#1a1411] text-sm font-bold px-3 py-2 rounded-lg disabled:opacity-60">
            <RefreshCw className="w-4 h-4" /> Rigenera
          </button>
          <button onClick={() => fileRef.current && fileRef.current.click()} disabled={busy} data-testid={`cover-manual-${pred.season}-${pred.round}`}
            className="inline-flex items-center gap-2 border border-[#ecdfce] hover:border-[#EA4E1B] text-[#1a1411] text-sm font-bold px-3 py-2 rounded-lg disabled:opacity-60">
            <Upload className="w-4 h-4" /> Usa immagine manuale
          </button>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onManualPick} />
          {isManual && (
            <button onClick={revert} disabled={busy} data-testid={`cover-revert-${pred.season}-${pred.round}`}
              className="inline-flex items-center gap-2 border border-[#ecdfce] hover:border-[#EA4E1B] text-[#1a1411] text-sm font-bold px-3 py-2 rounded-lg disabled:opacity-60">
              <RotateCcw className="w-4 h-4" /> Ripristina automatica
            </button>
          )}
        </div>
      </div>

      {(hor.url || sq.url) ? (
        <div className="grid sm:grid-cols-3 gap-4 mt-4">
          {hor.url && (
            <div className="border border-[#f0e7da] rounded-lg p-2" data-testid={`cover-horizontal-${pred.season}-${pred.round}`}>
              <p className="text-xs font-semibold text-[#6b5d52] mb-1">1200×675 · OG / pagina / archivio</p>
              <img src={`${hor.url}?t=${bust}`} alt="Copertina orizzontale" className="w-full rounded border border-[#ecdfce] bg-[#14100e]" />
              <p className="text-[11px] text-[#9c8b7d] mt-1">{hor.format || "webp"} · {hor.w}×{hor.h}{hor.bytes ? " · " + kb(hor.bytes) : ""}</p>
            </div>
          )}
          {sq.url && (
            <div className="border border-[#f0e7da] rounded-lg p-2" data-testid={`cover-square-${pred.season}-${pred.round}`}>
              <p className="text-xs font-semibold text-[#6b5d52] mb-1">1200×1200 · social</p>
              <img src={`${sq.url}?t=${bust}`} alt="Copertina quadrata" className="w-full rounded border border-[#ecdfce] bg-[#14100e]" />
              <p className="text-[11px] text-[#9c8b7d] mt-1">{sq.format || "webp"} · {sq.w}×{sq.h}{sq.bytes ? " · " + kb(sq.bytes) : ""}</p>
            </div>
          )}
          {tb.url && (
            <div className="border border-[#f0e7da] rounded-lg p-2" data-testid={`cover-thumb-${pred.season}-${pred.round}`}>
              <p className="text-xs font-semibold text-[#6b5d52] mb-1">600×338 · miniatura card</p>
              <img src={`${tb.url}?t=${bust}`} alt="Miniatura card" className="w-full rounded border border-[#ecdfce] bg-[#14100e]" />
              <p className="text-[11px] text-[#9c8b7d] mt-1">{tb.format || "webp"} · {tb.w}×{tb.h}{tb.bytes ? " · " + kb(tb.bytes) : ""}</p>
            </div>
          )}
        </div>
      ) : (
        <p className="text-sm text-[#9c8b7d] mt-3">Nessuna copertina generata. Viene creata automaticamente alla pubblicazione di una giornata valida, oppure manualmente da qui.</p>
      )}

      {cover.generated_at && <p className="text-[11px] text-[#9c8b7d] mt-3">Generata: {new Date(cover.generated_at).toLocaleString("it-IT")}{cover.template_version ? " · template v" + cover.template_version : ""}{cover.content_hash ? " · hash " + cover.content_hash : ""}</p>}
      {msg && <p className="text-xs text-[#4a3d34] mt-2 break-all" data-testid={`cover-msg-${pred.season}-${pred.round}`}>{msg}</p>}
    </div>
  );
}

export default function Graphics() {
  const [preds, setPreds] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try { setPreds(await api.adminPredictions()); } catch (e) {}
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  return (
    <div data-testid="graphics-page">
      <div className="flex items-center gap-2">
        <ImageIcon className="w-6 h-6 text-[#EA4E1B]" />
        <h1 className="font-anton text-3xl text-[#1a1411]">Grafiche pronostici</h1>
      </div>
      <p className="text-[#6b5d52] mt-1">Genera le grafiche social (orizzontale, quadrato, 9:16) da dati reali. Nessun dato sensibile nelle immagini.</p>

      <div className="mt-6"><LiveCard /></div>

      <div className="mt-8 space-y-8">
        {loading && preds.length === 0 && <p className="text-[#9c8b7d]">Caricamento...</p>}
        {!loading && preds.length === 0 && <p className="text-[#9c8b7d]">Nessun pronostico disponibile.</p>}
        {preds.map((p) => (
          <div key={`${p.season}-${p.round}`} data-testid={`pred-${p.season}-${p.round}`}>
            <h2 className="font-archivo font-extrabold text-[#1a1411] text-lg mb-3">{p.competition || "Serie A"} · {p.season} · {p.round}ª giornata</h2>
            <CoverCard pred={p} onChanged={load} />
            <div className="space-y-4">
              {(p.picks || []).map((pick, i) => (
                <PickCard key={i} pred={p} pick={pick} idx={i} onChanged={load} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
