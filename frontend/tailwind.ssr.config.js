/** Build CSS condiviso per le pagine SSR (Jinja2) di UnoXdue.
 *  Analizza SIA i componenti React SIA i template Jinja2 cosi' le pagine
 *  SEO riusano le stesse classi/colori/font/spaziature del frontend React.
 *  Output: ../backend/static/css/unoxdue.css (minificato, classi inutilizzate rimosse).
 */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "../backend/templates/**/*.html",
  ],
  theme: {
    extend: {
      keyframes: {
        marquee: { from: { transform: "translateX(0)" }, to: { transform: "translateX(-50%)" } },
        floaty: { "0%,100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-12px)" } },
        fadeUp: { from: { opacity: "0", transform: "translateY(28px)" }, to: { opacity: "1", transform: "translateY(0)" } },
      },
      animation: {
        marquee: "marquee 28s linear infinite",
        floaty: "floaty 6s ease-in-out infinite",
        fadeUp: "fadeUp .7s cubic-bezier(.22,1,.36,1) both",
      },
    },
  },
  plugins: [],
};
