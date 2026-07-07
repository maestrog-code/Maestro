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
that analyse the business and provide proactive, actionable recommendations grounded in each
organization's own data.

---

## Current State

**Tag:** `sprint-004` | **Version:** `v0.1.0` (stabilisation in progress)

### ✅ Fully Built (Sprints 001–004 — COMPLETE)

**Foundation**
- Backend: FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16 + Redis + Celery
- `TimestampedModel` base with UUID PKs, soft delete, audit fields, optimistic locking
- Docker Compose development environment
- Alembic migrations: `001_initial_schema`, `002_ai_conversations`
- GitHub Actions CI (Python 3.12, PostgreSQL 16, Redis 7)

**Auth & Identity (Sprint 002)**
- User registration, login, JWT access tokens, Argon2 password hashing
- Refresh token rotation, token revocation, audit logging
- `get_current_user` FastAPI dependency

**Organizations & RBAC (Sprint 003)**
- Organizations, OrganizationMember, Role, Permission, RolePermission models
- Full CRUD for users and organizations
- Membership management: invite, remove, role assignment
- `require_member`, `require_owner` authorization helpers
- Organization-scoped multi-tenancy enforced throughout

**AI Executive Engine (Sprint 004)**
- `app/core/ai_settings.py` — AI runtime config via `AI_` env prefix
- `app/ai/providers/base.py` — `BaseLLMProvider` (generate, stream, embeddings)
- `app/ai/providers/google.py` — Google Gemini (google-genai SDK)
- `app/ai/agents/registry.py` — Agent registry with `AgentDefinition`
- `app/ai/agents/definitions/` — CEO and CFO agent definitions
- `app/ai/prompts/builder.py` — Markdown template renderer with `{{variable}}` interpolation
- `app/ai/prompts/templates/` — Externalized system prompts (ceo_system.md, cfo_system.md)
- `app/ai/tools/base.py` — `BaseTool` abstract class with `get_json_schema()`
- `app/ai/pipeline/executor.py` — `AIExecutionPipeline` (agent → safety → prompt → provider → persist → telemetry)
- `app/ai/pipeline/tool_executor.py` — `ToolExecutor` (permission check → validation → timeout → retry → audit log)
- `app/ai/safety/guards.py` — Prompt injection detection + PII redaction guards
- `app/ai/telemetry/logger.py` — Structured execution telemetry (provider, model, cost, retries, latency)
- `app/modules/ai_conversations/` — Conversation persistence module (full models/schemas/services/repos/router)
- `POST /organizations/{org_id}/ai/chat` — SSE streaming endpoint

### 🔄 Next: v0.1.0 Stabilisation (Before Sprint 005)
- CI passes consistently
- Docker verified from clean clone
- Alembic migrations verified from zero
- Docs updated
- `v0.1.0` tag

---

## Current Sprint

**Sprint 005 — Organizational Knowledge Engine**
**Branch:** `feature/organizational-knowledge-engine` (to be created)

### Sprint 005 Goals

Give every AI executive access to organization-specific knowledge via a RAG pipeline.

1. **Knowledge Sources** — File uploads (PDF, DOCX, TXT, Markdown), notes, policies, SOPs
2. **Document Processing** — Text extraction, chunking, metadata generation
3. **Embeddings** — Pluggable embedding provider, batch indexing, re-index support
4. **Vector Store** — Organization-scoped storage, semantic search, metadata filtering
5. **Retrieval Pipeline** — Hybrid retrieval, context assembly, citation support
6. **Knowledge Tools** — `search_knowledge_base`, `get_document`, `list_documents`
7. **Security** — Organization isolation, permission-aware retrieval, document-level access controls

---

## Technology Stack

```
Backend:    Python 3.12 + FastAPI 0.110.0
ORM:        SQLAlchemy 2.0 (async, asyncpg)
Database:   PostgreSQL 16
Auth:       JWT (python-jose) + Argon2 (passlib)
Cache:      Redis 7
Queue:      Celery 5.3.6
AI:         Google Gemini (google-genai SDK) — gemini-2.5-pro
Embeddings: Google text-embedding-004 (Sprint 005)
Vector DB:  pgvector or Pinecone (Sprint 005, TBD)
Mobile:     Flutter (Phase 4)
Web:        React + Next.js (Phase 5)
Payments:   Stripe, M-Pesa, Airtel Money (Phase 5)
CI:         GitHub Actions (.github/workflows/backend-ci.yml)
```

---

## Folder Structure

```
backend/maestro/app/
├── main.py
├── ai/
│   ├── agents/
│   │   ├── definitions/     ← ceo.py, cfo.py — AgentDefinition instances
│   │   └── registry.py      ← AgentRegistry singleton
│   ├── memory/              ← Reserved for Sprint 005 (vector memory)
│   ├── pipeline/
│   │   ├── executor.py      ← AIExecutionPipeline (main orchestrator)
│   │   └── tool_executor.py ← ToolExecutor (permission, validate, retry, audit)
│   ├── prompts/
│   │   ├── builder.py       ← PromptBuilder.render(template, context)
│   │   └── templates/       ← Markdown system prompt files
│   ├── providers/
│   │   ├── base.py          ← BaseLLMProvider (generate, stream, embeddings)
│   │   └── google.py        ← GoogleProvider (Gemini)
│   ├── router/              ← Empty — AI routes live in modules/ai_conversations/
│   ├── safety/
│   │   └── guards.py        ← AISafetyGuards (injection, PII)
│   ├── telemetry/
│   │   └── logger.py        ← AITelemetryLogger
│   ├── tools/
│   │   └── base.py          ← BaseTool abstract class
│   └── schemas.py           ← MessageRole, AIMessage, LLMResponse, ToolCall
├── api/v1/                  ← HTTP route registration
│   └── router.py
├── core/
│   ├── ai_settings.py       ← AISettings (AI_ env prefix)
│   ├── auth/                ← JWT, refresh tokens, audit logs
│   ├── config.py            ← Settings (Pydantic BaseSettings)
│   ├── database.py          ← Async DB engine & session
│   ├── events/              ← Event bus
│   ├── logger.py            ← Structured logging
│   └── security/            ← Password hashing, JWT utils
├── dependencies/            ← FastAPI DI (auth, db)
├── middleware/              ← Request middleware
├── models/base.py           ← TimestampedModel (all tables extend this)
├── modules/
│   ├── ai_conversations/    ← Conversation + AIMessageModel (Sprint 004)
│   ├── organizations/       ← Organization, OrganizationMember
│   ├── permissions/         ← Role, Permission, RolePermission
│   └── users/               ← User model, services, schemas
├── repositories/            ← BaseRepository with CRUD
├── schemas/                 ← Shared Pydantic schemas
├── services/                ← Shared services
├── shared/utils/            ← Cross-cutting utilities
└── workers/                 ← Celery tasks
```

---

## AI Runtime Architecture

```
POST /organizations/{org_id}/ai/chat
        │
    router.py (ai_conversations)
        │
    AIConversationService.chat_stream()
        │
    AIExecutionPipeline.execute()
        │
    ┌───────────────────────────────┐
    │  1. Resolve Agent (registry)  │
    │  2. Safety Guards             │
    │  3. Build Prompt (builder)    │
    │  4. Load History              │
    │  5. Stream → Provider         │
    │  6. Persist Messages          │
    │  7. Log Telemetry             │
    └───────────────────────────────┘
        │
    GoogleProvider.stream()
        │
    SSE chunks → client
```

**Adding a new agent:** Create `app/ai/agents/definitions/{role}.py`, define an `AgentDefinition`,
call `registry.register(agent)`, and add a Markdown template to `app/ai/prompts/templates/`.

**Adding a new provider:** Implement `BaseLLMProvider` in `app/ai/providers/{name}.py`.
No changes required in the pipeline.

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
10. **AI configuration lives in `ai_settings`.** Never hardcode model names, temperatures, or token limits inside providers or agents.
11. **Every Alembic migration must have a `downgrade()` path.**
12. **Provider abstraction must be preserved.** The pipeline must never import a specific provider directly — use the `BaseLLMProvider` interface.

---

## Database Conventions

- Table names: `snake_case`, plural (e.g., `organizations`, `ai_conversations`)
- Column names: `snake_case`
- Foreign keys: `{table_singular}_id` (e.g., `organization_id`, `conversation_id`)
- FK constraints: include `ondelete` action (`CASCADE` or `SET NULL`)
- Unique constraints: named `uq_{table}_{columns}` (e.g., `uq_org_user`)
- Composite indexes: named `ix_{table}_{col1}_{col2}` (e.g., `ix_ai_conversations_org_created`)

## Database Schema Summary

| Migration | Tables Created |
|---|---|
| `001_initial_schema` | `users`, `organizations`, `organization_members`, `roles`, `permissions`, `role_permissions`, `refresh_tokens`, `audit_logs` |
| `002_ai_conversations` | `ai_conversations`, `ai_messages`, `message_role_enum` (PostgreSQL ENUM) |

---

## API Conventions

- Base URL: `/api/v1/`
- Auth: Bearer JWT in `Authorization` header
- All IDs in URLs and responses are UUIDs (strings)
- Pagination: `?page=1&page_size=20`
- Error responses: `{"detail": "message"}` (FastAPI default)
- AI streaming: `text/event-stream` (SSE), `event: end` signals completion

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
| Agents | `{ROLE}` uppercase | `"CEO"`, `"CFO"` |
| Prompt templates | `{agent_role}_system.md` | `ceo_system.md` |

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
- ❌ Do not hardcode model names or temperatures — use `ai_settings`
- ❌ Do not import `GoogleProvider` directly in the pipeline — use `BaseLLMProvider`
- ❌ Do not write an Alembic migration without a `downgrade()` function

---

## Sprint History

| Sprint | Goal | Score | Status |
|---|---|---|---|
| 001 | Backend Foundation | — | ✅ Done |
| 002 | Auth + Multi-tenant Structure | — | ✅ Done |
| 003 | User & Organization CRUD | — | ✅ Done |
| 004 | AI Executive Engine v1 | 10/10 | ✅ Done |
| v0.1.0 | Stabilisation Milestone | — | 🔄 Next |
| 005 | Organizational Knowledge Engine | — | ⬜ Planned |
| 006 | Intelligent Planning & Multi-Agent | — | ⬜ Planned |
| 007 | Business Tools (CRM, Finance, HR) | — | ⬜ Planned |
| 008 | Autonomous Workflows | — | ⬜ Planned |
| 009 | Executive Dashboards & Analytics | — | ⬜ Planned |
| 010 | Production Hardening | — | ⬜ Planned |

---

*Last updated: Sprint 004 complete — July 2026*
*Feed this document to any AI before starting a new session on MAESTRO.*
