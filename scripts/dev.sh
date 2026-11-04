#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
command -v docker >/dev/null 2>&1 || { echo "Install Docker Desktop (or Docker Engine + Compose) first." >&2; exit 1; }
docker compose version >/dev/null
docker info >/dev/null 2>&1 || { echo "Start Docker Desktop / Docker Engine, then run this command again." >&2; exit 1; }
if [ ! -e .env ]; then
    (umask 077; set -C
    password=$(od -An -N24 -tx1 /dev/urandom | tr -d ' \n')
    printf 'POSTGRES_DB=knowledge\nPOSTGRES_USER=rag\nPOSTGRES_PASSWORD=%s\nPOSTGRES_PORT=5433\nAPI_PORT=8080\n' "$password" > .env)
    echo "Created local .env with a random database password."
fi
echo "Building API and preparing local models. First startup downloads several GB."
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 1800 backend
docker compose ps
echo "Ready. Swagger is on the backend's published port (default http://127.0.0.1:8080/docs)."
echo "Stop: docker compose down (documents and models are retained)."
