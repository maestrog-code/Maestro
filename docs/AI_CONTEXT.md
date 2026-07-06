# MAESTRO — AI Context Document

> **READ THIS FIRST.**
> This document must be provided to any AI tool (Antigravity, Gemini, ChatGPT, Cursor)
> before asking it to generate or modify code for MAESTRO.
> It is the single source of truth for the project.

---

## Project Identity

- **Name:** MAESTRO
- **Type:** AI-powered business operating system (SaaS)
- **Tagline:** "Your AI Executive Team."
- **Target:** Small and medium businesses — primarily East Africa
- **Model:** Multi-tenant SaaS (subscription: Free / Premium / Enterprise)

---

## What We Are Building

MAESTRO is a platform that lets business owners run their entire company from one dashboard.
It combines operations, payments, AI executive agents, inventory, CRM, invoicing,
and analytics into a single mobile-first application.

The AI layer is not a chatbot. It is a team of specialized AI executives (CEO, CFO, COO, etc.)
that analyse the business and provide proactive, actionable recommendations.

---

## Current Sprint

**Sprint 002 — Authentication Foundation**
**Branch:** `feature/auth-foundation`

What exists:
- Backend foundation (FastAPI, SQLAlchemy async, PostgreSQL, Redis, Celery)
- `TimestampedModel` base with UUID PKs, soft delete, audit fields, optimistic locking
- User, Organization, OrganizationMember models
- Role, Permission, RolePermission models
- RefreshToken, AuditLog models
- Auth router: `/register`, `/login`, `/refresh`, `/revoke`
- JWT + Argon2 security layer
- Event system scaffolded (stubs)
- AI agent folder structure scaffolded (empty)

What is missing from Sprint 002:
- `docker-compose.yml`
- Alembic initial migration
- Auth router wired into `main.py`
- End-to-end test (register → login → protected route)

---

## Technology Stack

```
Backend:   Python 3.12 + FastAPI 0.110.0
ORM:       SQLAlchemy 2.0 (async)
Database:  PostgreSQL 16
Auth:      JWT (python-jose) + Argon2 (passlib)
Cache:     Redis 7
Queue:     Celery 5.3.6
AI:        Gemini (Google AI Pro)
Mobile:    Flutter (Phase 2)
Web:       React + Next.js (Phase 3)
Payments:  Stripe, M-Pesa, Airtel Money (Phase 4)
```

---

## Folder Structure

```
backend/maestro/app/
├── main.py
├── ai/
│   ├── agents/          ← CEO, CFO, COO, etc.
│   ├── memory/          ← Agent memory / context
│   ├── router/          ← AI API endpoints
│   └── tools/           ← Agent callable tools
├── api/v1/              ← HTTP route registration
├── core/
│   ├── auth/            ← JWT, refresh tokens, audit logs
│   ├── config.py        ← Settings (Pydantic BaseSettings)
│   ├── database.py      ← Async DB engine
│   ├── events/          ← Event bus
│   ├── logger.py        ← Logging
│   └── security/        ← JWT utils, password hashing
├── dependencies/        ← FastAPI DI (get_current_user, get_db)
├── middleware/          ← Request middleware
├── models/base.py       ← TimestampedModel
├── modules/
│   ├── organizations/   ← Organization, OrganizationMember
│   ├── permissions/     ← Role, Permission, RolePermission
│   └── users/           ← User
├── repositories/        ← Base repository
├── schemas/             ← Shared Pydantic schemas
├── services/            ← Shared services
├── shared/utils/        ← Cross-cutting utilities
└── workers/             ← Celery tasks
```

---

## Architecture Rules (Non-Negotiable)

1. **All primary keys are UUIDs.** Never use auto-increment integers.
2. **All tables extend `TimestampedModel`** from `app/models/base.py`.
3. **Soft deletes only.** Set `is_deleted=True`. Never `DELETE FROM` business tables.
4. **Organization scoping is mandatory.** Every business data query must filter by `organization_id`.
5. **Modules never import from each other directly.** Cross-module communication goes through the event bus.
6. **Layer discipline:**
   - Routers call services only
   - Services call repositories only
   - Repositories talk to the database only
   - Models contain no logic
7. **Audit everything.** Every write operation should create an `AuditLog` entry.
8. **Passwords use Argon2** via `passlib`. Never store plain text.
9. **Secrets come from environment variables.** Never hardcode secrets.

---

## Database Conventions

- Table names: `snake_case`, plural (e.g., `organizations`, `audit_logs`)
- Column names: `snake_case`
- Foreign keys: `{table_singular}_id` (e.g., `organization_id`, `user_id`)
- FK constraints: include `ondelete` action (`CASCADE` or `SET NULL`)
- Unique constraints: named `uq_{table}_{columns}` (e.g., `uq_org_user`)

---

## API Conventions

- Base URL: `/api/v1/`
- Auth: Bearer JWT in `Authorization` header
- All IDs in URLs and responses are UUIDs (strings)
- Response format: JSON, camelCase keys in responses (Pydantic handles this)
- Pagination: `?page=1&page_size=20`
- Error responses: `{"detail": "message"}` (FastAPI default)

---

## Naming Conventions

| Item | Convention | Example |
|---|---|---|
| Files | snake_case | `user_service.py` |
| Classes | PascalCase | `UserService` |
| Functions | snake_case | `get_user_by_email` |
| Constants | UPPER_SNAKE_CASE | `ACCESS_TOKEN_EXPIRE_MINUTES` |
| DB tables | snake_case, plural | `organization_members` |
| Schemas | `{Model}{Action}` | `UserCreate`, `UserResponse` |
| Routers | `{module}_router` | `auth_router` |

---

## Module Structure Template

Every module (`modules/xxx/` or `core/xxx/`) must have:

```
xxx/
├── models.py       ← SQLAlchemy models (tables)
├── schemas.py      ← Pydantic request/response models
├── services.py     ← Business logic
├── repositories.py ← Database queries
└── router.py       ← FastAPI route handlers
```

---

## What NOT to Do

- ❌ Do not use `Integer` auto-increment primary keys
- ❌ Do not import from `modules/X` inside `modules/Y`
- ❌ Do not put business logic in routers
- ❌ Do not put SQL queries in services
- ❌ Do not use `bcrypt` — use `argon2` via passlib
- ❌ Do not hard-delete business records
- ❌ Do not hardcode secrets, URLs, or credentials
- ❌ Do not skip the `organization_id` filter on business data queries
- ❌ Do not generate entire "apps" in one prompt — follow the sprint structure

---

## Current Open Tasks (Sprint 002 Remaining)

1. Create `docker-compose.yml` at repo root
2. Create Alembic migration: `initial_schema`
3. Wire auth router into `app/main.py`
4. Complete `shared/utils/repository.py` base CRUD class
5. Write end-to-end test: register → login → call protected route
6. Merge `feature/auth-foundation` → `main`

---

## Sprint History

| Sprint | Goal | Status |
|---|---|---|
| 001 | Backend Foundation | ✅ Done |
| 002 | Auth + Multi-tenant Structure | 🔄 In Progress |
| 003 | User & Organization CRUD | ⬜ Planned |
| 004 | AI Executive Engine (v1) | ⬜ Planned |
| 005 | Dashboard Foundation | ⬜ Planned |

---

*Last updated: Sprint 002 — July 2026*
*Feed this document to any AI before starting a new session on MAESTRO.*
