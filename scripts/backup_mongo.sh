#!/usr/bin/env bash
# Backup del database MongoDB di UnoXdue.
set -euo pipefail
DB_NAME="${DB_NAME:-unoxdue}"
MONGO_URL="${MONGO_URL:-mongodb://localhost:27017}"
OUT_DIR="$(dirname "$0")/../backups"
mkdir -p "$OUT_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="$OUT_DIR/unoxdue-$STAMP.archive"
echo "Backup di '$DB_NAME' -> $ARCHIVE"
mongodump --uri="$MONGO_URL" --db="$DB_NAME" --archive="$ARCHIVE"
echo "Fatto."
