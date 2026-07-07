# Maestro Backend

FastAPI application with SQLAlchemy 2.0 (asyncpg), Redis, Celery, and Docker configuration.

## Python Runtime Requirement

**This project requires Python 3.12.** Python 3.12 is the standardised runtime for all
environments (local, CI, production containers).

| Artefact | Value |
|---|---|
| `.python-version` (repo root) | `3.12` |
| `backend/maestro/.python-version` | `3.12` |
| CI (`backend-ci.yml`) | `python-version: "3.12"` |
| Docker base image | `python:3.12-slim` |

> [!IMPORTANT]
> Do **not** use Python 3.13 or 3.14. Some transitive dependencies (e.g. `asyncpg`, `argon2-cffi`)
> do not yet publish wheels for those releases and will fail to install.

## Features
- **FastAPI**: Modern, fast web framework for building APIs.
- **SQLAlchemy 2.0 (Async)**: Database interactions using `asyncpg`.
- **Alembic**: Database migrations.
- **Redis & Celery**: Background task queue.
- **Loguru**: Beautiful and structured logging.
- **Pydantic**: Data validation and settings management.
- **Docker Compose**: Ready-to-use development environment.

## Getting Started

### Using Docker (Recommended for Local Dev)

```bash
docker compose build
docker compose up -d
```
This will start:
- `api` on `http://localhost:8000`
- `db` on port `5432`
- `redis` on port `6379`

### Local Virtual Environment

Ensure you have Python 3.12 installed.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the application:
```bash
uvicorn app.main:app --reload
```

## Migrations

Initialize/upgrade the database:

```bash
alembic upgrade head
```

To create a new migration after modifying models:

```bash
alembic revision --autogenerate -m "Add new table"
```
