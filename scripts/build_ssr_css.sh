#!/usr/bin/env bash
# Compila il CSS condiviso (React src + template Jinja2) in un unico file statico
# minificato, con le sole classi utilizzate. Nessun Tailwind CDN a runtime.
# Build deterministico: stesso identico output del multi-stage Docker (nessun postcss.config raccolto).
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# Usa la CLI standalone (stesso identico binario del multi-stage Docker) per output coerente
# tra anteprima e produzione (es. il prefisso -webkit-backdrop-filter per Safari).
BIN="npx --yes tailwindcss@3.4.17"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/frontend" "$TMP/backend"
cp "$ROOT/frontend/tailwind.ssr.config.js" "$TMP/frontend/"
cp -r "$ROOT/frontend/src" "$TMP/frontend/src"
cp -r "$ROOT/backend/templates" "$TMP/backend/templates"

( cd "$TMP/frontend" && $BIN -c tailwind.ssr.config.js -i ./src/ssr.css -o "$TMP/unoxdue.css" --minify )

mkdir -p "$ROOT/backend/static/css"
cp "$TMP/unoxdue.css" "$ROOT/backend/static/css/unoxdue.css"
echo "CSS SSR compilato -> backend/static/css/unoxdue.css ($(wc -c < "$ROOT/backend/static/css/unoxdue.css") byte)"
