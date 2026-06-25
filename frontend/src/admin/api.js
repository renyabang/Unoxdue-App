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
  aiSettings: () => req("/admin/ai/settings"),
  updateAiSettings: (body) => req("/admin/ai/settings", { method: "PUT", body }),
  aiProcess: (slug) => req(`/admin/ai/process/${slug}`, { method: "POST" }),
  aiProcessBatch: (body) => req("/admin/ai/process-batch", { method: "POST", body }),
  adminPredictions: () => req("/admin/predictions"),
  generateGraphics: (body) => req("/admin/graphics/generate", { method: "POST", body }),
  editPick: (body) => req("/admin/predictions/pick", { method: "PUT", body }),
  getLive: () => req("/admin/live"),
  setLive: (body) => req("/admin/live", { method: "PUT", body }),
};
