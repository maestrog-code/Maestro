# CTO Review: Sprint 005

**Status:** ✅ Approved with architectural refinements  
**Overall score:** 9.9/10

This is the strongest sprint plan produced so far. Compared to Sprint 004, it is more cohesive and has a clear architectural objective: **give AI executives organizational knowledge while preserving modularity**.

---

## 1. Scope Discipline & Simplification

From what was described, the Sprint 005 proposal is **architecturally consistent** with everything built so far. The additions like `StorageProvider`, `VectorStore`, hybrid chunking, and `pgvector` all fit the direction of MAESTRO and avoid future lock-in.

### What is approved for Sprint 005:
* ✅ `StorageProvider` abstraction (implement `LocalStorageProvider` only)
* ✅ `VectorStore` abstraction (implement `PgVectorStore` only)
* ✅ `pgvector`
* ✅ Hybrid chunking
* ✅ Knowledge document management
* ✅ Embedding pipeline
* ✅ Semantic retrieval
* ✅ Knowledge tools
* ✅ Prompt context injection
* ✅ Organization isolation
* ✅ Re-indexing
* ✅ End-to-end tests

### pgvector vs Pinecone
**Recommendation:** Use `pgvector`. Do **not** introduce Pinecone yet.  
**Why:** MAESTRO already uses PostgreSQL, SQLAlchemy, and Alembic. Adding pgvector gives you one database, one backup strategy, one migration system, and one deployment target. For SMB customers this is a much simpler operational model. Later, if enterprise customers need billions of vectors, we can introduce abstractions for external vector databases. Sprint 005 should not solve a problem we don't have yet.

---

## 2. Mandatory Architectural Refinements

### Abstractions before implementations
The system must be built open for extension without forcing a rewrite later.
- Implement an **`EmbeddingProvider`** abstraction instead of coupling directly to Gemini. This allows future swaps to OpenAI, Voyage AI, or local embeddings.
- Implement a **`StorageProvider`** abstraction (starting with `LocalStorageProvider` configured to save files under `<org_id>/<doc_uuid>/<filename>` to prevent collisions).
- Implement document parsing via a **`BaseParser`** abstraction, decoupling file extraction (`PDFParser`, `DOCXParser`, etc.) from chunking logic.

### Data Model Separation
Move embeddings into a dedicated `knowledge_embeddings` table separate from the `knowledge_chunks` table.
- `knowledge_chunks`: Stores text content and structural metadata.
- `knowledge_embeddings`: Stores the vector (`VECTOR(768)`) alongside provenance data (`provider`, `model`, `dimensions`).
- **Why:** This decoupling enables targeted re-indexing without touching the core knowledge documents, and supports simultaneous A/B testing of multiple embedding models in the future.

### Async Ingestion
Treat document ingestion as an asynchronous job from the start. Never embed synchronously.
- **Flow:** Upload → Pending → Celery Task → Extract (BaseParser) → Chunk (HybridChunker) → Embed (EmbeddingProvider) → Index (VectorStore).

### Security & Organization Isolation
This is exactly the right security model.
- Every vector search should explicitly require the `organization_id`.
- There should be **no code path** that allows an unrestricted similarity search. Cross-tenant data leakage is unacceptable.

### Prompt Builder Context Injection
Don't concatenate strings. Create a dedicated `PromptContext` object to manage the injection of retrieved organizational knowledge directly into the LLM system prompt.
