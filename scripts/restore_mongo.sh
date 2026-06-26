#!/usr/bin/env bash
# Restore di un backup MongoDB di UnoXdue.
# Supporta sia il formato --archive (scripts/backup_mongo.sh) sia le cartelle mongodump (--out).
set -euo pipefail

SRC="${1:-}"
DB_NAME="${DB_NAME:-unoxdue}"
MONGO_URL="${MONGO_URL:-mongodb://localhost:27017}"

if [ -z "$SRC" ]; then
  echo "Uso:"
  echo "  DB_NAME=unoxdue MONGO_URL=mongodb://... bash scripts/restore_mongo.sh <archivio.archive | cartella_dump/>"
  echo "Esempi:"
  echo "  bash scripts/restore_mongo.sh backups/unoxdue-20260626-000000.archive"
  echo "  bash scripts/restore_mongo.sh backups/predeploy_20260625_213039/test_database"
  exit 1
fi

echo "ATTENZIONE: ripristino di '$SRC' nel DB '$DB_NAME' (--drop delle collezioni esistenti)."
read -r -p "Procedere? [y/N] " ans
[ "$ans" = "y" ] || { echo "Annullato."; exit 1; }

if [ -f "$SRC" ]; then
  # formato --archive
  mongorestore --uri="$MONGO_URL" --drop --archive="$SRC" --nsInclude="${DB_NAME}.*"
elif [ -d "$SRC" ]; then
  # cartella mongodump (contiene i .bson della singola collezione/db)
  mongorestore --uri="$MONGO_URL" --drop --db="$DB_NAME" "$SRC"
else
  echo "ERRORE: sorgente non trovata: $SRC"
  exit 1
fi

echo "Restore completato nel DB '$DB_NAME'."
