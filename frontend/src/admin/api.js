const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const TOKEN_KEY = "uxd_admin_token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

async function req(path, { method = "GET", body, form } = {}) {
  const headers = {};
  const t = getToken();
  if (t) headers["Authorization"] = `Bearer ${t}`;
  const opts = { method, headers };
  if (form) {
    opts.body = form;
  } else if (body) {
    headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${API}${path}`, opts);
  if (res.status === 401) clearToken();
  const ct = res.headers.get("content-type") || "";
  const data = ct.includes("json") ? await res.json() : await res.text();
  if (!res.ok) throw new Error((data && data.detail) || "Errore richiesta");
  return data;
}

export const api = {
  base: API,
  login: (email, password) => req("/admin/login", { method: "POST", body: { email, password } }),
  me: () => req("/admin/me"),
  changePassword: (current_password, new_password) =>
    req("/admin/change-password", { method: "POST", body: { current_password, new_password } }),
  episodes: () => req("/admin/episodes"),
  deleteEpisode: (slug) => req(`/admin/episodes/${slug}`, { method: "DELETE" }),
  syncYoutube: () => req("/admin/sync/youtube", { method: "POST" }),
  logs: (limit = 100) => req(`/admin/logs?limit=${limit}`),
  settings: () => req("/admin/settings"),
  predictions: () => req("/predictions"),
  pressSearch: (q) => req(`/admin/press/search?q=${encodeURIComponent(q)}`),
  ocr: (file) => {
    const fd = new FormData();
    fd.append("image", file);
    return req("/admin/predictions/ocr", { method: "POST", form: fd });
  },
  addPick: (payload) => req("/admin/predictions/add-pick", { method: "POST", body: payload }),
  slipUploads: (limit = 30) => req(`/admin/slip-uploads?limit=${limit}`),
  resultsStatus: () => req("/admin/results/status"),
  resultsSettings: (body) => req("/admin/results/settings", { method: "PUT", body }),
  resultsSettle: (body) => req("/admin/results/settle", { method: "POST", body }),
  resultsView: (season, round) => req(`/admin/results/${season}/${round}`),
  resultsCorrect: (body) => req("/admin/results/correct", { method: "POST", body }),
  aiSettings: () => req("/admin/ai/settings"),
  updateAiSettings: (body) => req("/admin/ai/settings", { method: "PUT", body }),
  aiProcess: (slug) => req(`/admin/ai/process/${slug}`, { method: "POST" }),
  aiProcessBatch: (body) => req("/admin/ai/process-batch", { method: "POST", body }),
  adminPredictions: () => req("/admin/predictions"),
  generateGraphics: (body) => req("/admin/graphics/generate", { method: "POST", body }),
  editPick: (body) => req("/admin/predictions/pick", { method: "PUT", body }),
  getLive: () => req("/admin/live"),
  setLive: (body) => req("/admin/live", { method: "PUT", body }),
  youtubeStats: () => req("/admin/youtube/stats"),
  youtubeBackfill: (body) => req("/admin/youtube/backfill", { method: "POST", body }),
  websubStatus: () => req("/admin/youtube/websub"),
  websubSubscribe: (mode = "subscribe") => req("/admin/youtube/websub/subscribe", { method: "POST", body: { mode } }),
  oauthStatus: () => req("/admin/youtube/oauth/status"),
  oauthStart: (origin) => req(`/admin/youtube/oauth/start?origin=${encodeURIComponent(origin)}`),
  oauthDisconnect: () => req("/admin/youtube/oauth/disconnect", { method: "POST" }),
  youtubeExclusions: () => req("/admin/youtube/exclusions"),
  transcripts: () => req("/admin/youtube/transcripts"),
  fetchTranscript: (slug) => req(`/admin/youtube/transcript/${slug}`, { method: "POST" }),
  pressStatus: () => req("/admin/press/status"),
  pressRun: (body) => req("/admin/press/run", { method: "POST", body: body || {} }),
  pressConfig: () => req("/admin/press/config"),
  pressSetConfig: (config) => req("/admin/press/config", { method: "POST", body: { config } }),
  pressList: (status) => req(`/admin/press/list${status ? `?status=${status}` : ""}`),
  pressRejected: (category) => req(`/admin/press/rejected${category ? `?category=${category}` : ""}`),
  pressRuns: (limit = 10) => req(`/admin/press/runs?limit=${limit}`),
  pressSetStatus: (id, status) => req("/admin/press/set-status", { method: "POST", body: { id, status } }),
  pressLink: (body) => req("/admin/press/link", { method: "POST", body }),
  pressLinkOptions: () => req("/admin/press/link-options"),
};
