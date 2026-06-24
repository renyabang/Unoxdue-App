import React from "react";
import { Twitch, Youtube, Instagram, ArrowUpRight } from "lucide-react";
import { TikTokIcon } from "./icons";
import { socials } from "../mock";
import Reveal from "./Reveal";

const iconFor = (key) => {
  if (key === "twitch") return Twitch;
  if (key === "youtube") return Youtube;
  if (key === "instagram") return Instagram;
  return null;
};

export default function SocialSection() {
  return (
    <section id="social" className="section-anchor bg-[#EA4E1B] py-20 lg:py-28">
      <div className="max-w-7xl mx-auto px-5 lg:px-8">
        <Reveal className="text-center max-w-2xl mx-auto">
          <span className="text-[#14100e] font-bold uppercase tracking-[0.25em] text-xs">
            Resta Connesso
          </span>
          <h2 className="font-anton text-[#14100e] text-4xl sm:text-5xl lg:text-6xl mt-3 leading-none">
            Seguici Ovunque
          </h2>
          <p className="text-[#3a1e10] text-base sm:text-lg mt-4 font-medium">
            Non perderti nessun contenuto: dirette, episodi, clip e interviste
            su tutte le nostre piattaforme.
          </p>
        </Reveal>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 mt-14">
          {socials.map((s, i) => {
            const Icon = iconFor(s.key);
            return (
              <Reveal key={s.key} delay={i * 80}>
                <a
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="lift group block h-full bg-white rounded-2xl p-6 shadow-sm hover:shadow-2xl"
                >
                  <div className="flex items-center justify-between">
                    <span
                      className="w-12 h-12 rounded-xl flex items-center justify-center text-white"
                      style={{ backgroundColor: s.color }}
                    >
                      {Icon ? (
                        <Icon className="w-6 h-6" />
                      ) : (
                        <TikTokIcon size={22} />
                      )}
                    </span>
                    <ArrowUpRight className="w-5 h-5 text-[#bcaea0] group-hover:text-[#EA4E1B] transition-colors" />
                  </div>
                  <h3 className="font-archivo font-extrabold text-[#1a1411] text-xl mt-4">
                    {s.label}
                  </h3>
                  <p className="text-[#EA4E1B] font-bold text-sm mt-0.5">
                    {s.handle}
                  </p>
                  <p className="text-[#6b5d52] text-sm leading-relaxed mt-2">
                    {s.desc}
                  </p>
                </a>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}
