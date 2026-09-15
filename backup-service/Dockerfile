FROM postgres:16

# python3/pip für den schlanken Backup-Admin-API-Server (app/main.py) - die
# eigentlichen Werkzeuge (pg_dump/pg_restore/psql) bringt das postgres:16-
# Basisimage bereits mit, garantiert dieselbe Version wie der 'db'-Service
# (wichtig für pg_restore-Kompatibilität).
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY app ./app
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8001
ENTRYPOINT ["/entrypoint.sh"]