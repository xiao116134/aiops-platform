#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$PROJECT_ROOT"

echo "[1/2] Ensure backend container is running..."
docker compose --env-file .env.compose up -d postgres backend >/dev/null

echo "[2/2] Run backend API tests..."
cd backend
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -q

echo "✅ Backend tests passed."
