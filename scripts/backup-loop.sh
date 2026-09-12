#!/bin/sh
# Läuft dauerhaft im 'backup'-Service (siehe docker-compose.yml). Nutzt die
# Standard-libpq-Umgebungsvariablen PGHOST/PGPORT/PGUSER/PGPASSWORD/
# PGDATABASE (vom Service gesetzt) - daher keine Verbindungsparameter im
# pg_dump-Aufruf nötig.
set -eu

BACKUP_DIR="/backups"
INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"
RETENTION="${BACKUP_RETENTION_COUNT:-14}"

mkdir -p "$BACKUP_DIR"

echo "Backup-Loop gestartet: alle ${INTERVAL}s, Aufbewahrung der letzten ${RETENTION} Dumps."

while true; do
    timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
    filename="${BACKUP_DIR}/${PGDATABASE}_${timestamp}.dump"
    tmpfile="${filename}.tmp"

    echo "[$(date -u +%FT%TZ)] Starte Backup nach ${filename} ..."
    if pg_dump --format=custom --file="${tmpfile}"; then
        # Atomares Umbenennen erst NACH erfolgreichem Abschluss - eine
        # abgebrochene Datei bekommt nie den "echten" Dateinamen und kann
        # daher nie fälschlich für ein vollständiges Backup gehalten werden.
        mv "${tmpfile}" "${filename}"
        echo "[$(date -u +%FT%TZ)] Backup abgeschlossen: ${filename}"
    else
        echo "[$(date -u +%FT%TZ)] FEHLER: Backup fehlgeschlagen, ${tmpfile} verworfen." >&2
        rm -f "${tmpfile}"
    fi

    # Rotation: nur die neuesten RETENTION Dumps behalten.
    ls -1t "${BACKUP_DIR}"/*.dump 2>/dev/null | tail -n "+$((RETENTION + 1))" | xargs -r rm -f

    sleep "${INTERVAL}"
done