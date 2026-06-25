import React from "react";
import { Radio, Target, Users, Clapperboard } from "lucide-react";
import { aboutText, features } from "../mock";
import Reveal from "./Reveal";

const iconMap = {
  radio: Radio,
  target: Target,
  users: Users,
  clapperboard: Clapperboard,
};

export default function About() {
  return (
    <section id="about" className="section-anchor bg-[#fbf7f2] py-20 lg:py-28">
      <div className="max-w-7xl mx-auto px-5 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-start">
          <Reveal>
            <span className="text-[#EA4E1B] font-bold uppercase tracking-[0.25em] text-xs">
              Chi siamo
            </span>
            <h2 className="font-anton text-[#1a1411] text-4xl sm:text-5xl lg:text-6xl mt-3 leading-none">
              Il podcast
            </h2>
            <div className="mt-6 space-y-4">
              {aboutText.map((p, i) => (
                <p
                  key={i}
                  className="text-[#4a3d34] text-base sm:text-lg leading-relaxed"
                >
                  {p}
                </p>
              ))}
            </div>
          </Reveal>

          <div className="grid sm:grid-cols-2 gap-5">
            {features.map((f, i) => {
              const Icon = iconMap[f.icon];
              return (
                <Reveal key={f.title} delay={i * 90}>
                  <div className="lift h-full bg-white rounded-2xl border border-[#ecdfce] p-6 shadow-sm hover:shadow-xl hover:border-[#EA4E1B]/40">
                    <div className="w-12 h-12 rounded-xl bg-[#EA4E1B]/10 flex items-center justify-center">
                      <Icon className="w-6 h-6 text-[#EA4E1B]" />
                    </div>
                    <h3 className="font-archivo font-extrabold text-[#1a1411] text-lg mt-4">
                      {f.title}
                    </h3>
                    <p className="text-[#6b5d52] text-sm leading-relaxed mt-2">
                      {f.text}
                    </p>
                  </div>
                </Reveal>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
