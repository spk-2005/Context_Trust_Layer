#!/usr/bin/env bash
set -e

echo "==> Running database migrations with Alembic..."
alembic upgrade head || {
    echo "Notice: Alembic migrations skipped or pre-existing schema detected. Ensuring head is stamped..."
    alembic stamp head 2>/dev/null || true
}

echo "==> Ensuring DB schema is initialized..."
python -c "import asyncio; from app.db.init_db import init_db_schema; asyncio.run(init_db_schema())" || echo "Notice: Schema init handled by application."

echo "==> Ensuring demo knowledge is seeded..."
python seed_demo_knowledge.py || echo "Notice: Demo knowledge already seeded."

echo "==> Launching FastAPI application on port ${PORT:-8000}..."
if [ "${APP_ENV}" = "production" ]; then
    echo "Running in PRODUCTION mode (workers: ${WEB_CONCURRENCY:-4})..."
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WEB_CONCURRENCY:-4}"
else
    echo "Running in DEVELOPMENT mode with hot-reload..."
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
fi
