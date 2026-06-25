import React, { useEffect, useState } from "react";
import { Routes, Route, NavLink, Navigate, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, FileVideo, Ticket, ScrollText, Plug, LogOut, Lock, KeyRound, Sparkles, Image as ImageIcon, Youtube,
} from "lucide-react";
import { api, getToken, setToken, clearToken } from "./api";
import Dashboard from "./Dashboard";
import Contents from "./Contents";
import SlipUploader from "./SlipUploader";
import Logs from "./Logs";
import Integrations from "./Integrations";
import AIGen from "./AIGen";
import Graphics from "./Graphics";
import YouTube from "./YouTube";

function Login({ onLogged }) {
  const [email, setEmail] = useState("admin@unoxdue.net");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setLoading(true);
    try {
      const r = await api.login(email, password);
      setToken(r.token);
      onLogged(!!r.must_change_password);
    } catch (e) {
      setErr(e.message === "429" ? "Troppi tentativi, riprova più tardi" : "Credenziali non valide");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#14100e] flex items-center justify-center px-5">
      <form onSubmit={submit} className="w-full max-w-sm bg-white/[0.04] border border-white/10 rounded-2xl p-8">
        <div className="flex items-center gap-3 mb-6">
          <img src="/logo.jpg" alt="UnoXdue" className="w-11 h-11 rounded-full ring-2 ring-[#EA4E1B]/60" />
          <span className="font-anton text-white text-2xl">Uno<span className="text-[#EA4E1B]">X</span>due <span className="text-sm text-white/50">admin</span></span>
        </div>
        <label className="block text-white/70 text-xs font-semibold uppercase tracking-wide">Email</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)} data-testid="login-email-input" type="email" className="w-full mt-1 mb-4 bg-[#14100e] border border-white/15 rounded-lg px-3 py-2.5 text-white text-sm focus:border-[#EA4E1B] outline-none" />
        <label className="block text-white/70 text-xs font-semibold uppercase tracking-wide">Password</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} data-testid="login-password-input" className="w-full mt-1 mb-5 bg-[#14100e] border border-white/15 rounded-lg px-3 py-2.5 text-white text-sm focus:border-[#EA4E1B] outline-none" />
        {err && <p className="text-red-400 text-sm mb-3">{err}</p>}
        <button disabled={loading} data-testid="login-submit-btn" className="w-full inline-flex items-center justify-center gap-2 bg-[#EA4E1B] hover:bg-[#d3430f] text-white font-bold uppercase tracking-wide px-5 py-3 rounded-lg transition-colors disabled:opacity-60">
          <Lock className="w-4 h-4" /> {loading ? "Accesso..." : "Entra"}
        </button>
      </form>
    </div>
  );
}

function ChangePassword({ onDone }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    if (next !== confirm) { setErr("Le password non coincidono"); return; }
    if (next.length < 8) { setErr("Minimo 8 caratteri"); return; }
    setLoading(true);
    try {
      const r = await api.changePassword(current, next);
      setToken(r.token);
      onDone();
    } catch (e) { setErr(e.message || "Errore"); }
    finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-[#14100e] flex items-center justify-center px-5">
      <form onSubmit={submit} className="w-full max-w-sm bg-white/[0.04] border border-white/10 rounded-2xl p-8">
        <div className="flex items-center gap-3 mb-2">
          <KeyRound className="w-6 h-6 text-[#EA4E1B]" />
          <span className="font-anton text-white text-xl">Cambia password</span>
        </div>
        <p className="text-white/55 text-sm mb-5">Per sicurezza devi impostare una nuova password al primo accesso.</p>
        <input type="password" placeholder="Password attuale" value={current} onChange={(e) => setCurrent(e.target.value)} className="w-full mb-3 bg-[#14100e] border border-white/15 rounded-lg px-3 py-2.5 text-white text-sm focus:border-[#EA4E1B] outline-none" />
        <input type="password" placeholder="Nuova password" value={next} onChange={(e) => setNext(e.target.value)} className="w-full mb-3 bg-[#14100e] border border-white/15 rounded-lg px-3 py-2.5 text-white text-sm focus:border-[#EA4E1B] outline-none" />
        <input type="password" placeholder="Conferma nuova password" value={confirm} onChange={(e) => setConfirm(e.target.value)} className="w-full mb-4 bg-[#14100e] border border-white/15 rounded-lg px-3 py-2.5 text-white text-sm focus:border-[#EA4E1B] outline-none" />
        {err && <p className="text-red-400 text-sm mb-3">{err}</p>}
        <button disabled={loading} className="w-full inline-flex items-center justify-center gap-2 bg-[#EA4E1B] hover:bg-[#d3430f] text-white font-bold uppercase tracking-wide px-5 py-3 rounded-lg transition-colors disabled:opacity-60">
          {loading ? "Salvataggio..." : "Aggiorna password"}
        </button>
      </form>
    </div>
  );
}

const nav = [
  { to: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/admin/contenuti", label: "Contenuti", icon: FileVideo },
  { to: "/admin/youtube", label: "YouTube", icon: Youtube },
  { to: "/admin/ai", label: "AI / SEO", icon: Sparkles },
  { to: "/admin/schedine", label: "Schedine / Pronostici", icon: Ticket },
  { to: "/admin/grafiche", label: "Grafiche", icon: ImageIcon },
  { to: "/admin/log", label: "Log automazioni", icon: ScrollText },
  { to: "/admin/integrazioni", label: "Integrazioni", icon: Plug },
];

export default function AdminApp() {
  const [authed, setAuthed] = useState(!!getToken());
  const [mustChange, setMustChange] = useState(false);
  const [checked, setChecked] = useState(!getToken());
  const navigate = useNavigate();

  useEffect(() => {
    if (getToken()) {
      api.me()
        .then((m) => { setAuthed(true); setMustChange(!!m.must_change_password); })
        .catch(() => { clearToken(); setAuthed(false); })
        .finally(() => setChecked(true));
    }
  }, []);

  if (!checked) return <div className="min-h-screen bg-[#14100e]" />;
  if (!authed) return <Login onLogged={(mc) => { setAuthed(true); setMustChange(mc); }} />;
  if (mustChange) return <ChangePassword onDone={() => setMustChange(false)} />;

  const logout = () => { clearToken(); setAuthed(false); navigate("/admin"); };

  return (
    <div className="min-h-screen bg-[#fbf7f2] flex">
      <aside className="w-64 bg-[#14100e] text-white flex flex-col fixed inset-y-0 left-0">
        <div className="p-5 flex items-center gap-3 border-b border-white/10">
          <img src="/logo.jpg" alt="UnoXdue" className="w-10 h-10 rounded-full ring-2 ring-[#EA4E1B]/60" />
          <span className="font-anton text-xl">Uno<span className="text-[#EA4E1B]">X</span>due</span>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {nav.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end}
              className={({ isActive }) => `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold transition-colors ${isActive ? "bg-[#EA4E1B] text-white" : "text-white/70 hover:bg-white/5 hover:text-white"}`}>
              <n.icon className="w-4 h-4" /> {n.label}
            </NavLink>
          ))}
        </nav>
        <button onClick={logout} className="m-3 flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-semibold text-white/70 hover:bg-white/5 hover:text-white">
          <LogOut className="w-4 h-4" /> Esci
        </button>
      </aside>
      <main className="flex-1 ml-64 p-8">
        <Routes>
          <Route index element={<Dashboard />} />
          <Route path="contenuti" element={<Contents />} />
          <Route path="youtube" element={<YouTube />} />
          <Route path="ai" element={<AIGen />} />
          <Route path="schedine" element={<SlipUploader />} />
          <Route path="grafiche" element={<Graphics />} />
          <Route path="log" element={<Logs />} />
          <Route path="integrazioni" element={<Integrations />} />
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Routes>
      </main>
    </div>
  );
}
