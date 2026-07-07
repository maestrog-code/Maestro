# MAESTRO — Sprint 005 Brief for ChatGPT (CTO Review)

Paste this entire document into ChatGPT to resume the MAESTRO project.

---

## Project Recap

You are the CTO / Chief Architect of MAESTRO.
MAESTRO is an AI-powered multi-tenant SaaS platform for small and medium businesses.
Tagline: "Your AI Executive Team."
Repository: `maestrog-code/Maestro` on GitHub

We are using:
- Antigravity IDE as the implementation engineer (writes the code)
- ChatGPT as the CTO / Architect (reviews, directs, plans)
- Gemini 2.5 Pro for complex AI and large refactoring tasks

---

## What Is Done (Sprints 001–004 — COMPLETE ✅ — merged to main)

### Infrastructure & Foundation (Sprint 001)
- FastAPI 0.110.0 + Python 3.12 backend
- SQLAlchemy 2.0 async with PostgreSQL 16
- Redis + Celery workers
- Root `docker-compose.yml` (api, db, redis, celery_worker)
- Alembic configured + `001_initial_schema.py` migration
- GitHub Actions CI (`backend-ci.yml`)

### Authentication & Security (Sprint 002)
- User registration, login, JWT access tokens (python-jose), Argon2 password hashing
- Refresh token rotation, token revocation, audit logging
- `get_current_user` FastAPI dependency in `dependencies/auth.py`

### Organizations & RBAC (Sprint 003)
- `Organization`, `OrganizationMember`, `Role`, `Permission`, `RolePermission` models
- Full CRUD for users and organizations
- Membership management: invite by email, remove member, assign role
- `require_member`, `require_owner` authorization helpers
- Organization-scoped multi-tenancy enforced throughout

### AI Executive Engine (Sprint 004)
- `app/core/ai_settings.py` — AI runtime config via `AI_` env prefix
- `app/ai/providers/base.py` — `BaseLLMProvider` (generate, stream, embeddings)
- `app/ai/providers/google.py` — Google Gemini (`google-genai` SDK, `gemini-2.5-pro`)
- `app/ai/agents/registry.py` — `AgentRegistry` singleton
- `app/ai/agents/definitions/` — CEO, CFO, COO, CMO, Sales, Support, Analytics agents
- `app/ai/prompts/builder.py` — Markdown template renderer with `{{variable}}` interpolation
- `app/ai/prompts/templates/` — Externalized system prompts (`ceo_system.md`, `cfo_system.md`, etc.)
- `app/ai/tools/base.py` — `BaseTool` abstract class with `get_json_schema()`
- `app/ai/pipeline/executor.py` — `AIExecutionPipeline` (agent → safety → prompt → provider → persist → telemetry)
- `app/ai/pipeline/tool_executor.py` — `ToolExecutor` (permission check → validation → timeout → retry → audit log)
- `app/ai/safety/guards.py` — Prompt injection detection + PII redaction guards
- `app/ai/telemetry/logger.py` — Structured execution telemetry (provider, model, cost, retries, latency)
- `app/modules/ai_conversations/` — Conversation persistence module (models/schemas/services/repos/router)
- `POST /organizations/{org_id}/ai/chat` — SSE streaming endpoint
- `alembic/versions/002_ai_conversations.py` — DB migration (`ai_conversations`, `ai_messages`)
- Tests with mock provider

---

## Current Database Schema

| Migration | Tables |
|---|---|
| `001_initial_schema` | `users`, `organizations`, `organization_members`, `roles`, `permissions`, `role_permissions`, `refresh_tokens`, `audit_logs` |
| `002_ai_conversations` | `ai_conversations`, `ai_messages`, `message_role_enum` (PostgreSQL ENUM) |

All tables extend `TimestampedModel`:
```
id (UUID PK), created_at, updated_at, is_deleted, deleted_at, created_by, updated_by, version
```

---

## Current Folder Structure (relevant to AI)

```
backend/maestro/app/
├── ai/
│   ├── agents/
│   │   ├── definitions/     ← ceo.py, cfo.py, coo.py, etc.
│   │   └── registry.py
│   ├── memory/              ← EMPTY — reserved for Sprint 005 vector memory
│   ├── pipeline/
│   │   ├── executor.py
│   │   └── tool_executor.py
│   ├── prompts/
│   │   ├── builder.py
│   │   └── templates/
│   ├── providers/
│   │   ├── base.py          ← BaseLLMProvider (generate, stream, embeddings)
│   │   └── google.py
│   ├── safety/guards.py
│   ├── telemetry/logger.py
│   ├── tools/base.py        ← BaseTool abstract class
│   └── schemas.py
├── modules/
│   ├── ai_conversations/
│   ├── organizations/
│   ├── permissions/
│   └── users/
├── core/
│   ├── ai_settings.py       ← AI_ env prefix (model, temperature, tokens, etc.)
│   └── ...
└── ...
```

---

## Architecture Rules (Non-Negotiable)

1. All PKs are UUIDs — never integers
2. All tables extend `TimestampedModel`
3. Soft deletes only — never `DELETE FROM` business tables
4. Every business query filtered by `organization_id`
5. Modules never import from each other — use event bus
6. Layer discipline: Router → Service → Repository → DB
7. Passwords = Argon2 only
8. Secrets from environment variables only
9. AI configuration in `ai_settings` only — never hardcode model names or temperatures
10. Provider abstraction must be preserved — pipeline never imports a concrete provider directly
11. Every Alembic migration must have a `downgrade()` path

---

## Sprint 005 — Organizational Knowledge Engine

### Goal
Give every AI executive access to organization-specific knowledge via a RAG pipeline.
Transform MAESTRO's executives from conversational assistants into AI systems that can
answer questions using each customer's own documents.

### Branch
`feature/organizational-knowledge-engine`

### Deliverables

#### 1. Knowledge Sources
Allow organizations to upload and manage documents:
- File types: PDF, DOCX, TXT, Markdown
- Notes (short-form, created inline via API)
- Policies and SOPs

#### 2. Document Processing Pipeline
- Text extraction from uploaded files
- Chunking strategy (section-aware or by token count, ~512 tokens per chunk with overlap)
- Metadata generation per chunk: `source_file`, `doc_type`, `chunk_index`, `organization_id`

#### 3. Embeddings
- Use existing `BaseLLMProvider.embed()` (already defined in `providers/base.py`)
- Provider: Google `text-embedding-004`
- Batch indexing (process all chunks for a document)
- Re-index support (delete old vectors, re-embed)

#### 4. Vector Store
- Use **pgvector** (PostgreSQL extension) to keep the stack minimal
- Organization-scoped: all vector queries must filter by `organization_id`
- Semantic similarity search
- Metadata filtering (by doc_type, date, tags)

#### 5. Retrieval Pipeline
- Semantic search (vector similarity)
- Keyword fallback (PostgreSQL full-text search) — hybrid if feasible
- Context assembly: format top-K chunks into a structured context block for prompt injection
- Citation / source attribution: include `[Source: filename, chunk N]` in responses

#### 6. Knowledge Tools (extend `BaseTool`)
```
search_knowledge_base(query: str, top_k: int = 5) → List[ChunkResult]
get_document(document_id: UUID) → DocumentResponse
list_documents(page: int, page_size: int) → List[DocumentResponse]
```
These tools are registered in the agent system and available to all AI executives.

#### 7. Security
- Strict `organization_id` isolation — never leak documents across organizations
- Permission check before retrieval (user must be an org member)
- Document-level access: `visibility` field (`org` | `private`) on each document

---

### New Database Tables (Sprint 005 — Migration `003_knowledge_engine`)

```
knowledge_documents
├── id (UUID PK)
├── organization_id (FK → organizations, CASCADE)
├── title
├── doc_type  (enum: file | note | policy | sop)
├── file_name (nullable — original filename)
├── file_path (nullable — storage path)
├── mime_type (nullable)
├── content   (TEXT — extracted raw text)
├── status    (enum: pending | processing | indexed | failed)
├── visibility (enum: org | private)
├── created_by (FK → users)
└── [TimestampedModel fields]
INDEX (organization_id)
INDEX (organization_id, doc_type)

knowledge_chunks
├── id (UUID PK)
├── document_id (FK → knowledge_documents, CASCADE)
├── organization_id (FK → organizations, CASCADE)  ← denormalized for fast filtering
├── chunk_index (int)
├── content (TEXT)
├── embedding (vector(768))  ← pgvector column
├── token_count (int)
└── [TimestampedModel fields]
INDEX (document_id)
INDEX using ivfflat on embedding (vector_cosine_ops)  ← pgvector ANN index

knowledge_tags
├── id (UUID PK)
├── document_id (FK → knowledge_documents, CASCADE)
├── tag (varchar)
└── [TimestampedModel fields]
INDEX (document_id)
```

---

### New API Endpoints

```
# Document management
POST   /api/v1/organizations/{org_id}/knowledge/documents          → DocumentResponse   (upload or create note)
GET    /api/v1/organizations/{org_id}/knowledge/documents          → List[DocumentResponse]
GET    /api/v1/organizations/{org_id}/knowledge/documents/{doc_id} → DocumentResponse
DELETE /api/v1/organizations/{org_id}/knowledge/documents/{doc_id} → 204

# Search
POST   /api/v1/organizations/{org_id}/knowledge/search             → List[ChunkResult]  (body: {query, top_k})

# Reindex
POST   /api/v1/organizations/{org_id}/knowledge/documents/{doc_id}/reindex → 202
```

---

### Files to Create / Modify

#### [NEW] `app/modules/knowledge/`
- `models.py` — `KnowledgeDocument`, `KnowledgeChunk`, `KnowledgeTag` SQLAlchemy models
- `schemas.py` — `DocumentCreate`, `DocumentResponse`, `ChunkResult`, `SearchRequest`
- `repositories.py` — CRUD + vector search queries
- `services.py` — Upload handling, chunking, embedding, indexing, search orchestration
- `router.py` — FastAPI routes

#### [NEW] `app/ai/tools/knowledge_tools.py`
- `SearchKnowledgeBaseTool(BaseTool)` — calls `KnowledgeService.search()`
- `GetDocumentTool(BaseTool)` — retrieves a document
- `ListDocumentsTool(BaseTool)` — lists documents for the org

#### [MODIFY] `app/ai/agents/definitions/*.py`
- Register `SearchKnowledgeBaseTool`, `GetDocumentTool`, `ListDocumentsTool` on all agent definitions

#### [MODIFY] `app/ai/pipeline/executor.py`
- Inject retrieved knowledge context into the prompt before sending to provider
- Add retrieval step between safety guards and prompt building

#### [MODIFY] `app/core/ai_settings.py`
- Add: `AI_EMBEDDING_MODEL`, `AI_VECTOR_SEARCH_TOP_K`, `AI_CHUNK_SIZE`, `AI_CHUNK_OVERLAP`

#### [MODIFY] `app/ai/memory/`
- This folder was reserved for Sprint 005 — use it for the retrieval memory layer

#### [NEW] `alembic/versions/003_knowledge_engine.py`
- Creates `knowledge_documents`, `knowledge_chunks`, `knowledge_tags`
- Enables `pgvector` extension
- Creates ivfflat index on `knowledge_chunks.embedding`
- Must include `downgrade()`

#### [MODIFY] `docker-compose.yml`
- Ensure `pgvector` is enabled on the PostgreSQL 16 container

#### [NEW] `tests/test_knowledge_e2e.py`
- Test document upload (note creation)
- Test semantic search
- Test knowledge tool invocation from the AI pipeline

---

### Definition of Done

- [ ] `knowledge_documents` and `knowledge_chunks` tables created via Alembic migration
- [ ] pgvector enabled in Docker Postgres
- [ ] File upload and note creation endpoints working
- [ ] Text extraction working for TXT and Markdown (PDF/DOCX via `pypdf2` / `python-docx`)
- [ ] Chunking pipeline splits content into overlapping token-bounded chunks
- [ ] Embedding pipeline calls `BaseLLMProvider.embed()` and stores vectors in `knowledge_chunks`
- [ ] Semantic search returns top-K chunks ordered by cosine similarity
- [ ] `SearchKnowledgeBaseTool`, `GetDocumentTool`, `ListDocumentsTool` implemented
- [ ] Tools registered on CEO and CFO agent definitions (minimum)
- [ ] `AIExecutionPipeline` retrieves and injects knowledge context before prompt assembly
- [ ] All endpoints protected by `get_current_user` + `require_member`
- [ ] Organization isolation enforced at every query
- [ ] Re-index endpoint working
- [ ] Tests written and passing
- [ ] Alembic migration has a `downgrade()` path
- [ ] Branch merged to `main`

---

## Your Role (ChatGPT)

For Sprint 005:
1. Review this plan — confirm, challenge, or improve it
2. Decide: pgvector vs Pinecone for this stage (recommendation expected)
3. Decide: chunking strategy — fixed token size vs section-aware (recommendation expected)
4. Provide a detailed Antigravity/Gemini prompt for each file to be built
5. Review any code I share for security, architecture, and correctness
6. Flag anything that would create technical debt or violate the architecture rules above

The implementation will be done in Antigravity IDE.
After each file is built, I will share it here for your review.

---

*Repository: https://github.com/maestrog-code/Maestro*
*Current branch: main (Sprint 004 complete — score: 10/10)*
*Next branch: feature/organizational-knowledge-engine*
*v0.1.0 stabilisation milestone should be completed before Sprint 005 coding begins*
