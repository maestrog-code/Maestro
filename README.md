# MAESTRO

> **Your AI Executive Team.**

MAESTRO is an AI-powered business operating system for small and medium businesses.
It gives every organization a suite of specialized AI executives — CEO, CFO, COO, and more —
that analyse the business and provide proactive, actionable guidance grounded in each
organization's own data.

---

## Project Status

| Sprint | Goal | Status |
|---|---|---|
| 001 | Backend Foundation | ✅ Done |
| 002 | Authentication & Security | ✅ Done |
| 003 | Organizations & Multi-tenancy | ✅ Done |
| 004 | AI Executive Engine v1 | ✅ Done |
| 005 | Organizational Knowledge Engine | ✅ Done |
| 006 | Agent Memory System | ✅ Done — `sprint-006` |
| v0.1.0 | Stabilisation Milestone | 🔄 In Progress |
| 007 | Agent Orchestration Engine | ⬜ Planned |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12 + FastAPI |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 async |
| AI Provider | Google Gemini (gemini-2.5-pro) |
| Cache / Queue | Redis 7 + Celery |
| Migrations | Alembic |
| CI | GitHub Actions (Python 3.12) |
| Mobile | Flutter *(Phase 4)* |
| Web | React/Vite scaffold *(Phase 5 product work is out of scope for v0.1)* |

---

## Repository Structure

```
Maestro/
├── backend/maestro/      ← FastAPI application
│   ├── app/
│   │   ├── ai/           ← AI Executive Engine (providers, agents, pipeline)
│   │   ├── core/         ← Auth, config, database, events
│   │   └── modules/      ← organizations, users, ai_conversations
│   └── alembic/          ← Database migrations
├── mobile/               ← Flutter app (Phase 4)
├── web/                  ← React/Vite scaffold (Phase 5 product work)
├── docs/                 ← Architecture, roadmap, AI context documents
└── prompts/              ← Sprint CTO review packages
```

---

## Getting Started

See [`backend/maestro/README.md`](backend/maestro/README.md) for full setup instructions.

**Quick start (Docker):**
```bash
cd backend/maestro
docker compose up --build
```

**Run migrations:**
```bash
alembic upgrade head
```

> **Python runtime:** This project requires **Python 3.12**. See `.python-version`.

---

## Documentation

| Document | Purpose |
|---|---|
| [`docs/AI_CONTEXT.md`](docs/AI_CONTEXT.md) | **Start here** — full project context for AI tools |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture and design decisions |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Sprint plan and milestone definitions |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Architecture decision records |

---

*Sprint 006 complete — tag `sprint-006` — July 2026*

> **v0.1.0 stabilisation note:** the v0.1 milestone is backend/API-first. The
> `web/` folder is currently a scaffold and is not a release blocker unless the
> milestone scope is explicitly expanded to include the web product.
