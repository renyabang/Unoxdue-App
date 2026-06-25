import React from "react";
import { Instagram, Mic } from "lucide-react";
import { hosts } from "../mock";
import Reveal from "./Reveal";

export default function Hosts() {
  return (
    <section id="team" className="section-anchor bg-[#fbf7f2] py-20 lg:py-28">
      <div className="max-w-7xl mx-auto px-5 lg:px-8">
        <Reveal className="text-center max-w-2xl mx-auto">
          <span className="text-[#EA4E1B] font-bold uppercase tracking-[0.25em] text-xs">
            Il nostro team
          </span>
          <h2 className="font-anton text-[#1a1411] text-4xl sm:text-5xl lg:text-6xl mt-3 leading-none">
            Il team
          </h2>
          <p className="text-[#6b5d52] text-base sm:text-lg mt-4">
            Tre tipster e un host: voci diverse, un'unica passione per il calcio.
          </p>
        </Reveal>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-7 mt-14">
          {hosts.map((h, i) => (
            <Reveal key={h.id} delay={i * 100}>
              <article className="lift group h-full bg-white rounded-3xl overflow-hidden border border-[#ecdfce] shadow-sm hover:shadow-2xl hover:border-[#EA4E1B]/40 flex flex-col">
                <div className="relative aspect-[4/5] overflow-hidden bg-[#14100e]">
                  <img
                    src={h.photo}
                    alt={`${h.nickname} — ${h.role}`}
                    loading="lazy"
                    className="w-full h-full object-cover object-top transition-transform duration-500 group-hover:scale-105"
                  />
                  <span className="absolute inset-0 bg-gradient-to-t from-[#14100e] via-[#14100e]/20 to-transparent" />
                  <span
                    className={`absolute top-4 left-4 inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide px-3 py-1.5 rounded-full ${
                      h.isHost
                        ? "bg-[#14100e] text-[#F6D9BF] ring-1 ring-[#EA4E1B]/50"
                        : "bg-[#EA4E1B] text-white"
                    }`}
                  >
                    {h.isHost && <Mic className="w-3 h-3" />}
                    {h.badge}
                  </span>
                  <div className="absolute bottom-4 left-4 right-4">
                    <h3 className="font-anton text-white text-2xl xl:text-3xl leading-none">
                      {h.nickname}
                    </h3>
                    <p className="text-[#F6D9BF] text-sm font-semibold mt-1">
                      {h.role}
                    </p>
                  </div>
                </div>
                <div className="p-6 flex flex-col flex-1">
                  <p className="text-[#6b5d52] text-sm leading-relaxed flex-1">
                    {h.bio}
                  </p>
                  {h.instagram ? (
                    <a
                      href={h.instagram}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-5 inline-flex items-center gap-2 text-[#1a1411] font-bold uppercase tracking-wide text-sm hover:text-[#EA4E1B] transition-colors"
                    >
                      <Instagram className="w-4 h-4" /> Segui su Instagram
                    </a>
                  ) : (
                    <span className="mt-5 inline-flex items-center gap-2 text-[#EA4E1B] font-bold uppercase tracking-wide text-sm">
                      <Mic className="w-4 h-4" /> La voce di UnoXdue
                    </span>
                  )}
                </div>
              </article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
