import React from "react";

// TikTok non è incluso in lucide-react, quindi lo definiamo come SVG dedicato.
export function TikTokIcon({ className = "", size = 24 }) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M16.6 5.82A4.28 4.28 0 0 1 15.54 3h-3.09v12.4a2.59 2.59 0 0 1-2.59 2.5 2.59 2.59 0 0 1-2.59-2.59 2.59 2.59 0 0 1 3.39-2.46V9.69a5.66 5.66 0 0 0-.8-.06A5.68 5.68 0 0 0 4.2 15.3a5.68 5.68 0 0 0 11.36 0V8.99a7.34 7.34 0 0 0 4.29 1.37V7.27a4.28 4.28 0 0 1-3.25-1.45z" />
    </svg>
  );
}
