#!/usr/bin/env bash
set -e

echo "==> Running database migrations with Alembic..."
alembic upgrade head || echo "Notice: Alembic migrations skipped or already up to date."

echo "==> Ensuring DB schema is initialized..."
python -c "import asyncio; from app.db.init_db import init_db_schema; asyncio.run(init_db_schema())" || echo "Notice: Schema init handled by application."

echo "==> Launching FastAPI application on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
