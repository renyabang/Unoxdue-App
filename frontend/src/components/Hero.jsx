import React from "react";
import { Twitch, Youtube, Instagram, Play } from "lucide-react";
import { TikTokIcon } from "./icons";
import { brand, socials } from "../mock";

const iconFor = (key) => {
  if (key === "twitch") return Twitch;
  if (key === "youtube") return Youtube;
  if (key === "instagram") return Instagram;
  return null;
};

export default function Hero() {
  return (
    <section
      id="home"
      className="section-anchor relative overflow-hidden bg-[#14100e] pt-32 pb-0"
    >
      {/* glow decor */}
      <div className="pointer-events-none absolute -top-32 -right-24 w-[36rem] h-[36rem] rounded-full bg-[#EA4E1B]/20 blur-[120px]" />
      <div className="pointer-events-none absolute -bottom-40 -left-24 w-[34rem] h-[34rem] rounded-full bg-[#EA4E1B]/10 blur-[120px]" />

      <div className="relative max-w-7xl mx-auto px-5 lg:px-8 grid lg:grid-cols-2 gap-10 items-center pb-16">
        <div className="text-center lg:text-left">
          <span className="inline-flex items-center gap-2 rounded-full border border-[#EA4E1B]/40 bg-[#EA4E1B]/10 px-4 py-1.5 text-[#F6D9BF] text-xs font-bold uppercase tracking-[0.2em]">
            {brand.tagline}
          </span>

          <h1 className="font-anton text-white text-6xl sm:text-7xl lg:text-8xl leading-[0.92] mt-6">
            Uno<span className="text-[#EA4E1B]">X</span>due
          </h1>
          <p className="font-archivo font-extrabold uppercase tracking-wide text-white/90 text-xl sm:text-2xl mt-3">
            {brand.title}
          </p>
          <p className="text-white/65 text-base sm:text-lg leading-relaxed mt-5 max-w-xl mx-auto lg:mx-0">
            {brand.description}
          </p>

          <div className="flex flex-col sm:flex-row gap-4 mt-8 justify-center lg:justify-start">
            <a
              href="https://www.twitch.tv/unoxdue_"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 bg-[#EA4E1B] hover:bg-[#d3430f] text-white font-bold uppercase tracking-wide px-7 py-3.5 rounded-full transition-all hover:scale-[1.03]"
            >
              <Play className="w-5 h-5" fill="currentColor" />
              Ascolta su Twitch
            </a>
            <a
              href="https://www.youtube.com/@unoXdue"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 border border-white/25 hover:border-white/60 text-white font-bold uppercase tracking-wide px-7 py-3.5 rounded-full transition-all"
            >
              <Youtube className="w-5 h-5" />
              Segui su YouTube
            </a>
          </div>

          <div className="flex items-center gap-3 mt-9 justify-center lg:justify-start">
            {socials.map((s) => {
              const Icon = iconFor(s.key);
              return (
                <a
                  key={s.key}
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={s.label}
                  className="w-11 h-11 rounded-full border border-white/15 flex items-center justify-center text-white/80 hover:text-white hover:border-[#EA4E1B] hover:bg-[#EA4E1B] transition-all"
                >
                  {Icon ? (
                    <Icon className="w-5 h-5" />
                  ) : (
                    <TikTokIcon size={18} />
                  )}
                </a>
              );
            })}
          </div>
        </div>

        {/* Logo visual */}
        <div className="flex justify-center lg:justify-end">
          <div className="relative animate-floaty">
            <div className="absolute inset-0 rounded-full bg-[#EA4E1B]/30 blur-3xl scale-110" />
            <img
              src={brand.logo}
              alt="UnoXdue podcast logo"
              className="relative w-64 h-64 sm:w-80 sm:h-80 lg:w-[26rem] lg:h-[26rem] rounded-full object-cover ring-4 ring-[#EA4E1B]/30 shadow-2xl"
            />
          </div>
        </div>
      </div>

      {/* Marquee strip */}
      <div className="relative border-y border-white/10 bg-[#EA4E1B] overflow-hidden">
        <div className="flex whitespace-nowrap animate-marquee py-3">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="flex items-center">
              {[
                "SERIE A",
                "PRONOSTICI",
                "ANALISI TATTICA",
                "DIBATTITO",
                "INTERVISTE",
                "DIRETTE LIVE",
              ].map((w, j) => (
                <span
                  key={j}
                  className="font-anton text-[#14100e] text-lg uppercase tracking-wide mx-6"
                >
                  {w} <span className="mx-3">&#9679;</span>
                </span>
              ))}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
