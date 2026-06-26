#!/usr/bin/env bash
# UnoXdue — avvio stack di produzione (Docker Compose) con health-check del backend.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "ERRORE: manca .env. Copia il template e compila i valori reali:"
  echo "  cp .env.example .env"
  exit 1
fi

# Verifica variabili obbligatorie non vuote.
REQUIRED="SITE_URL JWT_SECRET ADMIN_PASSWORD"
missing=""
for k in $REQUIRED; do
  v="$(grep -E "^${k}=" .env | head -1 | cut -d= -f2-)"
  [ -z "$v" ] && missing="$missing $k"
done
if [ -n "$missing" ]; then
  echo "ERRORE: variabili obbligatorie mancanti o vuote in .env:$missing"
  exit 1
fi

echo "==> Build e avvio (mongo + backend + web)..."
docker compose up -d --build

echo "==> Attendo l'health del backend..."
ok=0
for i in $(seq 1 40); do
  if docker compose exec -T backend curl -fsS http://localhost:8001/api/health >/dev/null 2>&1; then
    ok=1; echo "Backend OK."; break
  fi
  sleep 3
done
[ "$ok" = 1 ] || { echo "ATTENZIONE: backend non risponde a /api/health. Controlla: docker compose logs backend"; }

docker compose ps
echo "==> Stack avviato. Pubblico su http://<server>/ (metti un TLS davanti per HTTPS)."
echo "    Smoke test consigliato: bash scripts/smoke_test.sh https://unoxdue.net"
