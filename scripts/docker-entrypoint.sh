#!/bin/bash
set -e

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-5002}"
