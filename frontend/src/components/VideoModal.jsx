import React, { useEffect } from "react";
import { X } from "lucide-react";

// Player YouTube integrato in un modal full-screen.
export default function VideoModal({ video, onClose }) {
  useEffect(() => {
    if (!video) return;
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKey);
    };
  }, [video, onClose]);

  if (!video) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/85 backdrop-blur-sm p-4 animate-[fadeUp_0.25s_ease]"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="relative w-full max-w-5xl"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          aria-label="Chiudi"
          className="absolute -top-12 right-0 flex items-center gap-2 text-white/90 hover:text-[#EA4E1B] transition-colors"
        >
          <span className="text-sm font-semibold uppercase tracking-wide">
            Chiudi
          </span>
          <X className="w-6 h-6" />
        </button>
        <div className="relative w-full overflow-hidden rounded-2xl border border-white/10 shadow-2xl bg-black aspect-video">
          <iframe
            className="absolute inset-0 w-full h-full"
            src={`https://www.youtube.com/embed/${video.youtubeId}?autoplay=1&rel=0`}
            title={video.title}
            frameBorder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
          />
        </div>
        {video.title && (
          <p className="mt-4 text-white font-archivo font-semibold text-lg">
            {video.title}
          </p>
        )}
      </div>
    </div>
  );
}
