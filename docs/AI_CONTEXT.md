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

### ✅ Fully Built (Sprints 001–006 — COMPLETE)

**Foundation (S001-S003)**
- Backend: FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16 + Redis + Celery
- Organizations & RBAC, Multi-tenancy, Auth, JWT, UUIDs.

**AI Executive Engine (Sprint 004)**
- `app/ai/pipeline/executor.py`, Gemini Provider, Safety Guards.
- CEO/CFO agent definitions.

**Organizational Knowledge Engine (Sprint 005)**
- RAG pipeline for organization documents.
- `knowledge_documents`, `knowledge_chunks`, `knowledge_embeddings`.
- `pgvector` store, asynchronous embedding via Celery.
- Implicit RAG injection before prompt building.

**The Memory System (Sprint 006)**
- Long-term memory for AI agents across sessions.
- `agent_memories`, `memory_embeddings`, `memory_access_logs`.
- Explicit tools (`remember_fact`, `forget_fact`) + Implicit memory context injection.
- Asynchronous Celery extraction using Gemini Structured Outputs.
- Deduplication via Vector Similarity (> 0.92) and Weighted Ranking.

### 🔄 Next: v0.1.0 Stabilisation
- CI passes consistently
- Docker verified from clean clone
- Alembic migrations verified from zero
- Docs updated
- `v0.1.0` tag

---

## Current Sprint

**Sprint 007 — Agent Orchestration Engine**
**Branch:** `feature/agent-orchestration-engine` (to be created)

### Sprint 007 Goals

Agents that can delegate subtasks, plan across multiple steps, and coordinate with other agents (e.g. CEO delegating to CFO).

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
| 005 | Organizational Knowledge Engine | 9.9/10 | ✅ Done |
| 006 | The Memory System | 9.95/10| ✅ Done |
| v0.1.0 | Stabilisation Milestone | — | 🔄 Next |
| 007 | Agent Orchestration Engine | — | ⬜ Planned |
| 008 | Business Tools (CRM, Finance, HR) | — | ⬜ Planned |
| 009 | Autonomous Workflows | — | ⬜ Planned |
| 010 | Executive Dashboards & Analytics | — | ⬜ Planned |
| 011 | Production Hardening | — | ⬜ Planned |

---

*Last updated: Sprint 006 complete — July 2026*
*Feed this document to any AI before starting a new session on MAESTRO.*
