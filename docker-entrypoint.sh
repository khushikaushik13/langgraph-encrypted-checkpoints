#!/usr/bin/env bash
set -euo pipefail

echo " LangGraph Encrypted Demo Starting"

: "${PG_HOST:=127.0.0.1}"
: "${PG_PORT:=5432}"
: "${PG_DB:=lg}"
: "${PG_USER:=lg}"
: "${PG_PASSWORD:=lg}"

if [[ -z "${ENCRYPTION_KEY:-}" ]]; then
  echo "[entrypoint] ENCRYPTION_KEY not provided. Generating random..."
  ENCRYPTION_KEY="$(python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())")"
  export ENCRYPTION_KEY
  echo "[entrypoint] Generated ENCRYPTION_KEY=${ENCRYPTION_KEY}"
  echo "[entrypoint] (pass your own with -e ENCRYPTION_KEY=... for persistent decrypt)"
fi

export PG_HOST PG_PORT PG_DB PG_USER PG_PASSWORD

echo "[entrypoint] Detecting Postgres version..."
PG_MAJOR="$(ls /usr/lib/postgresql | sort -V | tail -n1)"
echo "[entrypoint] Using Postgres ${PG_MAJOR}"

if ! pg_lsclusters 2>/dev/null | awk 'NR>1{print $1,$2}' | grep -q "^${PG_MAJOR} main$"; then
  echo "[entrypoint] Creating cluster..."
  pg_createcluster "${PG_MAJOR}" main --start
else
  echo "[entrypoint] Starting existing cluster..."
  pg_ctlcluster "${PG_MAJOR}" main start
fi

echo "[entrypoint] Waiting for Postgres..."
until pg_isready -h 127.0.0.1 -p 5432 >/dev/null 2>&1; do
  sleep 0.5
done
echo "[entrypoint] Postgres ready."

echo "[entrypoint] Ensuring DB user exists..."
su - postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='${PG_USER}'\" | grep -q 1 || createuser -s '${PG_USER}'"

echo "[entrypoint] Ensuring database exists..."
su - postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='${PG_DB}'\" | grep -q 1 || createdb -O '${PG_USER}' '${PG_DB}'"

su - postgres -c "psql -c \"ALTER USER \\\"${PG_USER}\\\" WITH PASSWORD '${PG_PASSWORD}';\"" || true

echo "[entrypoint] Starting application..."
exec python main.py
