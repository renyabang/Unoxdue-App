import React from "react";
import { Twitch, Youtube, Instagram } from "lucide-react";
import { TikTokIcon } from "./icons";
import { brand, navLinks, socials } from "../mock";

const iconFor = (key) => {
  if (key === "twitch") return Twitch;
  if (key === "youtube") return Youtube;
  if (key === "instagram") return Instagram;
  return null;
};

export default function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="bg-[#14100e] text-white">
      <div className="max-w-7xl mx-auto px-5 lg:px-8 py-14">
        <div className="grid md:grid-cols-3 gap-10">
          <div>
            <div className="flex items-center gap-3">
              <img
                src={brand.logo}
                alt="UnoXdue logo"
                className="w-12 h-12 rounded-full object-cover ring-2 ring-[#EA4E1B]/60"
              />
              <span className="font-anton text-2xl tracking-wide">
                Uno<span className="text-[#EA4E1B]">X</span>due
              </span>
            </div>
            <p className="text-white/55 text-sm leading-relaxed mt-4 max-w-xs">
              Il podcast del calcio italiano. Analisi, pronostici, dibattito e
              interviste esclusive sulla Serie A.
            </p>
          </div>

          <div>
            <h4 className="font-archivo font-extrabold uppercase tracking-wide text-sm text-white/90">
              Naviga
            </h4>
            <ul className="mt-4 grid grid-cols-2 gap-y-2.5">
              {navLinks.map((l) => (
                <li key={l.href}>
                  <a
                    href={l.href}
                    className="text-white/60 hover:text-[#EA4E1B] text-sm transition-colors"
                  >
                    {l.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="font-archivo font-extrabold uppercase tracking-wide text-sm text-white/90">
              Seguici
            </h4>
            <div className="flex items-center gap-3 mt-4">
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
        </div>

        <div className="border-t border-white/10 mt-12 pt-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-white/45 text-sm">
            © {year} UnoXdue. Tutti i diritti riservati.
          </p>
          <p className="text-white/35 text-xs uppercase tracking-wide">
            Calcio · Serie A · Pronostici · Interviste
          </p>
        </div>
      </div>
    </footer>
  );
}
