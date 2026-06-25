/**
 * Preview SSR routing.
 *
 * Nell'ambiente di anteprima l'ingress instrada tutto ciò che non è /api verso
 * il dev server React (porta 3000). Per servire le pagine pubbliche come HTML
 * server-rendered (Jinja2) — e non come shell SPA — questo proxy inoltra le
 * route pubbliche pulite verso l'SSR del backend (/api/seo/...), mantenendo
 * /admin in React e gli asset statici sul dev server.
 *
 * In produzione la stessa mappatura URL pulita -> SSR è gestita dal reverse
 * proxy/ingress. Helper unico, nessuna anchor fittizia.
 */
const { createProxyMiddleware } = require("http-proxy-middleware");

const TARGET = process.env.SSR_PROXY_TARGET || "http://127.0.0.1:8001";

const EXACT = new Set([
  "/",
  "/il-podcast",
  "/parlano-di-noi",
  "/collaborazioni",
  "/contatti",
  "/privacy",
  "/cookie",
  "/sitemap.xml",
  "/video-sitemap.xml",
  "/robots.txt",
]);
const PREFIX = ["/episodi", "/interviste", "/pronostici", "/team"];

function clean(p) {
  const c = (p || "/").split("?")[0].replace(/\/+$/, "");
  return c === "" ? "/" : c;
}

function isPublic(pathname) {
  const path = clean(pathname);
  if (
    path.startsWith("/admin") ||
    path.startsWith("/static") ||
    path.startsWith("/api") ||
    path.startsWith("/ws") ||
    path.startsWith("/sockjs-node") ||
    path.startsWith("/__") ||
    path.includes("hot-update") ||
    path === "/manifest.json" ||
    path === "/asset-manifest.json" ||
    path === "/favicon.ico"
  ) {
    return false;
  }
  if (path === "/") return true;
  if (EXACT.has(path)) return true;
  return PREFIX.some((pre) => path === pre || path.startsWith(pre + "/"));
}

function rewrite(reqUrl) {
  const [p, qs] = (reqUrl || "/").split("?");
  const c = clean(p);
  let out;
  if (c === "/") out = "/api/seo/home";
  else if (["/sitemap.xml", "/video-sitemap.xml", "/robots.txt"].includes(c)) out = "/api" + c;
  else out = "/api/seo" + c;
  return qs ? `${out}?${qs}` : out;
}

module.exports = function (app) {
  app.use(
    createProxyMiddleware((pathname) => isPublic(pathname), {
      target: TARGET,
      changeOrigin: true,
      xfwd: true,
      pathRewrite: (path, req) => rewrite(req.originalUrl || path),
      logLevel: "silent",
    })
  );
};
