import React, { useEffect, useState } from "react";
import {
  Send, CheckCircle2, XCircle, Loader2, RefreshCw, Eye, Radio, Ticket,
  MessageSquare, BarChart3, Save, Plus, Trash2, ShieldCheck, ShieldAlert,
} from "lucide-react";
import { api } from "./api";

const PLACEHOLDERS = {
  episode: "{title} {excerpt} {url} {youtube}",
  live: "{text} {twitch}",
  prediction: "{tipster} {competition} {round} {selections} {total_odds} {url}",
};

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
      <span>
        <span className="block text-sm font-semibold text-[#1a1411]">{label}</span>
        {hint && <span className="block text-xs text-[#8a7a6c]">{hint}</span>}
      </span>
    </label>
  );
}

function Preview({ data }) {
  if (!data) return null;
  if (!data.ok) return <p className="mt-3 text-sm text-red-600" data-testid="tg-preview-error">{data.error}</p>;
  return (
    <div className="mt-3 rounded-xl bg-[#e7f0f7] border border-[#cfe0ee] p-3 max-w-md" data-testid="tg-preview-box">
      {data.photo && <img src={data.photo} alt="" className="w-full max-h-52 object-cover rounded-lg mb-2" />}
      <div className="text-sm text-[#0f1b24] whitespace-pre-wrap leading-relaxed"
        dangerouslySetInnerHTML={{ __html: data.text.replace(/</g, "&lt;").replace(/&lt;b&gt;/g, "<b>").replace(/&lt;\/b&gt;/g, "</b>") }} />
    </div>
  );
}

export default function Telegram() {
  const [cfg, setCfg] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [testing, setTesting] = useState(false);
  const [tokenInput, setTokenInput] = useState("");
  const [busy, setBusy] = useState("");

  const [episodes, setEpisodes] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [messages, setMessages] = useState([]);

  const [epSlug, setEpSlug] = useState("");
  const [predKey, setPredKey] = useState("");
  const [pickIdx, setPickIdx] = useState(0);
  const [liveText, setLiveText] = useState("");
  const [pollQ, setPollQ] = useState("");
  const [pollOpts, setPollOpts] = useState(["", ""]);
  const [preview, setPreview] = useState(null);

  const load = async () => {
    const c = await api.tgConfig();
    setCfg(c);
    if (!liveText) setLiveText("");
  };
  const loadLists = async () => {
    try { setEpisodes(await api.episodes()); } catch { /* */ }
    try { setPredictions(await api.adminPredictions()); } catch { /* */ }
    try { setMessages(await api.tgMessages(15)); } catch { /* */ }
  };
  useEffect(() => { load().catch(() => {}); loadLists(); }, []); // eslint-disable-line

  const set = (k, v) => setCfg((c) => ({ ...c, [k]: v }));
  const setTpl = (k, v) => setCfg((c) => ({ ...c, templates: { ...c.templates, [k]: v } }));

  const save = async () => {
    setSaving(true); setSaved(false);
    try {
      const body = {
        channel_id: cfg.channel_id, twitch_url: cfg.twitch_url, enabled: cfg.enabled,
        auto_episode: cfg.auto_episode, auto_prediction: cfg.auto_prediction, templates: cfg.templates,
      };
      if (tokenInput.trim()) body.bot_token = tokenInput.trim();
      const c = await api.tgSaveConfig(body);
      setCfg(c); setTokenInput(""); setSaved(true); setTimeout(() => setSaved(false), 2500);
    } catch (e) { alert(e.message); }
    setSaving(false);
  };

  const test = async () => {
    setTesting(true);
    try { const r = await api.tgTest(); await load(); if (!r.ok) alert("Test fallito: " + (r.error || "")); }
    catch (e) { alert(e.message); }
    setTesting(false);
  };

  const run = async (key, fn, okMsg) => {
    setBusy(key);
    try { const r = await fn(); if (r && r.ok === false) alert("Errore: " + (r.error || "")); else { await loadLists(); if (okMsg) alert(okMsg); } }
    catch (e) { alert(e.message); }
    setBusy("");
  };

  const doPreview = async (params) => {
    setPreview(null);
    try { setPreview(await api.tgPreview(params)); } catch (e) { setPreview({ ok: false, error: e.message }); }
  };

  if (!cfg) return <div className="flex items-center gap-2 text-[#6b5d52]"><Loader2 className="w-4 h-4 animate-spin" /> Caricamento…</div>;

  const st = cfg.status || {};
  const selectedPred = predictions.find((p) => `${p.season}|${p.round}` === predKey);

  return (
    <div data-testid="telegram-admin">
      <h1 className="font-anton text-3xl text-[#1a1411]">Telegram</h1>
      <p className="text-[#6b5d52] mt-1">Pubblica sul canale Telegram nuove puntate, pronostici, avvisi live e sondaggi. Manuale o automatico.</p>

      {/* CONFIG */}
      <Card title="Configurazione bot e canale" icon={Send} testid="tg-config-card">
        <div className="grid md:grid-cols-2 gap-4 max-w-3xl">
          <div className="md:col-span-2">
            <label className="block text-sm font-semibold text-[#1a1411]">Bot Token {cfg.token_set && <span className="text-xs text-green-700">(impostato: {cfg.token_masked})</span>}</label>
            <input type="password" value={tokenInput} onChange={(e) => setTokenInput(e.target.value)} autoComplete="off" spellCheck={false}
              placeholder={cfg.token_set ? "•••••••• (lascia vuoto per non cambiarlo)" : "Incolla qui il token da @BotFather"}
              data-testid="tg-token-input"
              className="mt-1.5 w-full rounded-lg border border-[#e5d8c7] bg-[#fbf7f2] px-3 py-2.5 text-sm text-[#1a1411] focus:outline-none focus:ring-2 focus:ring-[#EA4E1B]/40 focus:border-[#EA4E1B]" />
            <p className="mt-1 text-xs text-[#8a7a6c]">Il token viene salvato lato server e mai più mostrato in chiaro.</p>
          </div>
          <div>
            <label className="block text-sm font-semibold text-[#1a1411]">Canale (ID o @username)</label>
            <input type="text" value={cfg.channel_id || ""} onChange={(e) => set("channel_id", e.target.value)} spellCheck={false}
              placeholder="@unoxdue oppure -1001234567890" data-testid="tg-channel-input"
              className="mt-1.5 w-full rounded-lg border border-[#e5d8c7] bg-[#fbf7f2] px-3 py-2.5 text-sm text-[#1a1411] focus:outline-none focus:ring-2 focus:ring-[#EA4E1B]/40 focus:border-[#EA4E1B]" />
          </div>
          <div>
            <label className="block text-sm font-semibold text-[#1a1411]">Link Twitch (per avviso live)</label>
            <input type="text" value={cfg.twitch_url || ""} onChange={(e) => set("twitch_url", e.target.value)} spellCheck={false}
              placeholder="https://www.twitch.tv/unoxdue_" data-testid="tg-twitch-input"
              className="mt-1.5 w-full rounded-lg border border-[#e5d8c7] bg-[#fbf7f2] px-3 py-2.5 text-sm text-[#1a1411] focus:outline-none focus:ring-2 focus:ring-[#EA4E1B]/40 focus:border-[#EA4E1B]" />
          </div>
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button onClick={save} disabled={saving} data-testid="tg-save-button" className="inline-flex items-center gap-2 bg-[#14100e] hover:bg-[#EA4E1B] text-white text-sm font-bold uppercase tracking-wide px-5 py-2.5 rounded-lg disabled:opacity-60 transition-colors">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Salva
          </button>
          {saved && <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-green-700"><CheckCircle2 className="w-4 h-4" /> Salvato</span>}
          <button onClick={test} disabled={testing} data-testid="tg-test-button" className="inline-flex items-center gap-2 border border-[#e5d8c7] hover:border-[#EA4E1B] text-[#1a1411] text-sm font-bold uppercase tracking-wide px-4 py-2.5 rounded-lg disabled:opacity-60 transition-colors">
            {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />} Testa connessione
          </button>
          <button onClick={() => run("sendtest", () => api.tgSendTest())} disabled={busy === "sendtest"} data-testid="tg-sendtest-button" className="inline-flex items-center gap-2 border border-[#e5d8c7] hover:border-[#EA4E1B] text-[#1a1411] text-sm font-bold uppercase tracking-wide px-4 py-2.5 rounded-lg disabled:opacity-60 transition-colors">
            {busy === "sendtest" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Invia messaggio di prova
          </button>
        </div>

        {st.checked_at && (
          <div className="mt-4 rounded-lg bg-[#fbf7f2] border border-[#ecdfce] p-3 text-sm" data-testid="tg-status-box">
            {st.ok ? (
              <p className="flex items-center gap-1.5 text-green-700 font-semibold"><CheckCircle2 className="w-4 h-4" /> Connessione OK</p>
            ) : (
              <p className="flex items-center gap-1.5 text-red-600 font-semibold"><XCircle className="w-4 h-4" /> {st.error || "Errore"}</p>
            )}
            {st.bot && <p className="text-[#4a3d34] mt-1">Bot: <b>@{st.bot.username}</b> ({st.bot.name})</p>}
            {st.channel && <p className="text-[#4a3d34]">Canale: <b>{st.channel.title}</b> · {st.channel.type}{st.channel.username ? ` · @${st.channel.username}` : ""}</p>}
            {st.channel && (st.can_post
              ? <p className="flex items-center gap-1.5 text-green-700 mt-1"><ShieldCheck className="w-4 h-4" /> Il bot può pubblicare nel canale</p>
              : st.can_post === false
                ? <p className="flex items-center gap-1.5 text-[#c2410c] mt-1"><ShieldAlert className="w-4 h-4" /> Il bot NON ha il permesso "Pubblica messaggi" nel canale</p>
                : null)}
          </div>
        )}
      </Card>

      {/* AUTO */}
      <Card title="Automazioni" icon={CheckCircle2} testid="tg-auto-card">
        <Toggle checked={!!cfg.enabled} onChange={(v) => set("enabled", v)} testid="tg-enabled-toggle"
          label="Pubblicazione attiva" hint="Interruttore generale: se spento, niente invii automatici (i pulsanti manuali funzionano comunque)." />
        <Toggle checked={!!cfg.auto_episode} onChange={(v) => set("auto_episode", v)} testid="tg-auto-episode-toggle"
          label="Auto: nuova puntata pubblicata" hint="Invia al canale quando un episodio/intervista viene pubblicato (una sola volta per contenuto)." />
        <Toggle checked={!!cfg.auto_prediction} onChange={(v) => set("auto_prediction", v)} testid="tg-auto-prediction-toggle"
          label="Auto: nuovo pronostico/schedina" hint="Invia ogni schedina tipster quando il pronostico diventa pubblicato (una sola volta per tipster)." />
        <p className="text-xs text-[#8a7a6c] mt-1">Ricordati di premere <b>Salva</b> in alto dopo aver cambiato gli interruttori.</p>
      </Card>

      {/* TEMPLATES */}
      <Card title="Modelli messaggi (modificabili)" icon={MessageSquare} testid="tg-templates-card">
        {["episode", "prediction", "live"].map((k) => (
          <div key={k} className="mb-4">
            <div className="flex items-center justify-between">
              <label className="block text-sm font-semibold text-[#1a1411] capitalize">{k === "episode" ? "Nuova puntata" : k === "prediction" ? "Pronostico / schedina" : "Avviso live"}</label>
              <button onClick={() => setTpl(k, cfg.default_templates[k])} className="text-xs text-[#EA4E1B] hover:underline">Ripristina default</button>
            </div>
            <textarea value={cfg.templates[k] || ""} onChange={(e) => setTpl(k, e.target.value)} rows={k === "prediction" ? 8 : 6} data-testid={`tg-template-${k}`}
              className="mt-1.5 w-full rounded-lg border border-[#e5d8c7] bg-[#fbf7f2] px-3 py-2.5 text-sm font-mono text-[#1a1411] focus:outline-none focus:ring-2 focus:ring-[#EA4E1B]/40 focus:border-[#EA4E1B]" />
            <p className="mt-1 text-xs text-[#8a7a6c]">Variabili disponibili: <code className="bg-[#fbf7f2] px-1 rounded">{PLACEHOLDERS[k]}</code> · puoi usare <code className="bg-[#fbf7f2] px-1 rounded">&lt;b&gt;grassetto&lt;/b&gt;</code></p>
          </div>
        ))}
        <button onClick={save} disabled={saving} className="inline-flex items-center gap-2 bg-[#14100e] hover:bg-[#EA4E1B] text-white text-sm font-bold uppercase tracking-wide px-5 py-2.5 rounded-lg disabled:opacity-60 transition-colors">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Salva modelli
        </button>
      </Card>

      {/* MANUAL PUBLISH */}
      <Card title="Pubblica manualmente" icon={Send} testid="tg-publish-card">
        {/* Episode */}
        <div className="border-b border-[#f0e7da] pb-4 mb-4">
          <h3 className="font-semibold text-[#1a1411] mb-2 flex items-center gap-1.5"><Send className="w-4 h-4 text-[#EA4E1B]" /> Puntata</h3>
          <div className="flex flex-wrap items-center gap-2">
            <select value={epSlug} onChange={(e) => setEpSlug(e.target.value)} data-testid="tg-episode-select" className="rounded-lg border border-[#e5d8c7] bg-[#fbf7f2] px-3 py-2 text-sm min-w-[260px]">
              <option value="">Scegli un contenuto…</option>
              {episodes.map((e) => <option key={e.slug} value={e.slug}>{e.type === "intervista" ? "🎤 " : "🎙️ "}{e.title} {e.status !== "pubblicato" ? `(${e.status})` : ""}</option>)}
            </select>
            <button disabled={!epSlug} onClick={() => doPreview({ kind: "episode", slug: epSlug })} className="inline-flex items-center gap-1.5 border border-[#e5d8c7] hover:border-[#EA4E1B] text-sm font-semibold px-3 py-2 rounded-lg disabled:opacity-50"><Eye className="w-4 h-4" /> Anteprima</button>
            <button disabled={!epSlug || busy === "ep"} onClick={() => run("ep", () => api.tgPublishEpisode(epSlug), "Inviato al canale ✅")} data-testid="tg-publish-episode-button" className="inline-flex items-center gap-1.5 bg-[#EA4E1B] hover:bg-[#d3430f] text-white text-sm font-bold px-4 py-2 rounded-lg disabled:opacity-50">
              {busy === "ep" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Pubblica
            </button>
          </div>
        </div>

        {/* Prediction */}
        <div className="border-b border-[#f0e7da] pb-4 mb-4">
          <h3 className="font-semibold text-[#1a1411] mb-2 flex items-center gap-1.5"><Ticket className="w-4 h-4 text-[#EA4E1B]" /> Pronostico</h3>
          <div className="flex flex-wrap items-center gap-2">
            <select value={predKey} onChange={(e) => { setPredKey(e.target.value); setPickIdx(0); }} data-testid="tg-prediction-select" className="rounded-lg border border-[#e5d8c7] bg-[#fbf7f2] px-3 py-2 text-sm min-w-[220px]">
              <option value="">Scegli giornata…</option>
              {predictions.map((p) => <option key={`${p.season}|${p.round}`} value={`${p.season}|${p.round}`}>{p.season} · Giornata {p.round} {p.status !== "pubblicato" ? `(${p.status})` : ""}</option>)}
            </select>
            {selectedPred && (selectedPred.picks || []).length > 0 && (
              <select value={pickIdx} onChange={(e) => setPickIdx(Number(e.target.value))} data-testid="tg-pick-select" className="rounded-lg border border-[#e5d8c7] bg-[#fbf7f2] px-3 py-2 text-sm">
                {(selectedPred.picks || []).map((pk, i) => <option key={i} value={i}>{pk.tipster || `Giocata ${i + 1}`}</option>)}
              </select>
            )}
            <button disabled={!selectedPred} onClick={() => doPreview({ kind: "prediction", season: selectedPred.season, round: selectedPred.round, pick_index: pickIdx })} className="inline-flex items-center gap-1.5 border border-[#e5d8c7] hover:border-[#EA4E1B] text-sm font-semibold px-3 py-2 rounded-lg disabled:opacity-50"><Eye className="w-4 h-4" /> Anteprima</button>
            <button disabled={!selectedPred || busy === "pred"} onClick={() => run("pred", () => api.tgPublishPrediction(selectedPred.season, selectedPred.round, pickIdx), "Inviato al canale ✅")} data-testid="tg-publish-prediction-button" className="inline-flex items-center gap-1.5 bg-[#EA4E1B] hover:bg-[#d3430f] text-white text-sm font-bold px-4 py-2 rounded-lg disabled:opacity-50">
              {busy === "pred" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Pubblica
            </button>
          </div>
        </div>

        {/* Live */}
        <div className="border-b border-[#f0e7da] pb-4 mb-4">
          <h3 className="font-semibold text-[#1a1411] mb-2 flex items-center gap-1.5"><Radio className="w-4 h-4 text-[#EA4E1B]" /> Avviso LIVE</h3>
          <textarea value={liveText} onChange={(e) => setLiveText(e.target.value)} rows={2} data-testid="tg-live-input" placeholder="Es: Commentiamo in diretta la giornata di Serie A (lascia vuoto per il testo di default)"
            className="w-full rounded-lg border border-[#e5d8c7] bg-[#fbf7f2] px-3 py-2 text-sm" />
          <div className="flex items-center gap-2 mt-2">
            <button onClick={() => doPreview({ kind: "live", text: liveText })} className="inline-flex items-center gap-1.5 border border-[#e5d8c7] hover:border-[#EA4E1B] text-sm font-semibold px-3 py-2 rounded-lg"><Eye className="w-4 h-4" /> Anteprima</button>
            <button disabled={busy === "live"} onClick={() => run("live", () => api.tgPublishLive(liveText), "Avviso live inviato ✅")} data-testid="tg-publish-live-button" className="inline-flex items-center gap-1.5 bg-[#EA4E1B] hover:bg-[#d3430f] text-white text-sm font-bold px-4 py-2 rounded-lg disabled:opacity-50">
              {busy === "live" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Radio className="w-4 h-4" />} Pubblica avviso
            </button>
          </div>
        </div>

        {/* Poll */}
        <div>
          <h3 className="font-semibold text-[#1a1411] mb-2 flex items-center gap-1.5"><BarChart3 className="w-4 h-4 text-[#EA4E1B]" /> Sondaggio</h3>
          <input value={pollQ} onChange={(e) => setPollQ(e.target.value)} data-testid="tg-poll-question" placeholder="Domanda del sondaggio" className="w-full max-w-lg rounded-lg border border-[#e5d8c7] bg-[#fbf7f2] px-3 py-2 text-sm mb-2" />
          {pollOpts.map((o, i) => (
            <div key={i} className="flex items-center gap-2 mb-2 max-w-lg">
              <input value={o} onChange={(e) => setPollOpts((p) => p.map((x, j) => j === i ? e.target.value : x))} data-testid={`tg-poll-opt-${i}`} placeholder={`Opzione ${i + 1}`} className="flex-1 rounded-lg border border-[#e5d8c7] bg-[#fbf7f2] px-3 py-2 text-sm" />
              {pollOpts.length > 2 && <button onClick={() => setPollOpts((p) => p.filter((_, j) => j !== i))} className="text-red-500 p-1"><Trash2 className="w-4 h-4" /></button>}
            </div>
          ))}
          <div className="flex items-center gap-2">
            {pollOpts.length < 10 && <button onClick={() => setPollOpts((p) => [...p, ""])} className="inline-flex items-center gap-1.5 border border-[#e5d8c7] hover:border-[#EA4E1B] text-sm font-semibold px-3 py-2 rounded-lg"><Plus className="w-4 h-4" /> Aggiungi opzione</button>}
            <button disabled={busy === "poll"} onClick={() => run("poll", () => api.tgPublishPoll(pollQ, pollOpts), "Sondaggio inviato ✅")} data-testid="tg-publish-poll-button" className="inline-flex items-center gap-1.5 bg-[#EA4E1B] hover:bg-[#d3430f] text-white text-sm font-bold px-4 py-2 rounded-lg disabled:opacity-50">
              {busy === "poll" ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />} Pubblica sondaggio
            </button>
          </div>
        </div>

        <Preview data={preview} />
      </Card>

      {/* LOG */}
      <Card title="Ultimi invii" icon={MessageSquare} testid="tg-log-card">
        {messages.length === 0 ? <p className="text-sm text-[#8a7a6c]">Nessun invio ancora.</p> : (
          <div className="space-y-2">
            {messages.map((m) => (
              <div key={m.id} className="flex items-start gap-2 text-sm border-b border-[#f0e7da] pb-2">
                {m.ok ? <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 shrink-0" /> : <XCircle className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />}
                <div className="min-w-0">
                  <span className="inline-block text-xs font-bold uppercase text-[#EA4E1B] mr-2">{m.kind}</span>
                  <span className="text-xs text-[#8a7a6c]">{new Date(m.created_at).toLocaleString("it-IT")}</span>
                  <p className="text-[#4a3d34] truncate">{m.error ? <span className="text-red-600">{m.error}</span> : (m.text || "").replace(/<\/?b>/g, "")}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
