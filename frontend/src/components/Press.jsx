import React from "react";
import { Newspaper, ArrowUpRight } from "lucide-react";
import { press } from "../mock";
import Reveal from "./Reveal";

export default function Press() {
  return (
    <section id="press" className="section-anchor bg-[#f4ebe1] py-20 lg:py-28">
      <div className="max-w-7xl mx-auto px-5 lg:px-8">
        <Reveal className="text-center max-w-2xl mx-auto">
          <span className="inline-flex items-center gap-2 text-[#EA4E1B] font-bold uppercase tracking-[0.25em] text-xs">
            <Newspaper className="w-4 h-4" /> Rassegna Stampa
          </span>
          <h2 className="font-anton text-[#1a1411] text-4xl sm:text-5xl lg:text-6xl mt-3 leading-none">
            Parlano di Noi
          </h2>
          <p className="text-[#6b5d52] text-base sm:text-lg mt-4">
            Le nostre interviste e i nostri contenuti ripresi dalle principali
            testate sportive.
          </p>
        </Reveal>

        <div className="grid md:grid-cols-3 gap-7 mt-14">
          {press.map((p, i) => (
            <Reveal key={p.id} delay={i * 100}>
              <a
                href={p.url}
                target="_blank"
                rel="noopener noreferrer"
                className="lift group block h-full bg-white rounded-2xl border border-[#ecdfce] p-7 shadow-sm hover:shadow-xl hover:border-[#EA4E1B]/40"
              >
                <div className="flex items-center justify-between">
                  <span className="font-anton text-[#EA4E1B] text-xl uppercase">
                    {p.source}
                  </span>
                  <span className="w-9 h-9 rounded-full bg-[#fbf7f2] flex items-center justify-center text-[#1a1411] group-hover:bg-[#EA4E1B] group-hover:text-white transition-colors">
                    <ArrowUpRight className="w-5 h-5" />
                  </span>
                </div>
                <span className="block text-xs text-[#9c8b7d] font-semibold mt-3">
                  {p.date}
                </span>
                <h3 className="font-archivo font-extrabold text-[#1a1411] text-lg leading-snug mt-2">
                  {p.title}
                </h3>
                <p className="text-[#6b5d52] text-sm leading-relaxed mt-3">
                  {p.excerpt}
                </p>
                <span className="mt-5 inline-flex items-center gap-2 text-[#EA4E1B] font-bold uppercase tracking-wide text-sm">
                  Leggi l'articolo
                </span>
              </a>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
