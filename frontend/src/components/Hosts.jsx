import React from "react";
import { Instagram, Mic, Quote } from "lucide-react";
import { hosts } from "../mock";
import Reveal from "./Reveal";

export default function Hosts() {
  const host = hosts.find((h) => h.isHost);
  const tipsters = hosts.filter((h) => !h.isHost);

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
            Un host e tre tipster: voci diverse, un'unica passione per il calcio.
          </p>
        </Reveal>

        {/* Host in evidenza */}
        {host && (
          <Reveal className="mt-14">
            <article className="relative overflow-hidden rounded-[2rem] bg-[#14100e] grid md:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] items-stretch shadow-2xl">
              <div className="pointer-events-none absolute -top-24 -right-16 w-96 h-96 rounded-full bg-[#EA4E1B]/20 blur-[110px]" />

              {/* Foto */}
              <div className="relative min-h-[360px] md:min-h-[460px]">
                <img
                  src={host.photo}
                  alt={`${host.nickname} — host di UnoXdue`}
                  className="absolute inset-0 w-full h-full object-cover object-center"
                />
                <span className="absolute inset-0 bg-gradient-to-r from-transparent via-transparent to-[#14100e] hidden md:block" />
                <span className="absolute inset-0 bg-gradient-to-t from-[#14100e] via-transparent to-transparent md:hidden" />
                <span className="absolute top-5 left-5 inline-flex items-center gap-2 bg-[#14100e]/80 backdrop-blur-sm text-[#F6D9BF] text-[11px] font-bold uppercase tracking-wide px-3.5 py-2 rounded-full ring-1 ring-[#EA4E1B]/50">
                  <Mic className="w-3.5 h-3.5 text-[#EA4E1B]" /> Host
                </span>
              </div>

              {/* Testo */}
              <div className="relative p-7 sm:p-10 flex flex-col justify-center">
                <span className="text-[#EA4E1B] font-bold uppercase tracking-[0.22em] text-xs">
                  La voce di UnoXdue
                </span>
                <h3 className="font-anton text-white text-3xl sm:text-4xl lg:text-5xl leading-none mt-3">
                  {host.nickname}
                </h3>
                <div className="flex items-center gap-2 mt-3 text-[#F6D9BF]">
                  <Mic className="w-4 h-4 text-[#EA4E1B]" />
                  <span className="text-sm font-semibold uppercase tracking-wide">
                    {host.role}
                  </span>
                </div>
                <div className="relative mt-5">
                  <Quote className="absolute -left-1 -top-2 w-8 h-8 text-[#EA4E1B]/25" />
                  <p className="text-white/65 text-sm sm:text-base leading-relaxed pl-7">
                    {host.bio}
                  </p>
                </div>
              </div>
            </article>
          </Reveal>
        )}

        {/* Tipster */}
        <Reveal className="mt-12">
          <div className="flex items-center gap-4">
            <span className="font-archivo font-extrabold uppercase tracking-[0.2em] text-sm text-[#1a1411]">
              I tipster
            </span>
            <span className="h-px flex-1 bg-[#e6d8c6]" />
          </div>
        </Reveal>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-7 mt-7">
          {tipsters.map((h, i) => (
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
                  <span className="absolute top-4 left-4 bg-[#EA4E1B] text-white text-[11px] font-bold uppercase tracking-wide px-3 py-1.5 rounded-full">
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
                  <a
                    href={h.instagram}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-5 inline-flex items-center gap-2 text-[#1a1411] font-bold uppercase tracking-wide text-sm hover:text-[#EA4E1B] transition-colors"
                  >
                    <Instagram className="w-4 h-4" /> Segui su Instagram
                  </a>
                </div>
              </article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
