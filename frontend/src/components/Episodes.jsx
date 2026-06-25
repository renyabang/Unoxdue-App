import React, { useState } from "react";
import { Play, ExternalLink, Clock, Youtube, Twitch } from "lucide-react";
import { TikTokIcon } from "./icons";
import { episodes } from "../mock";
import Reveal from "./Reveal";

const platformMeta = {
  YouTube: { color: "#FF0000", Icon: Youtube },
  Twitch: { color: "#9146FF", Icon: Twitch },
  TikTok: { color: "#111111", Icon: null },
};

function YtThumb({ id, alt }) {
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

export default function Episodes({ onPlay }) {
  return (
    <section id="episodi" className="section-anchor bg-[#f4ebe1] py-20 lg:py-28">
      <div className="max-w-7xl mx-auto px-5 lg:px-8">
        <Reveal className="text-center max-w-2xl mx-auto">
          <span className="text-[#EA4E1B] font-bold uppercase tracking-[0.25em] text-xs">
            Contenuti recenti
          </span>
          <h2 className="font-anton text-[#1a1411] text-4xl sm:text-5xl lg:text-6xl mt-3 leading-none">
            Ultimi contenuti
          </h2>
          <p className="text-[#6b5d52] text-base sm:text-lg mt-4">
            Rimani aggiornato con i nostri ultimi episodi e clip su tutte le
            piattaforme.
          </p>
        </Reveal>

        <div className="grid md:grid-cols-3 gap-7 mt-14">
          {episodes.map((ep, i) => {
            const meta = platformMeta[ep.platform] || {};
            const Icon = meta.Icon;
            const isYt = ep.type === "youtube";
            return (
              <Reveal key={ep.id} delay={i * 90}>
                <article className="lift group h-full bg-white rounded-2xl border border-[#ecdfce] overflow-hidden shadow-sm hover:shadow-xl hover:border-[#EA4E1B]/40 flex flex-col">
                  <div className="relative aspect-video overflow-hidden bg-[#14100e]">
                    {isYt ? (
                      <button
                        onClick={() => onPlay(ep)}
                        className="absolute inset-0 w-full h-full"
                        aria-label={`Guarda ${ep.title}`}
                      >
                        <YtThumb id={ep.youtubeId} alt={ep.title} />
                        <span className="absolute inset-0 flex items-center justify-center">
                          <span className="w-14 h-14 rounded-full bg-[#EA4E1B] flex items-center justify-center shadow-lg transition-transform group-hover:scale-110">
                            <Play
                              className="w-6 h-6 text-white ml-0.5"
                              fill="currentColor"
                            />
                          </span>
                        </span>
                      </button>
                    ) : (
                      <a
                        href={ep.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="absolute inset-0 flex items-center justify-center"
                        style={{ backgroundColor: meta.color }}
                        aria-label={`Apri ${ep.title}`}
                      >
                        {Icon ? (
                          <Icon className="w-12 h-12 text-white/90" />
                        ) : (
                          <TikTokIcon size={44} className="text-white/90" />
                        )}
                      </a>
                    )}
                    <span
                      className="absolute top-3 left-3 inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-white px-2.5 py-1 rounded-full"
                      style={{ backgroundColor: meta.color }}
                    >
                      {Icon ? <Icon className="w-3.5 h-3.5" /> : <TikTokIcon size={13} />}
                      {ep.platform}
                    </span>
                    <span className="absolute bottom-3 right-3 inline-flex items-center gap-1 text-[11px] font-semibold text-white bg-black/60 px-2 py-1 rounded-md backdrop-blur-sm">
                      <Clock className="w-3 h-3" />
                      {ep.duration}
                    </span>
                  </div>

                  <div className="p-5 flex flex-col flex-1">
                    <span className="text-xs text-[#9c8b7d] font-semibold">
                      {ep.date}
                    </span>
                    <h3 className="font-archivo font-extrabold text-[#1a1411] text-lg mt-1.5 leading-snug">
                      {ep.title}
                    </h3>
                    <p className="text-[#6b5d52] text-sm leading-relaxed mt-2 flex-1">
                      {ep.text}
                    </p>
                    {isYt ? (
                      <button
                        onClick={() => onPlay(ep)}
                        className="mt-4 inline-flex items-center gap-2 text-[#EA4E1B] font-bold uppercase tracking-wide text-sm hover:gap-3 transition-all"
                      >
                        <Play className="w-4 h-4" fill="currentColor" /> Guarda ora
                      </button>
                    ) : (
                      <a
                        href={ep.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-4 inline-flex items-center gap-2 text-[#EA4E1B] font-bold uppercase tracking-wide text-sm hover:gap-3 transition-all"
                      >
                        Apri su {ep.platform} <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                  </div>
                </article>
              </Reveal>
            );
          })}
        </div>

        <Reveal className="text-center mt-12">
          <a
            href="https://www.youtube.com/@unoXdue"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 bg-[#1a1411] hover:bg-[#EA4E1B] text-white font-bold uppercase tracking-wide px-7 py-3.5 rounded-full transition-colors"
          >
            <Youtube className="w-5 h-5" /> Vedi tutti i contenuti
          </a>
        </Reveal>
      </div>
    </section>
  );
}
