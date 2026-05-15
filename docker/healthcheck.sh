#!/usr/bin/env sh
set -eu

BASE_URL="${1:-http://localhost:5174}"
API_URL="${2:-http://localhost:8000}"

echo "[1/3] Check frontend: ${BASE_URL}"
curl -fsS "${BASE_URL}" >/dev/null

echo "[2/3] Check backend health: ${API_URL}/health"
curl -fsS "${API_URL}/health" >/dev/null

echo "[3/3] Check docker services"
docker compose ps

echo "All checks passed ✅"
