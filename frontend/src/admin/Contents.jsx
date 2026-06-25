import React, { useEffect, useState } from "react";
import { ExternalLink, Trash2, RefreshCw } from "lucide-react";
import { api } from "./api";

const SITE = process.env.REACT_APP_BACKEND_URL;

export default function Contents() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try { setItems(await api.episodes()); } catch (e) {}
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const del = async (slug) => {
    if (!window.confirm("Eliminare questo contenuto?")) return;
    await api.deleteEpisode(slug);
    load();
  };

  const statusColor = (s) =>
    s === "da_verificare" ? "bg-amber-100 text-amber-700"
      : s === "bozza" ? "bg-gray-100 text-gray-600"
        : "bg-green-100 text-green-700";

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-anton text-3xl text-[#1a1411]">Contenuti</h1>
          <p className="text-[#6b5d52] mt-1">Episodi e interviste importati dal canale YouTube.</p>
        </div>
        <button onClick={load} className="inline-flex items-center gap-2 text-sm font-semibold text-[#EA4E1B]">
          <RefreshCw className="w-4 h-4" /> Aggiorna
        </button>
      </div>

      <div className="mt-6 bg-white rounded-xl border border-[#ecdfce] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[#fbf7f2] text-[#6b5d52] text-left">
            <tr>
              <th className="px-4 py-3 font-semibold">Titolo</th>
              <th className="px-4 py-3 font-semibold">Tipo</th>
              <th className="px-4 py-3 font-semibold">Stato</th>
              <th className="px-4 py-3 font-semibold">Azioni</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan="4" className="px-4 py-6 text-center text-[#9c8b7d]">Caricamento...</td></tr>}
            {!loading && items.map((i) => {
              const sec = i.type === "intervista" ? "interviste" : "episodi";
              return (
                <tr key={i.slug} className="border-t border-[#f0e7da]">
                  <td className="px-4 py-3 text-[#1a1411] font-medium max-w-md">{i.title}</td>
                  <td className="px-4 py-3"><span className="capitalize text-[#6b5d52]">{i.type}</span></td>
                  <td className="px-4 py-3"><span className={`text-xs font-bold px-2 py-1 rounded-full ${statusColor(i.status)}`}>{i.status || "pubblicato"}</span></td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <a href={`${SITE}/api/seo/${sec}/${i.slug}`} target="_blank" rel="noopener noreferrer" className="text-[#EA4E1B] inline-flex items-center gap-1" title="Anteprima SSR"><ExternalLink className="w-4 h-4" /></a>
                      <button onClick={() => del(i.slug)} className="text-red-500" title="Elimina"><Trash2 className="w-4 h-4" /></button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
