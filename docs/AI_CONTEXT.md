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

**Sprint 004 — AI Executive Engine**
**Branch:** `feature/ai-executive-engine` (to be created)

### What is fully built (Sprints 001, 002, & 003 — COMPLETE ✅)
- Backend foundation (FastAPI, SQLAlchemy async, PostgreSQL, Redis, Celery)
- `TimestampedModel` base with UUID PKs, soft delete, audit fields, optimistic locking
- User, Organization, OrganizationMember models
- Role, Permission, RolePermission models
- RefreshToken, AuditLog models
- Authentication: Register, login, protected routes via JWT
- Organization management: Create org (with atomic transaction + unique slug generation), list orgs, get org
- Membership management: Invite member, remove member, change roles
- Centralized authorization helpers: `require_member`, `require_owner`
- Event dispatcher with domain events (`ORGANIZATION_CREATED`, `MEMBER_INVITED`, etc.)
- Full CRUD `BaseRepository` (persistence only)
- Alembic migrations
- E2E tests for auth, users, and organizations
- Master context docs: `docs/` (PROJECT_VISION, ARCHITECTURE, ROADMAP, DECISIONS, AI_CONTEXT)
- All code on `main` branch on GitHub

### Sprint 004 Goals
Establish the core AI runtime and execution platform so that future agents (CEO, CFO, COO) can be easily added.
The engine must include:
1. **AI Router**: Receives requests and selects the appropriate executive agent.
2. **Agent Registry**: For discovering and registering available AI executives.
3. **Conversation Memory**: Organization-scoped context and session management.
4. **Prompt Management**: Versioned system prompts and templates.
5. **Tool Execution Framework**: Allowing agents to safely invoke business tools.
6. **Execution Pipeline**: Supporting request → planning → tool use → response.
7. **Streaming Responses**: Via Server-Sent Events or WebSockets.
8. **Observability**: Execution logs, latency, token usage, and failures.

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

## Current Open Tasks (Sprint 004)

1. Create branch `feature/ai-executive-engine`
2. Implement **Conversation Memory** (DB models and schemas for threads/messages)
3. Implement **Agent Registry & Prompt Management** (Hardcoded configurations or DB models)
4. Implement **Tool Execution Framework**
5. Implement **Execution Pipeline & AI Router** (LangChain/LlamaIndex or raw provider SDK)
6. Implement **Streaming Responses** endpoint
7. Implement **Observability** tracking for AI usage
8. Wire AI routers into `api/v1/router.py`
9. Write tests for AI components using mock LLM responses

---

## Sprint History

| Sprint | Goal | Status |
|---|---|---|
| 001 | Backend Foundation | ✅ Done |
| 002 | Auth + Multi-tenant Structure | ✅ Done |
| 003 | User & Organization CRUD | ✅ Done |
| 004 | AI Executive Engine (v1) | 🔄 In Progress |
| 005 | Dashboard Foundation | ⬜ Planned |

---

*Last updated: Sprint 004 — July 2026*
*Feed this document to any AI before starting a new session on MAESTRO.*
