#!/usr/bin/env bash

echo "Initiating Zero Budget Hack: Co-locating Celery and FastAPI..."

# Start Celery in the background with strict memory limits
celery -A app.workers.celery_app worker --loglevel=info --concurrency=1 &

# Start the FastAPI application in the foreground
uvicorn app.main:app --host 0.0.0.0 --port $PORT
