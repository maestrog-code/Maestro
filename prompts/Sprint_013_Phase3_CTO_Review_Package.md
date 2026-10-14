# MAESTRO — Sprint 013 Phase 3 (Infrastructure as Code) CTO Review Package

Paste this entire document into ChatGPT for the code review.

---

## Context

Sprint 013 Phase 3: Infrastructure as Code (render.yaml).
This document contains the Render Blueprint for spinning up the FastAPI Web Service and Celery Worker synchronously.

---

## `../../backend/maestro/render.yaml`

```yaml
services:
  # The FastAPI Web Service
  - type: web
    name: maestro-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: ENVIRONMENT
        value: production
      - key: PYTHON_VERSION
        value: 3.12.3
      - key: DATABASE_URL
        sync: false
      - key: REDIS_URL
        sync: false
      - key: SECRET_KEY
        generateValue: true
      - key: BACKEND_CORS_ORIGINS
        sync: false
      - key: GEMINI_API_KEY
        sync: false

  # The Celery Worker Service
  - type: worker
    name: maestro-celery-worker
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: celery -A app.workers.celery_app worker --loglevel=info
    envVars:
      - key: ENVIRONMENT
        value: production
      - key: PYTHON_VERSION
        value: 3.12.3
      - key: DATABASE_URL
        sync: false
      - key: REDIS_URL
        sync: false
      - key: GEMINI_API_KEY
        sync: false
```

---

