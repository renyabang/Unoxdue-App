import React, { useState } from "react";
import Reveal from "./Reveal";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function NewsletterBand() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("idle"); // idle | sending | ok | already | error
  const [msg, setMsg] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setStatus("sending");
    setMsg("Invio…");
    try {
      const r = await fetch(`${API}/newsletter/subscribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, source: "home" }),
      });
      const j = await r.json();
      if (j.ok) {
        setStatus(j.already ? "already" : "ok");
        setMsg(j.already ? "Sei già iscritto, grazie!" : "Iscrizione confermata. Grazie!");
        setEmail("");
      } else {
        setStatus("error");
        setMsg(j.error || "Errore, riprova.");
      }
    } catch {
      setStatus("error");
      setMsg("Errore di rete, riprova.");
    }
  };

  const msgColor =
    status === "ok" || status === "already"
      ? "text-[#7ee2a8]"
      : status === "error"
      ? "text-[#ffb199]"
      : "text-white/70";

  return (
    <section
      className="relative overflow-hidden bg-[#14100e]"
      data-testid="newsletter-band"
    >
      <div className="pointer-events-none absolute -top-24 -right-16 w-[26rem] h-[26rem] rounded-full bg-[#EA4E1B]/30 blur-[120px]" />
      <div className="relative max-w-7xl mx-auto px-5 lg:px-8 py-16 lg:py-20 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-10">
        <Reveal className="max-w-xl">
          <span className="text-[#EA4E1B] font-bold uppercase tracking-[0.25em] text-xs">
            Newsletter UnoXdue
          </span>
          <h2 className="font-anton text-white text-4xl sm:text-5xl mt-3 leading-[0.95]">
            Non perderti la prossima puntata.
          </h2>
          <p className="text-white/60 text-base sm:text-lg mt-4">
            Nuove puntate, dirette su Twitch e pronostici — direttamente nella
            tua email. Niente spam.
          </p>
        </Reveal>

        <Reveal delay={120} className="w-full lg:w-auto lg:min-w-[420px]">
          <form
            onSubmit={submit}
            className="flex flex-col sm:flex-row gap-3"
            data-testid="newsletter-band-form"
          >
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="La tua email"
              data-testid="newsletter-band-email"
              className="flex-1 min-w-0 rounded-xl border border-white/20 bg-white/5 px-4 py-3.5 text-white placeholder-white/40 text-[15px] outline-none focus:border-[#EA4E1B] transition-colors"
            />
            <button
              type="submit"
              disabled={status === "sending"}
              data-testid="newsletter-band-submit"
              className="rounded-xl bg-[#EA4E1B] hover:bg-[#d3430f] disabled:opacity-70 text-white font-archivo font-extrabold uppercase tracking-wide text-sm px-7 py-3.5 whitespace-nowrap transition-colors"
            >
              Iscriviti
            </button>
          </form>
          {msg && (
            <p
              className={`mt-3 text-sm font-semibold ${msgColor}`}
              data-testid="newsletter-band-msg"
            >
              {msg}
            </p>
          )}
          <p className="text-white/35 text-xs mt-3">
            Iscrivendoti accetti la{" "}
            <a href="/privacy/" className="underline hover:text-white/60">
              privacy policy
            </a>
            . Puoi disiscriverti quando vuoi.
          </p>
        </Reveal>
      </div>
    </section>
  );
}
