# MAESTRO — Sprint 006 Brief for ChatGPT (CTO Review)

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
- Gemini 3.1 Pro for complex AI and large refactoring tasks

---

## What Is Done (Sprints 001–005 — COMPLETE ✅ — merged to main)

### Sprints 001–003: Core Foundation
- FastAPI, SQLAlchemy (async), PostgreSQL 16, Redis, Celery
- JWT Authentication, Argon2, Refresh Tokens
- Organization-scoped Multi-tenancy, RBAC (Role-Based Access Control)

### Sprint 004: AI Executive Engine
- `BaseLLMProvider` abstractions, Gemini integration
- `AgentRegistry` and AI executives (CEO, CFO, COO, etc.)
- Tool execution pipeline, Prompt templating, Safety guards, Telemetry
- Conversation persistence (`ai_conversations`, `ai_messages`), SSE streaming

### Sprint 005: Organizational Knowledge Engine
- Document upload and async Celery ingestion pipeline (`Text`, `PDF`, `DOCX`)
- Separate tables for `knowledge_chunks` and `knowledge_embeddings` (for multi-model testing)
- `PgVectorStore` utilizing PostgreSQL `pgvector` with `ivfflat` indexing
- Implicit RAG context injection into the `PromptContext`
- AI Tools: `SearchKnowledgeBaseTool`, `GetDocumentTool`, `ListDocumentsTool`
- Strict `organization_id` isolation to prevent cross-tenant data leakage

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

## Sprint 006 — The Memory System (Long-Term Agent Memory)

### Goal
Equip AI executives with long-term, cross-conversation memory. While Sprint 005 enabled agents to retrieve static documents (RAG), Sprint 006 will allow agents to "remember" user preferences, past decisions, strategic goals, and context across multiple sessions, forming a continuous working relationship.

### Branch
`feature/agent-memory-system`

### Deliverables

#### 1. Memory Store (Database)
- A new table `agent_memories` to store semantic memories extracted from conversations.
- Memories must be scoped by `organization_id`, `user_id` (optional, for personal context), and `agent_id` (optional, for role-specific memory).
- Use `pgvector` to store the semantic representation of each memory to allow dynamic retrieval based on current conversation context.

#### 2. Memory Extraction Pipeline (Async)
- After a conversation ends (or asynchronously during the chat), run a background Celery task to summarize and extract new facts, decisions, or user preferences.
- Deduplicate or update existing conflicting memories to prevent memory bloat.

#### 3. Contextual Memory Injection
- Update the `AIExecutionPipeline` and `PromptContext` to retrieve not only *Knowledge Base Documents* (Sprint 005) but also *Relevant Past Memories* (Sprint 006).
- Format retrieved memories clearly in the system prompt (e.g., `## Past Context & Preferences`).

#### 4. Explicit Memory Management Tools
- Agents need tools to explicitly manage their memory if implicit extraction misses something.
- `remember_fact(fact: str, scope: str)`: Tool for the agent to save a specific, important decision or fact.
- `forget_fact(memory_id: UUID)`: Tool to delete obsolete information.

#### 5. User-Facing Memory Dashboard
- An API endpoint and schema to allow the human user to view, edit, or delete the memories the agents have formed about them or the organization.

---

### New Database Tables (Sprint 006 — Migration `004_memory_system`)

```
agent_memories
├── id (UUID PK)
├── organization_id (FK → organizations, CASCADE)
├── user_id (FK → users, CASCADE, nullable)       ← if the memory is specific to a user
├── agent_id (varchar, nullable)                  ← if the memory is specific to a role (e.g. "CFO")
├── content (TEXT)                                ← the extracted fact or preference
├── importance_score (float)                      ← weight/importance of the memory
├── embedding (vector(768))                       ← pgvector column for semantic retrieval
└── [TimestampedModel fields]
INDEX (organization_id)
INDEX using ivfflat on embedding (vector_cosine_ops)
```

---

### New API Endpoints

```
# Memory Management
GET    /api/v1/organizations/{org_id}/memories             → List[MemoryResponse]
POST   /api/v1/organizations/{org_id}/memories             → MemoryResponse (manual addition)
DELETE /api/v1/organizations/{org_id}/memories/{memory_id} → 204
```

---

### Definition of Done

- [ ] `agent_memories` table created via Alembic migration with `pgvector` column
- [ ] Async Celery task implemented to extract and consolidate memories from chat transcripts
- [ ] `AIExecutionPipeline` updated to inject relevant semantic memories into the `PromptContext`
- [ ] Explicit memory management tools (`remember_fact`, `forget_fact`) registered to agents
- [ ] User-facing CRUD API for managing agent memories implemented
- [ ] All endpoints and vector searches strictly scoped by `organization_id`
- [ ] E2E Tests written and passing
- [ ] Alembic migration has a `downgrade()` path
- [ ] Branch merged to `main`

---

## Your Role (ChatGPT)

For Sprint 006:
1. Review this plan — confirm, challenge, or improve it.
2. Decide on the memory extraction strategy: should it be asynchronous post-chat, or continuous via explicit tool calls during the chat? (Recommendation expected).
3. Provide a detailed Antigravity/Gemini prompt for each file to be built.
4. Review any code I share for security, architecture, and correctness.
5. Flag anything that would create technical debt or violate the architecture rules above.

The implementation will be done in Antigravity IDE.
After each file is built, I will share it here for your review.

---

*Repository: https://github.com/maestrog-code/Maestro*
*Current branch: main (Sprint 005 complete)*
*Next branch: feature/agent-memory-system*
