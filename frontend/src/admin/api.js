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
  seoTools: () => req("/admin/seo-tools"),
  updateSeoTools: (body) => req("/admin/seo-tools", { method: "PUT", body }),
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
  coverGenerate: (body) => req("/admin/covers/generate", { method: "POST", body }),
  coverRevert: (body) => req("/admin/covers/revert", { method: "POST", body }),
  coverManual: (season, round, file) => {
    const fd = new FormData();
    fd.append("season", season);
    fd.append("round", round);
    fd.append("image", file);
    return req("/admin/covers/manual", { method: "POST", form: fd });
  },
  editPick: (body) => req("/admin/predictions/pick", { method: "PUT", body }),
  getLive: () => req("/admin/live"),
  setLive: (body) => req("/admin/live", { method: "PUT", body }),
  ilPodcastContent: () => req("/admin/site-content/il-podcast"),
  saveIlPodcastContent: (content) => req("/admin/site-content/il-podcast", { method: "PUT", body: { content } }),
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
  pressLogoExtract: (id) => req("/admin/press/logo/extract", { method: "POST", body: { id } }),
  pressLogoExtractAll: (onlyMissing = false) => req(`/admin/press/logo/extract-all?only_missing=${onlyMissing}`, { method: "POST", body: {} }),
  pressLogoApprove: (id) => req("/admin/press/logo/approve", { method: "POST", body: { id } }),
  pressLogoInitials: (id) => req("/admin/press/logo/initials", { method: "POST", body: { id } }),
  pressLogoManual: (id, file) => {
    const fd = new FormData();
    fd.append("id", id);
    fd.append("image", file);
    return req("/admin/press/logo/manual", { method: "POST", form: fd });
  },
  predAiList: () => req("/admin/predictions/ai/list"),
  predAiDetail: (season, round) => req(`/admin/predictions/ai/detail?season=${encodeURIComponent(season)}&round=${round}`),
  predAiSafety: (season, round) => req(`/admin/predictions/ai/safety?season=${encodeURIComponent(season)}&round=${round}`),
  predAiGenerate: (season, round) => req("/admin/predictions/ai/generate", { method: "POST", body: { season, round } }),
  predAiRegenerate: (season, round) => req("/admin/predictions/ai/regenerate", { method: "POST", body: { season, round } }),
  predAiEdit: (season, round, fields, matches) => req("/admin/predictions/ai/edit", { method: "POST", body: { season, round, fields, matches } }),
  predAiStatus: (season, round, action) => req("/admin/predictions/ai/status", { method: "POST", body: { season, round, action } }),
  predAiPublish: (season, round) => req("/admin/predictions/ai/publish", { method: "POST", body: { season, round, confirm: true } }),
  transcriptSeoStatus: () => req("/admin/transcripts/seo/status"),
  transcriptSeoGenerate: (slug) => req(`/admin/transcripts/seo/generate/${slug}`, { method: "POST" }),
  transcriptSeoPreview: (slug) => req(`/admin/transcripts/seo/preview/${slug}`),
  transcriptSeoSaveSections: (slug, sections) => req(`/admin/transcripts/seo/preview/${slug}/sections`, { method: "PUT", body: { sections } }),
  transcriptSeoPublish: (slug) => req(`/admin/transcripts/seo/publish/${slug}`, { method: "POST" }),
  transcriptSeoBatch: (body) => req("/admin/transcripts/seo/generate-batch", { method: "POST", body }),
  // Telegram
  tgConfig: () => req("/admin/telegram/config"),
  tgSaveConfig: (body) => req("/admin/telegram/config", { method: "PUT", body }),
  tgTest: () => req("/admin/telegram/test", { method: "POST" }),
  tgSendTest: () => req("/admin/telegram/send-test", { method: "POST" }),
  tgPreview: (params) => {
    const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== "")).toString();
    return req(`/admin/telegram/preview?${q}`);
  },
  tgPublishEpisode: (slug) => req("/admin/telegram/publish/episode", { method: "POST", body: { slug } }),
  tgPublishPrediction: (season, round, pick_index = 0) => req("/admin/telegram/publish/prediction", { method: "POST", body: { season, round, pick_index } }),
  tgPublishLive: (text) => req("/admin/telegram/publish/live", { method: "POST", body: { text } }),
  tgPublishPoll: (question, options) => req("/admin/telegram/publish/poll", { method: "POST", body: { question, options } }),
  tgMessages: (limit = 20) => req(`/admin/telegram/messages?limit=${limit}`),
  // Sponsor / Collabora
  sponsorContent: () => req("/admin/site-content/sponsor"),
  sponsorSaveContent: (content) => req("/admin/site-content/sponsor", { method: "PUT", body: { content } }),
  sponsorLeads: () => req("/admin/sponsor/leads"),
  sponsorLeadStatus: (id, status) => req(`/admin/sponsor/leads/${id}/status`, { method: "POST", body: { status } }),
  sponsorLeadDelete: (id) => req(`/admin/sponsor/leads/${id}`, { method: "DELETE" }),
};
