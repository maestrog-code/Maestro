# MAESTRO — System Architecture

> **Pattern: Modular Monolith → Future Microservices**
> Last updated: Sprint 004 complete — July 2026

This document is the authoritative reference for MAESTRO's architecture.
Every AI tool and developer must read this before making changes.

---

## Architecture Style

**Modular Monolith** — modules are self-contained and communicate through events,
not direct imports. This allows us to extract microservices later with minimal rework.

```
Request → API Layer → Service Layer → Repository Layer → Database
                                ↕
                          Event Bus
                                ↕
                         AI Agent Layer
```

---

## Technology Stack (Locked)

| Layer | Technology | Version |
|---|---|---|
| Backend Framework | FastAPI | 0.110.0 |
| Language | Python | **3.12** (pinned) |
| ORM | SQLAlchemy | 2.0.29 (async) |
| Database | PostgreSQL | 16 |
| Migrations | Alembic | 1.13.1 |
| Validation | Pydantic v2 | 2.6.4 |
| Auth | JWT (python-jose) + Argon2 | — |
| Cache | Redis | 7 |
| Task Queue | Celery | 5.3.6 |
| **AI Provider** | **Google Gemini (google-genai SDK)** | **gemini-2.5-pro** |
| **Embeddings** | Google text-embedding-004 | Sprint 005 |
| **Vector Store** | pgvector or Pinecone | Sprint 005, TBD |
| Mobile | Flutter | Phase 4 |
| Web | React + Next.js | Phase 5 |
| Payments | Stripe / M-Pesa / Airtel Money | Phase 5 |
| Containerisation | Docker + Docker Compose | — |
| CI/CD | GitHub Actions | backend-ci.yml |

---

## Repository Structure

```
Maestro/
├── backend/
│   └── maestro/
│       ├── app/                    ← Application code
│       │   ├── main.py
│       │   ├── ai/                      ← AI Executive Engine
│       │   │   ├── agents/
│       │   │   │   ├── definitions/     ← ceo.py, cfo.py (AgentDefinition)
│       │   │   │   └── registry.py      ← AgentRegistry singleton
│       │   │   ├── memory/              ← Reserved: Sprint 005 vector memory
│       │   │   ├── pipeline/
│       │   │   │   ├── executor.py      ← AIExecutionPipeline (orchestrator)
│       │   │   │   └── tool_executor.py ← ToolExecutor (retry, timeout, audit)
│       │   │   ├── prompts/
│       │   │   │   ├── builder.py       ← PromptBuilder.render(template, ctx)
│       │   │   │   └── templates/       ← ceo_system.md, cfo_system.md
│       │   │   ├── providers/
│       │   │   │   ├── base.py          ← BaseLLMProvider (generate/stream/embed)
│       │   │   │   └── google.py        ← GoogleProvider (Gemini)
│       │   │   ├── safety/
│       │   │   │   └── guards.py        ← Prompt injection + PII guards
│       │   │   ├── telemetry/
│       │   │   │   └── logger.py        ← AITelemetryLogger
│       │   │   ├── tools/
│       │   │   │   └── base.py          ← BaseTool abstract class
│       │   │   └── schemas.py           ← MessageRole, AIMessage, LLMResponse
│       │   ├── api/                     ← HTTP routing
│       │   │   └── v1/
│       │   ├── core/                    ← Platform-level concerns
│       │   │   ├── ai_settings.py       ← AISettings (AI_ env prefix)
│       │   │   ├── auth/                ← JWT, refresh tokens, audit logs
│       │   │   ├── config.py            ← Settings
│       │   │   ├── database.py          ← DB engine & session
│       │   │   ├── events/              ← Event bus
│       │   │   ├── logger.py            ← Structured logging
│       │   │   └── security/            ← Password hashing, JWT utils
│       │   ├── dependencies/            ← FastAPI DI (auth, db)
│       │   ├── middleware/              ← Request middleware
│       │   ├── models/
│       │   │   └── base.py              ← TimestampedModel (all tables extend this)
│       │   ├── modules/                 ← Business domain modules
│       │   │   ├── ai_conversations/    ← Conversation + AIMessageModel (S004)
│       │   │   ├── organizations/       ← Organization + OrganizationMember
│       │   │   ├── permissions/         ← Role + Permission + RolePermission
│       │   │   └── users/               ← User model, services, schemas
│       │   ├── repositories/            ← BaseRepository with CRUD
│       │   ├── schemas/                 ← Shared Pydantic schemas
│       │   ├── services/                ← Shared services
│       │   ├── shared/                  ← Cross-cutting utilities
│       │   └── workers/                 ← Celery tasks
│       ├── alembic/
│       │   └── versions/
│       │       ├── 001_initial_schema.py
│       │       └── 002_ai_conversations.py
│       └── requirements.txt
├── mobile/                         ← Flutter app (Phase 2)
├── web/                            ← Next.js web app (Phase 3)
├── docker/                         ← Dockerfiles
├── docs/                           ← THIS FOLDER — master context
├── prompts/                        ← AI prompt templates per sprint
├── scripts/                        ← Code generation & utility scripts
└── .github/workflows/              ← CI/CD pipelines
```

---

## Database Design

### Base Model — `TimestampedModel`
Every table in MAESTRO extends this:

```python
id:          UUID        # Primary key (never auto-increment integers)
created_at:  datetime    # Auto-set on insert
updated_at:  datetime    # Auto-set on insert & update
is_deleted:  bool        # Soft delete flag
deleted_at:  datetime?   # When soft deleted
created_by:  UUID?       # Audit: who created
updated_by:  UUID?       # Audit: who last updated
version:     int         # Optimistic locking (prevents race conditions)
```

### Core Tables (Sprint 002)

```
users
├── id (UUID PK)
├── email (unique)
├── hashed_password
├── full_name
├── is_active
├── is_superuser
└── [TimestampedModel fields]

organizations
├── id (UUID PK)
├── name
├── slug (unique)
└── [TimestampedModel fields]

organization_members
├── id (UUID PK)
├── organization_id (FK → organizations)
├── user_id (FK → users)
├── role_id (FK → roles, nullable)
├── status
└── [TimestampedModel fields]
UNIQUE (organization_id, user_id)

roles
├── id (UUID PK)
├── name
├── description
├── organization_id (FK → organizations)
└── [TimestampedModel fields]
UNIQUE (organization_id, name)

permissions
├── id (UUID PK)
├── name (unique)
├── resource
├── action
└── [TimestampedModel fields]

role_permissions
├── id (UUID PK)
├── role_id (FK → roles)
├── permission_id (FK → permissions)
└── [TimestampedModel fields]
UNIQUE (role_id, permission_id)

refresh_tokens
├── id (UUID PK)
├── token (unique, indexed)
├── user_id (FK → users)
├── expires_at
├── revoked_at (nullable)
└── [TimestampedModel fields]

audit_logs
├── id (UUID PK)
├── who (FK → users, nullable)
├── what (action name)
├── resource (resource type)
├── organization_id (FK → organizations, nullable)
├── ip
├── user_agent
├── details (JSON)
└── [TimestampedModel fields]

ai_conversations (Sprint 004)
├── id (UUID PK)
├── organization_id (FK → organizations, CASCADE)
├── title (nullable)
├── active_agent (nullable — e.g. "CEO", "CFO")
├── provider (nullable — e.g. "google")
├── model (nullable — e.g. "gemini-2.5-pro")
├── temperature (nullable float)
└── [TimestampedModel fields]
INDEX (organization_id)
INDEX (organization_id, created_at)  ← composite for listing

ai_messages (Sprint 004)
├── id (UUID PK)
├── conversation_id (FK → ai_conversations, CASCADE)
├── role (message_role_enum: system | user | assistant | tool)
├── content (TEXT)
├── name (nullable — tool name when role=tool)
├── tool_calls (JSON nullable — list of ToolCall dicts)
├── tool_call_id (nullable — correlation id for tool results)
└── [TimestampedModel fields]
INDEX (conversation_id)
INDEX (conversation_id, created_at)  ← composite for history
```

---

## Multi-Tenancy Model

MAESTRO uses **Organization-scoped multi-tenancy**:

```
User
 └── can belong to many Organizations (via OrganizationMember)
      └── each membership has a Role
           └── each Role has Permissions
                └── Permissions gate all business data access
```

**Rule:** Every business data query MUST be scoped to `organization_id`.
Never return data from one organization to another — ever.

---

## Authentication Flow

```
1. POST /api/v1/auth/register   → Create user → issue JWT + refresh token
2. POST /api/v1/auth/login      → Verify password → issue JWT + refresh token
3. GET  /api/v1/...             → Bearer JWT in Authorization header
4. POST /api/v1/auth/refresh    → Rotate refresh token → issue new JWT
5. POST /api/v1/auth/revoke     → Blacklist refresh token
```

JWT payload:
```json
{
  "sub": "<user_uuid>",
  "exp": "<expiry_timestamp>"
}
```

---

## Event-Driven Architecture

Modules communicate through events — never direct cross-module imports.

```
Invoice Created
    ↓
EventDispatcher.publish(InvoiceCreatedEvent)
    ↓
┌─────────────────────────────────────┐
│  InventoryAgent   → reduce stock    │
│  FinanceAgent     → record income   │
│  CEOAgent         → update KPIs     │
│  NotificationSvc  → send receipt    │
└─────────────────────────────────────┘
```

Event types live in `app/core/events/types.py`.

---

## API Conventions

- **Base path:** `/api/v1/`
- **Auth endpoints:** `/api/v1/auth/`
- **User endpoints:** `/api/v1/users/`
- **Org endpoints:** `/api/v1/organizations/`
- **AI endpoints:** `/api/v1/organizations/{org_id}/ai/`
- All responses use **camelCase** in JSON
- All IDs are **UUIDs** (never integers)
- Pagination: `?page=1&page_size=20`
- Soft deletes: `is_deleted=true` — never hard delete business data
- AI streaming: `Content-Type: text/event-stream` (SSE), `event: end` signals completion

---

## Coding Standards

### Naming
- **Files:** `snake_case.py`
- **Classes:** `PascalCase`
- **Functions/variables:** `snake_case`
- **Constants:** `UPPER_SNAKE_CASE`
- **Database tables:** `snake_case` (plural)
- **Pydantic schemas:** `ModelNameCreate`, `ModelNameUpdate`, `ModelNameResponse`

### Layer Rules
- **Routers** → only handle HTTP, call services
- **Services** → business logic only, call repositories
- **Repositories** → database queries only, no business logic
- **Models** → SQLAlchemy only, no business logic
- **Schemas** → Pydantic only, no database logic

### Must-Haves in Every Module
- `models.py` — SQLAlchemy models
- `schemas.py` — Pydantic request/response schemas
- `services.py` — Business logic
- `repositories.py` — DB queries
- `router.py` — FastAPI routes

---

## Security Rules

1. **Passwords** — always hashed with Argon2 (passlib), never stored plain
2. **JWT secrets** — loaded from environment variables, never hardcoded
3. **Organization scoping** — every query filtered by `organization_id`
4. **Soft deletes** — `is_deleted` flag; never hard-delete business records
5. **Audit logs** — every write operation logs to `audit_logs`
6. **CORS** — whitelist only; configured in `core/config.py`
7. **Rate limiting** — to be implemented in `middleware/`
8. **AI configuration in `ai_settings` only** — model names, temperatures, and token limits must never be hardcoded in providers or agents
9. **Provider abstraction preserved** — pipeline never imports a concrete provider directly

---

## AI Runtime Flow

```
POST /organizations/{org_id}/ai/chat
        │
    router.py (ai_conversations)
        │
    AIConversationService.chat_stream()
        │
    AIExecutionPipeline.execute()
        │
    ┌──────────────────────────────────┐
    │  1. Resolve Agent (registry)     │
    │  2. Safety Guards (injection/PII)│
    │  3. Build Prompt (builder)       │
    │  4. Load Conversation History    │
    │  5. Stream → Provider            │
    │  6. Persist Messages (DB)        │
    │  7. Log Telemetry                │
    └──────────────────────────────────┘
        │
    GoogleProvider.stream()
        │
    SSE chunks → client
```

---

*Last updated: Sprint 004 complete — July 2026*
