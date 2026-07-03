# Maestro Backend

FastAPI application with SQLAlchemy 2.0 (asyncpg), Redis, Celery, and Docker configuration.

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

Ensure you have Python 3.10+ installed.

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
