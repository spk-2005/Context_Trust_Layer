#!/usr/bin/env bash
set -e

echo "==> Running database migrations with Alembic..."
alembic upgrade head

echo "==> Ensuring demo knowledge is seeded..."
python seed_demo_knowledge.py || true

echo "==> Launching FastAPI application on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
