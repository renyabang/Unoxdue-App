#!/usr/bin/env bash
# Avvio locale rapido (fuori da Emergent) senza Docker.
# Richiede: Python 3.11, Node 20, MongoDB locale in esecuzione.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "== Backend =="
cd "$ROOT/backend"
pip install -r requirements.txt
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ || true
uvicorn server:app --host 0.0.0.0 --port 8001 &
BACK_PID=$!

echo "== Frontend =="
cd "$ROOT/frontend"
yarn install
yarn start &
FRONT_PID=$!

echo "Backend PID=$BACK_PID  Frontend PID=$FRONT_PID"
echo "Backend: http://localhost:8001/api/health  |  Frontend: http://localhost:3000"
wait
