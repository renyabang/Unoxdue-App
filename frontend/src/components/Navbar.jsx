import React, { useEffect, useState } from "react";
import { Menu, X, Twitch } from "lucide-react";
import { brand, navLinks } from "../mock";

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const closeAnd = (href) => {
    setOpen(false);
    const el = document.querySelector(href);
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-[#14100e]/95 backdrop-blur-md border-b border-white/10 py-3"
          : "bg-transparent py-5"
      }`}
    >
      <nav className="max-w-7xl mx-auto px-5 lg:px-8 flex items-center justify-between">
        <a
          href="#home"
          onClick={(e) => {
            e.preventDefault();
            closeAnd("#home");
          }}
          className="flex items-center gap-3 group"
        >
          <img
            src={brand.logo}
            alt="UnoXdue logo"
            className="w-11 h-11 rounded-full object-cover ring-2 ring-[#EA4E1B]/60 group-hover:ring-[#EA4E1B] transition-all"
          />
          <span className="font-anton text-white text-2xl tracking-wide hidden sm:block">
            Uno<span className="text-[#EA4E1B]">X</span>due
          </span>
        </a>

        <ul className="hidden lg:flex items-center gap-7">
          {navLinks.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                onClick={(e) => {
                  e.preventDefault();
                  closeAnd(link.href);
                }}
                className="link-underline text-sm font-semibold uppercase tracking-wide text-white/85 hover:text-white transition-colors"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>

        <div className="flex items-center gap-3">
          <a
            href="https://www.twitch.tv/unoxdue_"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:inline-flex items-center gap-2 bg-[#EA4E1B] hover:bg-[#d3430f] text-white text-sm font-bold uppercase tracking-wide px-5 py-2.5 rounded-full transition-colors"
          >
            <Twitch className="w-4 h-4" />
            Segui su Twitch
          </a>
          <button
            className="lg:hidden text-white p-2"
            onClick={() => setOpen((v) => !v)}
            aria-label="Menu"
          >
            {open ? <X className="w-7 h-7" /> : <Menu className="w-7 h-7" />}
          </button>
        </div>
      </nav>

      {/* Mobile menu */}
      <div
        className={`lg:hidden overflow-hidden transition-all duration-300 ${
          open ? "max-h-[480px] mt-3" : "max-h-0"
        }`}
      >
        <ul className="bg-[#14100e]/98 backdrop-blur-md border-t border-white/10 px-6 py-4 flex flex-col gap-1">
          {navLinks.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                onClick={(e) => {
                  e.preventDefault();
                  closeAnd(link.href);
                }}
                className="block py-3 text-base font-semibold uppercase tracking-wide text-white/85 hover:text-[#EA4E1B] border-b border-white/5"
              >
                {link.label}
              </a>
            </li>
          ))}
          <li className="pt-3">
            <a
              href="https://www.twitch.tv/unoxdue_"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 bg-[#EA4E1B] text-white text-sm font-bold uppercase tracking-wide px-5 py-3 rounded-full w-full justify-center"
            >
              <Twitch className="w-4 h-4" />
              Segui su Twitch
            </a>
          </li>
        </ul>
      </div>
    </header>
  );
}
