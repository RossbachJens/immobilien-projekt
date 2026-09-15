#!/bin/sh
# Startet den bestehenden periodischen Backup-Loop im Hintergrund und den
# neuen Backup-Admin-API-Server im Vordergrund (PID 1). Pragmatische
# Vereinfachung: kein echter Prozess-Supervisor (tini/supervisord) - der
# Loop ist nur eine Sleep-Schleife um pg_dump, beim Container-Stop räumt
# Docker sie zusammen mit dem ganzen Prozess-Namespace auf.
set -eu

/backup-loop.sh &

exec uvicorn app.main:app --host 0.0.0.0 --port 8001