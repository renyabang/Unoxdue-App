#!/usr/bin/env bash
# Compila il CSS condiviso (React + template Jinja2) in un unico file statico,
# minificato e con le sole classi utilizzate. Nessun Tailwind CDN a runtime.
set -e
cd "$(dirname "$0")/../frontend"
mkdir -p ../backend/static/css
npx tailwindcss -c tailwind.ssr.config.js -i ./src/ssr.css -o ../backend/static/css/unoxdue.css --minify
echo "CSS SSR compilato -> backend/static/css/unoxdue.css"
