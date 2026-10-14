# MAESTRO — Sprint 003 Brief for ChatGPT (CTO Review)

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

## What Is Done (Sprints 001 & 002 — COMPLETE ✅ — merged to main)

### Infrastructure
- FastAPI 0.110.0 + Python 3.12 backend
- SQLAlchemy 2.0 async with PostgreSQL 16
- Redis + Celery workers
- Root `docker-compose.yml` (api, db, redis, celery_worker)
- Alembic configured + `001_initial_schema.py` migration created

### Architecture
- Clean modular architecture:
  - `core/` — auth, config, events, security
  - `modules/` — users, organizations, permissions
  - `ai/` — agents, memory, router, tools (scaffolded, empty)
  - `shared/utils/repository.py` — Full CRUD `BaseRepository`
  - `api/v1/router.py` — Routes registered

### Data Models (all extend `TimestampedModel` with UUID PKs, soft delete, audit, version)
- `users` — email, hashed_password, first_name, last_name, is_active, is_verified
- `organizations` — name, slug
- `organization_members` — organization_id, user_id, role_id, status
- `roles` — name, description, organization_id
- `permissions` — name, resource, action
- `role_permissions` — role_id, permission_id
- `refresh_tokens` — token, user_id, expires_at, revoked_at
- `audit_logs` — who, what, resource, organization_id, ip, user_agent, details

### Authentication (Live Endpoints)
- `POST /api/v1/auth/register` — Create user, issue JWT + refresh token
- `POST /api/v1/auth/login` — Verify password, issue JWT + refresh token
- `POST /api/v1/auth/refresh` — Stub (placeholder response)
- `POST /api/v1/auth/revoke` — Stub (placeholder response)
- `POST /api/v1/auth/verify-email` — Stub
- `POST /api/v1/auth/password-reset` — Stub
- `GET /api/v1/health` — Health check with DB ping

### Security
- Argon2 password hashing (passlib)
- JWT access tokens (python-jose) — 30 min expiry
- Refresh tokens stored in DB — 7 day expiry
- `get_current_user` FastAPI dependency in `dependencies/auth.py`

### Tests
- `tests/test_auth_e2e.py` — 6 tests covering register, login, duplicate email, wrong password, full flow

### Docs
- `docs/PROJECT_VISION.md` — Vision, principles, AI team design
- `docs/ARCHITECTURE.md` — Tech stack, folder structure, DB schema, API conventions
- `docs/ROADMAP.md` — Sprint-by-sprint plan
- `docs/DECISIONS.md` — 14 locked architectural decisions
- `docs/AI_CONTEXT.md` — Master context (feed to any AI before coding)

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

---

## Sprint 003 — User & Organization Management

### Goal
By the end of Sprint 003, a user should be able to:
1. View their own profile
2. Update their profile
3. Create an organization
4. List all their organizations
5. Get a single organization's details
6. Invite another user (by email) to their organization
7. Remove a member from their organization
8. Assign a role to a member

All endpoints must be protected by JWT. The `get_current_user` dependency already exists.

### Branch
`feature/user-org-management`

### Endpoints to Build

#### Users
```
GET    /api/v1/users/me                              → UserResponse
PATCH  /api/v1/users/me                              → UserResponse
```

#### Organizations
```
POST   /api/v1/organizations/                        → OrganizationResponse
GET    /api/v1/organizations/                        → List[OrganizationResponse]
GET    /api/v1/organizations/{org_id}                → OrganizationResponse
```

#### Organization Members
```
POST   /api/v1/organizations/{org_id}/members        → MemberResponse  (invite by email)
DELETE /api/v1/organizations/{org_id}/members/{user_id}  → 204
PATCH  /api/v1/organizations/{org_id}/members/{user_id}/role → MemberResponse
```

### Business Rules
- When a user creates an organization, they are automatically added as a member with a system role "owner"
- Only existing users can be invited (look up by email)
- Only organization members can view or modify an organization
- Only the owner can invite/remove members or change roles
- `slug` is auto-generated from `name` (lowercase, hyphens) — must be unique

### New Schemas Needed
```python
# organizations
class OrganizationCreate(BaseModel):
    name: str

class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# members
class MemberInvite(BaseModel):
    email: EmailStr
    role_id: Optional[UUID] = None

class MemberRoleUpdate(BaseModel):
    role_id: UUID

class MemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    organization_id: UUID
    role_id: Optional[UUID]
    status: str
    model_config = ConfigDict(from_attributes=True)
```

### Files to Create / Modify

#### [NEW] `modules/organizations/schemas.py`
#### [NEW] `modules/organizations/repositories.py`
#### [NEW] `modules/organizations/services.py`
#### [NEW] `modules/organizations/router.py`
#### [MODIFY] `modules/users/router.py` — add `/me` endpoints
#### [MODIFY] `api/v1/router.py` — register new routers
#### [NEW] `tests/test_users_e2e.py`
#### [NEW] `tests/test_organizations_e2e.py`

### Definition of Done
- [ ] All 8 endpoints implemented and returning correct responses
- [ ] All endpoints protected by `get_current_user` dependency
- [ ] Organization creator is auto-added as "owner" member
- [ ] Slug auto-generated from name
- [ ] Tests written and passing
- [ ] Routers registered in `api/v1/router.py`
- [ ] Branch merged to `main`

---

## Your Role (ChatGPT)

For Sprint 003:
1. Review this plan and confirm or improve it
2. Provide a detailed Gemini/Antigravity prompt for each file to be built
3. Review any code I share for security, architecture, and correctness
4. Flag anything that would create technical debt

The implementation will be done in Antigravity IDE.
After each file is built, I will share it here for your review.

---

*Repository: https://github.com/maestrog-code/Maestro*
*Current branch: main (Sprint 002 complete)*
*Next branch: feature/user-org-management*
