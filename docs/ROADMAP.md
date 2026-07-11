# MAESTRO — Development Roadmap

> Status as of Sprint 004 — July 2026
> Tag: `sprint-004` | Branch: `main`

---

## Phase 0 — Blueprint ✅ DONE

- [x] Project vision defined
- [x] Tech stack locked
- [x] Repository created (`maestrog-code/Maestro`)
- [x] Branching strategy established (`main` + `feature/*`)
- [x] `docs/`, `prompts/`, `scripts/`, `docker/` folders created
- [x] `ARCHITECTURE.md` — published
- [x] `ROADMAP.md` — published
- [x] `DECISIONS.md` — published
- [x] `AI_CONTEXT.md` — published

---

## Phase 1 — MAESTRO CORE ✅ DONE

### Sprint 001 — Backend Foundation ✅ DONE
**Goal:** FastAPI + PostgreSQL running in Docker

- [x] Clean architecture folder structure
- [x] `core/config.py` — Settings with Pydantic
- [x] `core/database.py` — Async SQLAlchemy engine
- [x] `core/logger.py` — Structured logging
- [x] `models/base.py` — `TimestampedModel` with UUID, soft delete, audit, optimistic locking
- [x] `workers/celery.py` — Celery + Redis integration
- [x] `api/v1/health.py` — Health check endpoint
- [x] `requirements.txt` — All dependencies pinned
- [x] `docker-compose.yml` — Development environment
- [x] Alembic initial migration

---

### Sprint 002 — Authentication Foundation ✅ DONE
**Goal:** User registration, login, JWT, refresh tokens

- [x] `modules/users/models.py` — `User` model
- [x] `core/auth/models.py` — `RefreshToken`, `AuditLog`
- [x] `core/auth/router.py` — `/register`, `/login`, `/refresh`, `/revoke`
- [x] `core/security/jwt.py` — `create_access_token`
- [x] `core/security/password.py` — Argon2 hashing
- [x] `dependencies/auth.py` — `get_current_user` dependency
- [x] `core/events/` — Event system scaffolded
- [x] Alembic migration `001_initial_schema`
- [x] E2E auth tests

---

### Sprint 003 — User & Organization Management ✅ DONE
**Goal:** Full CRUD for users and organizations; RBAC foundation

- [x] `GET /api/v1/users/me` — Current user profile
- [x] `PATCH /api/v1/users/me` — Update profile
- [x] `POST /api/v1/organizations/` — Create organization
- [x] `GET /api/v1/organizations/` — List user's organizations
- [x] `POST /api/v1/organizations/{id}/members` — Invite member
- [x] `DELETE /api/v1/organizations/{id}/members/{user_id}` — Remove member
- [x] Role assignment to members
- [x] Centralized authorization helpers: `require_member`, `require_owner`
- [x] Organization-scoped multi-tenancy enforced
- [x] E2E tests for users and organizations

---

### Sprint 004 — AI Executive Engine v1 ✅ DONE
**Goal:** Reusable AI execution platform; first working executive agents (CEO, CFO)

**Tag:** `sprint-004` | **Score:** 10/10 (CTO Approved)

- [x] `app/core/ai_settings.py` — AI runtime configuration (`AI_` env prefix)
- [x] `app/ai/providers/base.py` — `BaseLLMProvider` abstraction
- [x] `app/ai/providers/google.py` — Google Gemini implementation
- [x] `app/ai/agents/registry.py` — Agent registry
- [x] `app/ai/agents/definitions/ceo.py` — CEO agent definition
- [x] `app/ai/agents/definitions/cfo.py` — CFO agent definition
- [x] `app/ai/prompts/builder.py` — Markdown template renderer
- [x] `app/ai/prompts/templates/` — Externalized system prompts
- [x] `app/ai/tools/base.py` — `BaseTool` / `ToolExecutor`
- [x] `app/ai/pipeline/executor.py` — Orchestration pipeline
- [x] `app/ai/pipeline/tool_executor.py` — Validation, retries, timeouts, audit log
- [x] `app/ai/safety/guards.py` — Prompt injection + PII redaction guards
- [x] `app/ai/telemetry/logger.py` — Structured AI execution telemetry
- [x] `app/modules/ai_conversations/` — Conversation persistence module
- [x] `POST /organizations/{org_id}/ai/chat` — SSE streaming endpoint
- [x] `alembic/versions/002_ai_conversations.py` — DB migration
- [x] `.github/workflows/backend-ci.yml` — CI enforcing Python 3.12
- [x] `.python-version` — Runtime pinned at `3.12`
- [x] Tests with mock provider

---

## v0.1.0 Stabilisation Milestone 🔄 NEXT

> **Do not start Sprint 005 until this milestone is complete.**
> This investment prevents technical debt from accumulating as AI capabilities expand.

**Branch:** `feature/v0.1.0-stabilisation`

### Checklist

- [ ] CI passes consistently on `main` (no flaky tests)
- [ ] Docker build succeeds from a clean clone (`docker compose up --build`)
- [ ] Alembic migrations run clean from zero (`alembic upgrade head`)
- [ ] `README.md` (root) reflects current architecture and setup instructions
- [ ] `docs/ARCHITECTURE.md` updated to include AI layer and new tables
- [ ] `docs/AI_CONTEXT.md` updated with Sprint 004 completions and Sprint 005 goals
- [ ] OpenAPI docs (`/docs`) reviewed — all endpoints documented with correct schemas
- [ ] Development setup verified on a fresh machine
- [ ] `v0.1.0` tag created and pushed after all checks pass

**Scope note:** v0.1.0 stabilisation is backend/API-first. The React/Vite
`web/` scaffold is not a release blocker for this milestone.

---

## Phase 2 — AI Knowledge & Reasoning

### Sprint 005 — Organizational Knowledge Engine ✅ DONE
**Goal:** Give every AI executive access to organization-specific knowledge via RAG

**Tag:** `sprint-005` | **Score:** 9.9/10 (CTO Approved)

- [x] **Knowledge Sources**
  - File uploads (PDF, DOCX, TXT, Markdown)
  - Notes, policies, SOPs
- [x] **Document Processing**
  - Text extraction pipeline
  - Hybrid chunking strategy (semantic + token)
  - Metadata generation (source, type, date)
- [x] **Embeddings**
  - Pluggable embedding provider (Google `text-embedding-004`)
  - Celery async pipeline
- [x] **Vector Store**
  - Organization-scoped storage via `pgvector`
  - Semantic search
- [x] **Retrieval Pipeline**
  - Context assembly for prompt injection
  - Implicit background RAG during chat
- [x] **Knowledge Tools**
  - `search_knowledge_base`
  - `get_document`
  - `list_documents`
- [x] **Security**
  - Organization isolation
  - Permission-aware retrieval
- [x] DB migration `003_knowledge_engine.py`
- [x] End-to-end tests

---

### Sprint 006 — The Memory System (Long-Term Agent Memory) ✅ DONE
**Goal:** Transform MAESTRO into a long-term executive partner by equipping AI agents with persistent, type-aware memory across sessions.

**Tag:** `sprint-006` | **Score:** 9.95/10 (CTO Approved)

- [x] **Database Schema & Models**
  - `agent_memories`, `memory_embeddings`, `memory_access_logs`
  - Support for `MemoryType` (`FACT`, `GOAL`, `RELATIONSHIP`, etc.) and `MemoryStatus`
- [x] **Hybrid Memory Extraction Pipeline**
  - Explicit extraction tools (`remember_fact`, `forget_fact`)
  - Async Celery extraction via Gemini Structured Outputs
- [x] **Retrieval & Ranking**
  - Vector similarity search
  - Weighted ranking formula (`Similarity × Importance × Confidence × Recency × Access Frequency`)
- [x] **Prompt Injection Pipeline Update**
  - Inject memory context strictly *before* knowledge base context
- [x] **Sprint 006: Memory System** (Completed)
  - `AgentMemory` models with vectors
  - Implicit memory extraction via Celery
  - Hybrid Knowledge vs Memory abstractions

- [x] **Sprint 006.5: Memory Stabilization** (Completed)
  - `ConflictResolutionService` for LLM-based deduplication (`MERGE`, `SUPERSEDE`, `NEW`)
  - Exponential decay of memory importance (`decay_memories_task`)
  - Centralized `MemoryPolicy` for lifecycle control

- [x] **Sprint 007: Agent Orchestration Engine** ✅ DONE
  - [x] Task delegation via `delegate_task` tool
  - [x] Agent-to-agent routing and nested context management
  - [x] CEO scratchpad updates via `update_task_status`
  - [x] Task memory (multi-step conversations with parent_message_id)

- [x] **Sprint 008: Multi-Agent Streaming (SSE)** ✅ DONE
  - [x] Pydantic SSE StreamEvents (`TokenEvent`, `OrchestrationEvent`, etc.)
  - [x] Streaming context propagation and nested stream filtering
  - [x] Tool lifecycle hooks (`ToolCallEvent`)

---

## Phase 3 — Business Modules

### Sprint 009 — Frontend UI & SSE Consumption (Next.js) ✅ DONE
- [x] Next.js App Router scaffold
- [x] Zustand global state for orchestrator (`useChatStore`)
- [x] SSE streaming client with AbortController
- [x] Real-time dynamic UI for agent orchestration and tool loading
- [x] Premium Dark Mode aesthetic (Framer Motion, Tailwind Typography)
- [x] Sub-agent execution log streaming (Detail Drawer and Inline Telemetry Cards)

### Sprint 010 — Business Tools & Dashboards
- **Dashboards:** Revenue trends, KPI aggregation
- **Business Models (Option A):** Scaffold placeholder models (Invoices, Projects) to test real SQLAlchemy joins instead of JSON stubs.
- **AI Daily Briefing:** Scheduled Celery task (`generate_daily_briefings`) to prepare morning reports proactively.
- **Notifications:** Standard polling REST API (`GET /notifications`) for MVP alerts.

### Sprint 011 — Production Hardening
- Performance profiling and optimization
- Horizontal scaling validation
- Full observability stack (metrics, traces, alerts)
- Security review and penetration testing readiness
- Rate limiting and abuse protection

---

## Phase 4 — Mobile (Flutter)

### Sprint 011–016 — Flutter App
- Authentication screens
- Dashboard
- AI chat interface
- Inventory management
- Sales recording
- Customer list

---

## Phase 5 — Web & SaaS Scale

### Sprint 017+ — Web App & SaaS Infrastructure
- Next.js admin panel
- Subscription billing (Stripe + M-Pesa + Airtel Money)
- Multi-language UI
- Public API
- Plugin system
- Marketplace

---

## Milestone Definitions

| Milestone | Definition | Status |
|---|---|---|
| **v0.1.0** | All 4 core sprints merged, CI green, Docker verified | 🔄 In Progress |
| **Alpha** | Knowledge engine + at least 1 business module working | ⬜ Planned |
| **Beta** | All Phase 3 business modules + dashboards | ⬜ Planned |
| **MVP** | Mobile app + full AI executive suite | ⬜ Planned |
| **v1.0** | Payments + automation + paying customers | ⬜ Planned |
| **v2.0** | 100+ businesses, marketplace, public API | ⬜ Planned |

---

## Technical Debt Backlog

- **Database**: Adopt the native `pgvector.sqlalchemy` types during the next major database refactoring sprint. (Currently using a manual workaround `vector = Column(String)`).

---

*Last updated: Sprint 006 complete — July 2026*
