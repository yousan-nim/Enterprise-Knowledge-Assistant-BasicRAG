#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
case "${1:-}" in
    --native) set -- -f docker-compose.yml -f docker-compose.native.yml ;;
    "") set -- ;;
    *) echo "Usage: sh scripts/dev.sh [--native]" >&2; exit 2 ;;
esac
command -v docker >/dev/null 2>&1 || { echo "Install Docker Desktop (or Docker Engine + Compose) first." >&2; exit 1; }
docker compose version >/dev/null
docker info >/dev/null 2>&1 || { echo "Start Docker Desktop / Docker Engine, then run this command again." >&2; exit 1; }
if [ ! -e .env ]; then
    (umask 077; set -C
    password=$(od -An -N24 -tx1 /dev/urandom | tr -d ' \n')
    printf 'POSTGRES_DB=knowledge\nPOSTGRES_USER=rag\nPOSTGRES_PASSWORD=%s\nPOSTGRES_PORT=5433\nAPI_PORT=8080\nWEB_PORT=3000\n' "$password" > .env)
    echo "Created local .env with a random database password."
fi
if [ "$#" -gt 0 ]; then
    echo "Using host Ollama. Open Ollama and install embeddinggemma + qwen2.5:3b first."
else
    echo "Building API and preparing models. Docker mode downloads several GB on first startup."
fi
docker compose "$@" config --quiet
docker compose "$@" up -d --build --wait --wait-timeout 1800 frontend
docker compose "$@" ps
echo "Ready. Open the workspace at http://127.0.0.1:3000 (or your WEB_PORT). API docs: http://127.0.0.1:8080/docs."
echo "Stop: docker compose down (documents and models are retained)."
