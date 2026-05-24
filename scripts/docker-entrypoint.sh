#!/bin/bash
set -e

if [ "$1" = 'celery' ]; then
    echo "Starting celery worker..."
    exec "$@"
fi

echo "Running Alembic migrations..."
alembic upgrade head

if [ "$#" -eq 0 ] || [ "$1" = 'backend' ]; then
    echo "Starting uvicorn server..."
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-5002}"
fi

exec "$@"
