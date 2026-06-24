import React, { useState } from "react";
import { Play, Mic } from "lucide-react";
import { interviews } from "../mock";
import Reveal from "./Reveal";

function Thumb({ id, alt }) {
  const [src, setSrc] = useState(
    `https://img.youtube.com/vi/${id}/maxresdefault.jpg`
  );
  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      onError={() => setSrc(`https://img.youtube.com/vi/${id}/hqdefault.jpg`)}
      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
    />
  );
}

export default function Interviews({ onPlay }) {
  return (
    <section
      id="interviste"
      className="section-anchor relative bg-[#14100e] py-20 lg:py-28 overflow-hidden"
    >
      <div className="pointer-events-none absolute top-0 right-0 w-[30rem] h-[30rem] rounded-full bg-[#EA4E1B]/10 blur-[120px]" />
      <div className="relative max-w-7xl mx-auto px-5 lg:px-8">
        <Reveal className="text-center max-w-2xl mx-auto">
          <span className="inline-flex items-center gap-2 text-[#EA4E1B] font-bold uppercase tracking-[0.25em] text-xs">
            <Mic className="w-4 h-4" /> UnoXdue Intervista
          </span>
          <h2 className="font-anton text-white text-4xl sm:text-5xl lg:text-6xl mt-3 leading-none">
            Le Voci del Calcio
          </h2>
          <p className="text-white/60 text-base sm:text-lg mt-4">
            Interviste esclusive ai protagonisti del calcio italiano. Storie,
            carriere e ricordi raccontati senza filtri.
          </p>
        </Reveal>

        <div className="grid md:grid-cols-2 gap-7 mt-14">
          {interviews.map((it, i) => (
            <Reveal key={it.id} delay={i * 110}>
              <article className="lift group bg-white/[0.03] border border-white/10 rounded-3xl overflow-hidden hover:border-[#EA4E1B]/50">
                <button
                  onClick={() => onPlay(it)}
                  className="relative block w-full aspect-video overflow-hidden"
                  aria-label={`Guarda l'intervista a ${it.player}`}
                >
                  <Thumb id={it.youtubeId} alt={it.title} />
                  <span className="absolute inset-0 bg-gradient-to-t from-[#14100e] via-transparent to-transparent" />
                  <span className="absolute inset-0 flex items-center justify-center">
                    <span className="w-16 h-16 rounded-full bg-[#EA4E1B] flex items-center justify-center shadow-lg transition-transform group-hover:scale-110">
                      <Play className="w-7 h-7 text-white ml-1" fill="currentColor" />
                    </span>
                  </span>
                  <span className="absolute bottom-3 left-3 flex flex-wrap gap-2">
                    {it.tags.map((t) => (
                      <span
                        key={t}
                        className="text-[10px] font-bold uppercase tracking-wide bg-black/55 text-white px-2.5 py-1 rounded-full backdrop-blur-sm"
                      >
                        {t}
                      </span>
                    ))}
                  </span>
                </button>

                <div className="p-6">
                  <div className="flex items-center gap-2 text-[#EA4E1B] text-xs font-bold uppercase tracking-wide">
                    <span>{it.player}</span>
                    <span className="w-1 h-1 rounded-full bg-[#EA4E1B]" />
                    <span className="text-white/50">{it.role}</span>
                  </div>
                  <h3 className="font-archivo font-extrabold text-white text-xl mt-2 leading-snug">
                    {it.title}
                  </h3>
                  <p className="text-white/55 text-sm leading-relaxed mt-3">
                    {it.excerpt}
                  </p>
                  <button
                    onClick={() => onPlay(it)}
                    className="mt-5 inline-flex items-center gap-2 text-white font-bold uppercase tracking-wide text-sm hover:text-[#EA4E1B] transition-colors"
                  >
                    <Play className="w-4 h-4" fill="currentColor" />
                    Guarda l'intervista
                  </button>
                </div>
              </article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
