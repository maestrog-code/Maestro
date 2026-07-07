# MAESTRO — Decision Log

> Every significant architectural or product decision is recorded here.
> Before changing any of these, discuss and update this document.

---

## DEC-001 — Platform Name
**Decision:** MAESTRO
**Date:** Sprint 000
**Reason:** A maestro coordinates many specialists into one performance — exactly what this platform does for business operations and AI agents.

---

## DEC-002 — Multi-Tenant SaaS
**Decision:** Organization-scoped multi-tenancy. One user can own multiple organizations.
**Date:** Sprint 000
**Reason:** Enables a single business owner to run multiple businesses on one account, which is common in the target market.

---

## DEC-003 — Mobile-First
**Decision:** Flutter for mobile. Mobile is the primary target device.
**Date:** Sprint 000
**Reason:** East African SMB market is predominantly mobile. Most business owners operate from phones.

---

## DEC-004 — Multi-Language and Multi-Currency from Day One
**Decision:** Design all data models and UI to support multiple languages and currencies from Sprint 001.
**Date:** Sprint 000
**Reason:** Retrofitting i18n and multi-currency after launch is extremely expensive. Building for it early costs very little.

---

## DEC-005 — UUID Primary Keys
**Decision:** All tables use UUID primary keys. Never use auto-increment integers.
**Date:** Sprint 001 (CTO Review)
**Reason:** Better SaaS security (IDs are not guessable), better distributed system compatibility, easier to merge data across tenants or environments.

---

## DEC-006 — Modular Monolith Architecture
**Decision:** Start as a modular monolith. Modules communicate through events, not direct imports.
**Date:** Sprint 001 (CTO Review)
**Reason:** Microservices at this stage would introduce unnecessary complexity and cost. The event-driven modular approach allows future extraction into microservices with minimal rework.

---

## DEC-007 — Multi-Agent AI Design
**Decision:** Build the AI as a team of specialized agents (CEO, CFO, COO, Marketing, Sales, Support, Data) rather than one general chatbot.
**Date:** Sprint 001
**Reason:** Specialized agents are more extensible, more accurate within their domain, and align with the "orchestra" theme of MAESTRO. New capabilities can be added as new agents without redesigning the system.

---

## DEC-008 — Primary AI: Gemini (Google AI)
**Decision:** Use Gemini (via Google AI Pro subscription) as the primary AI engine.
**Date:** Sprint 001
**Reason:** Large context windows for reviewing full codebases, excellent code generation, included in existing subscription (zero extra cost during development).

---

## DEC-009 — Primary Development Environment: Antigravity IDE
**Decision:** Use Antigravity IDE as the primary implementation tool.
**Date:** Sprint 001
**Reason:** Antigravity works inside existing projects rather than generating isolated snippets. Better suited for a codebase that will grow to hundreds of files.
**Division of responsibility:**
- ChatGPT → System Architect, product decisions, code review
- Antigravity IDE → Implementation (writes and modifies code)
- Gemini 2.5 Pro → Specialist for complex algorithms, large refactors, AI logic

---

## DEC-010 — Soft Deletes
**Decision:** Never hard-delete business data. Use `is_deleted` flag on `TimestampedModel`.
**Date:** Sprint 002
**Reason:** Business records may be needed for audits, tax, or recovery. Soft deletes are standard in SaaS platforms.

---

## DEC-011 — Optimistic Locking
**Decision:** All models include a `version` column, used as the SQLAlchemy `version_id_col`.
**Date:** Sprint 002
**Reason:** Prevents race conditions when multiple users or agent processes update the same record simultaneously.

---

## DEC-012 — Event Bus Architecture
**Decision:** All cross-module side effects happen through events dispatched to the EventDispatcher.
**Date:** Sprint 002
**Reason:** Prevents tight coupling between modules. Makes the system easier to extend (new handlers can react to existing events without touching the source module).

---

## DEC-013 — Argon2 for Password Hashing
**Decision:** Use Argon2 (via `passlib[argon2]`) for password hashing.
**Date:** Sprint 002
**Reason:** Argon2 won the Password Hashing Competition and is the current recommended standard. It is memory-hard, making brute-force attacks expensive.

---

## DEC-014 — JWT + Refresh Token Authentication
**Decision:** Access tokens are short-lived JWTs. Refresh tokens are stored in the database and can be revoked.
**Date:** Sprint 002
**Reason:** Short-lived access tokens limit exposure. Stored refresh tokens allow revocation (logout from all devices, security lockout).

---

## DEC-015 — Vector Storage with pgvector
**Decision:** Use PostgreSQL with the `pgvector` extension for storing and querying embeddings, rather than a standalone vector database like Pinecone.
**Date:** Sprint 005
**Reason:** Reduces infrastructure complexity by keeping transactional and vector data in the same datastore. Allows simple joins between business data and embeddings, making organization-scoping enforced at the SQL level.

---

## DEC-016 — Hybrid Deduplicated Memory Extraction
**Decision:** Memory extraction is handled asynchronously via Celery using Gemini's Structured Output functionality, with vector similarity deduplication during insertion.
**Date:** Sprint 006
**Reason:** Prevents LLM extraction latency from blocking the main conversation loop. Vector similarity checks (threshold > 0.92) before inserting a new memory prevents the database from exploding with duplicate facts over time.

---

*Last updated: Sprint 006 — July 2026*
