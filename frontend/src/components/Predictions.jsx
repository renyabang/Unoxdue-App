import React from "react";
import { ShieldAlert, TrendingUp, Download } from "lucide-react";
import { predictions, predictionsMeta, brand } from "../mock";
import Reveal from "./Reveal";

function SlipCard({ p }) {
  return (
    <article className="lift bg-white rounded-2xl overflow-hidden border border-white/10 shadow-xl flex flex-col">
      {/* header */}
      <div className="bg-[#14100e] px-5 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img
            src={p.photo}
            alt={p.tipster}
            className="w-11 h-11 rounded-full object-cover object-top ring-2 ring-[#EA4E1B]"
          />
          <div>
            <p className="text-white font-archivo font-extrabold leading-tight">
              {p.tipster}
            </p>
            <p className="text-[#EA4E1B] text-xs font-bold uppercase tracking-wide">
              {p.type} ({p.selections.length})
            </p>
          </div>
        </div>
        <span className="text-[10px] font-bold uppercase tracking-wide text-[#14100e] bg-[#F6D9BF] px-2.5 py-1 rounded-full">
          {p.status}
        </span>
      </div>

      {/* selections */}
      <div className="flex-1 divide-y divide-[#efe4d6]">
        {p.selections.map((s, idx) => (
          <div key={idx} className="px-5 py-3.5">
            <p className="text-[11px] text-[#9c8b7d] font-semibold uppercase tracking-wide">
              {s.competition} · {s.date}
            </p>
            <p className="font-archivo font-extrabold text-[#1a1411] mt-0.5">
              {s.match}
            </p>
            <div className="flex items-center justify-between mt-1.5">
              <span className="text-sm text-[#6b5d52]">{s.market}</span>
              <span className="inline-flex items-center gap-2">
                <span className="text-sm font-semibold text-[#1a1411]">
                  {s.pick}
                </span>
                <span className="text-sm font-bold text-white bg-[#EA4E1B] px-2 py-0.5 rounded-md tabular-nums">
                  {s.odds}
                </span>
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* footer */}
      <div className="bg-[#fbf7f2] border-t border-[#efe4d6] px-5 py-4 flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-wide text-[#6b5d52]">
          Quota totale
        </span>
        <span className="font-anton text-[#EA4E1B] text-2xl tabular-nums">
          {p.totalOdds}
        </span>
      </div>
    </article>
  );
}

export default function Predictions() {
  return (
    <section
      id="pronostici"
      className="section-anchor relative bg-[#14100e] py-20 lg:py-28 overflow-hidden"
    >
      <div className="pointer-events-none absolute -bottom-32 right-0 w-[30rem] h-[30rem] rounded-full bg-[#EA4E1B]/10 blur-[120px]" />
      <div className="relative max-w-7xl mx-auto px-5 lg:px-8">
        <Reveal className="text-center max-w-2xl mx-auto">
          <span className="inline-flex items-center gap-2 text-[#EA4E1B] font-bold uppercase tracking-[0.25em] text-xs">
            <TrendingUp className="w-4 h-4" /> Pronostici
          </span>
          <h2 className="font-anton text-white text-4xl sm:text-5xl lg:text-6xl mt-3 leading-none">
            Le giocate del team
          </h2>
          <div className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-[#F6D9BF] bg-white/5 border border-white/10 rounded-full px-4 py-1.5">
            <img src={brand.logo} alt="" className="w-5 h-5 rounded-full" />
            {predictionsMeta.competition} · {predictionsMeta.season} ·{" "}
            {predictionsMeta.round}ª giornata
          </div>
          <p className="text-white/60 text-base sm:text-lg mt-4">
            {predictionsMeta.intro}
          </p>
        </Reveal>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-7 mt-14 items-start">
          {predictions.map((p, i) => (
            <Reveal key={p.id} delay={i * 100}>
              <SlipCard p={p} />
            </Reveal>
          ))}
        </div>

        {/* compliance */}
        <Reveal className="mt-12 max-w-3xl mx-auto">
          <div className="flex items-start gap-3 bg-white/[0.04] border border-white/10 rounded-2xl px-5 py-4">
            <ShieldAlert className="w-5 h-5 text-[#EA4E1B] flex-shrink-0 mt-0.5" />
            <p className="text-white/55 text-sm leading-relaxed">
              <span className="font-bold text-white/80">18+ · Gioca responsabilmente.</span>{" "}
              I pronostici di UnoXdue sono opinioni editoriali a scopo di
              intrattenimento e non garantiscono alcun risultato. Le quote sono
              indicative al momento della pubblicazione e possono variare.
            </p>
          </div>
          <p className="text-center text-white/35 text-xs mt-5 inline-flex items-center gap-2 justify-center w-full">
            <Download className="w-3.5 h-3.5" /> Grafiche condivisibili delle
            giocate in arrivo con il pannello di gestione.
          </p>
        </Reveal>
      </div>
    </section>
  );
}
