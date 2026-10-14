You are the Lead Backend Engineer for MAESTRO.

IMPORTANT

This is a production SaaS platform.

Never sacrifice architecture for simplicity.

Existing Stack

- FastAPI
- SQLAlchemy 2.0
- PostgreSQL
- Alembic
- Async
- Docker

Your task is NOT to build the entire app.

Your task is ONLY Sprint 002.

OBJECTIVES

Implement a production-grade multi-tenant authentication foundation.

Architecture

Use Modular Monolith architecture.

Implement the following modules:

modules/
    users/
    organizations/
    permissions/

Create these SQLAlchemy models using UUID primary keys:

User

Organization

OrganizationMember

Role

Permission

RefreshToken

AuditLog

Requirements

• SQLAlchemy 2.0
• Async
• UUID primary keys
• Soft delete support
• created_at
• updated_at
• created_by
• updated_by
• indexes
• constraints
• relationships
• Alembic migrations

Authentication

Implement

- Register

- Login

- JWT Access Token

- Refresh Token

- Password Hashing using Argon2

- Email Verification placeholders

- Password Reset placeholders

Security

RBAC

Organization Isolation

Never allow one organization to access another organization's data.

API

Generate:

Routers

Schemas

Repositories

Services

Dependencies

Tests

Swagger Documentation

Output

Return COMPLETE files.

No pseudo code.

No explanations.

Only production-ready code.
