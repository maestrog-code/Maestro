# MAESTRO — Sprint 010 CTO Review Package

Paste this entire document into ChatGPT for the code review.

---

## Context

Sprint 010 is on branch `feature/sprint-010-business-tools`.
This document contains every implementation file in full, exactly as committed.

---

## `app/modules/business/models.py`

```py
from enum import Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Date, Numeric, Enum as SQLEnum
import uuid
from decimal import Decimal
from datetime import date
from app.models.base import TimestampedModel


class ProjectStatus(str, Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    UNPAID = "unpaid"
    PAID = "paid"
    OVERDUE = "overdue"


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class TransactionCategory(str, Enum):
    REVENUE = "revenue"
    COGS_INFRASTRUCTURE = "cogs_infrastructure"
    COGS_CONTRACTORS = "cogs_contractors"
    OPEX_PAYROLL = "opex_payroll"
    OPEX_SOFTWARE = "opex_software"
    OPEX_RENT = "opex_rent"
    OPEX_MARKETING = "opex_marketing"


class Project(TimestampedModel):
    __tablename__ = "projects"

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(SQLEnum(ProjectStatus), default=ProjectStatus.PLANNING, nullable=False, index=True)
    budget: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationships
    allocations = relationship("ProjectAllocation", back_populates="project", cascade="all, delete-orphan")


class Resource(TimestampedModel):
    __tablename__ = "resources"

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String, nullable=False)
    cost_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Relationships
    allocations = relationship("ProjectAllocation", back_populates="resource", cascade="all, delete-orphan")


class ProjectAllocation(TimestampedModel):
    __tablename__ = "project_allocations"

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"), index=True, nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    allocation_percentage: Mapped[int] = mapped_column(nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)

    # Relationships
    resource = relationship("Resource", back_populates="allocations")
    project = relationship("Project", back_populates="allocations")


class Invoice(TimestampedModel):
    __tablename__ = "invoices"

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    invoice_number: Mapped[str] = mapped_column(String, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(SQLEnum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False, index=True)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    client_name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # Relationships
    transactions = relationship("Transaction", back_populates="invoice")


class Transaction(TimestampedModel):
    __tablename__ = "transactions"

    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("invoices.id", ondelete="SET NULL"), index=True, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    type: Mapped[TransactionType] = mapped_column(SQLEnum(TransactionType), nullable=False, index=True)
    category: Mapped[TransactionCategory] = mapped_column(SQLEnum(TransactionCategory), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    invoice = relationship("Invoice", back_populates="transactions")
```

---

## `app/modules/business/schemas.py`

```py
from typing import Optional
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from app.modules.business.models import ProjectStatus, InvoiceStatus, TransactionType, TransactionCategory


# ─── Project Schemas ────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.PLANNING
    budget: Decimal = Field(..., gt=0)
    start_date: date
    end_date: Optional[date] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    budget: Optional[Decimal] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: Optional[str]
    status: ProjectStatus
    budget: Decimal
    start_date: date
    end_date: Optional[date]
    created_at: datetime
    updated_at: datetime


# ─── Resource Schemas ───────────────────────────────────────────────────────────

class ResourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    role: str = Field(..., min_length=1)
    cost_rate: Decimal = Field(..., ge=0)


class ResourceUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    cost_rate: Optional[Decimal] = None


class ResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    role: str
    cost_rate: Decimal
    created_at: datetime
    updated_at: datetime


# ─── Project Allocation Schemas ──────────────────────────────────────────────────

class ProjectAllocationCreate(BaseModel):
    resource_id: UUID
    project_id: UUID
    allocation_percentage: int = Field(..., ge=1, le=100)
    role: str = Field(..., min_length=1)


class ProjectAllocationUpdate(BaseModel):
    allocation_percentage: Optional[int] = Field(None, ge=1, le=100)
    role: Optional[str] = None


class ProjectAllocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    resource_id: UUID
    project_id: UUID
    allocation_percentage: int
    role: str
    created_at: datetime
    updated_at: datetime


# ─── Invoice Schemas ────────────────────────────────────────────────────────────

class InvoiceCreate(BaseModel):
    invoice_number: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)
    status: InvoiceStatus = InvoiceStatus.DRAFT
    issue_date: date
    due_date: date
    client_name: str = Field(..., min_length=1)


class InvoiceUpdate(BaseModel):
    invoice_number: Optional[str] = None
    amount: Optional[Decimal] = None
    status: Optional[InvoiceStatus] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    client_name: Optional[str] = None


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    invoice_number: str
    amount: Decimal
    status: InvoiceStatus
    issue_date: date
    due_date: date
    client_name: str
    created_at: datetime
    updated_at: datetime


# ─── Transaction Schemas ────────────────────────────────────────────────────────

class TransactionCreate(BaseModel):
    invoice_id: Optional[UUID] = None
    amount: Decimal = Field(..., gt=0)
    type: TransactionType
    category: TransactionCategory
    date: date
    description: Optional[str] = None


class TransactionUpdate(BaseModel):
    invoice_id: Optional[UUID] = None
    amount: Optional[Decimal] = None
    type: Optional[TransactionType] = None
    category: Optional[TransactionCategory] = None
    date: Optional[date] = None
    description: Optional[str] = None


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    invoice_id: Optional[UUID]
    amount: Decimal
    type: TransactionType
    category: TransactionCategory
    date: date
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
```

---

## `alembic/versions/008_business_models.py`

```py
"""add_business_models

Revision ID: 008_business_models
Revises: 007
Create Date: 2026-07-11 18:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ENUM

# revision identifiers, used by Alembic.
revision: str = '008_business_models'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enums
project_status_enum = ENUM("planning", "active", "completed", "on_hold", name="projectstatus", create_type=False)
invoice_status_enum = ENUM("draft", "unpaid", "paid", "overdue", name="invoicestatus", create_type=False)
transaction_type_enum = ENUM("income", "expense", name="transactiontype", create_type=False)
transaction_category_enum = ENUM(
    "revenue",
    "cogs_infrastructure",
    "cogs_contractors",
    "opex_payroll",
    "opex_software",
    "opex_rent",
    "opex_marketing",
    name="transactioncategory",
    create_type=False
)


def upgrade() -> None:
    # 1. Create Enums
    project_status_enum.create(op.get_bind(), checkfirst=True)
    invoice_status_enum.create(op.get_bind(), checkfirst=True)
    transaction_type_enum.create(op.get_bind(), checkfirst=True)
    transaction_category_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create projects table
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("status", project_status_enum, nullable=False, server_default="planning", index=True),
        sa.Column("budget", sa.Numeric(15, 2), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        # Audit & Common fields
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), index=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_projects_name", "projects", ["name"])

    # 3. Create resources table
    op.create_table(
        "resources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=False),
        sa.Column("cost_rate", sa.Numeric(12, 2), nullable=False),
        # Audit & Common fields
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), index=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_resources_name", "resources", ["name"])

    # 4. Create project_allocations table
    op.create_table(
        "project_allocations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("resource_id", UUID(as_uuid=True), sa.ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("allocation_percentage", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=False),
        # Audit & Common fields
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), index=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )

    # 5. Create invoices table
    op.create_table(
        "invoices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("invoice_number", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("status", invoice_status_enum, nullable=False, server_default="draft", index=True),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("client_name", sa.String(length=255), nullable=False),
        # Audit & Common fields
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), index=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_invoices_invoice_number", "invoices", ["invoice_number"])
    op.create_index("ix_invoices_client_name", "invoices", ["client_name"])

    # 6. Create transactions table
    op.create_table(
        "transactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("type", transaction_type_enum, nullable=False, index=True),
        sa.Column("category", transaction_category_enum, nullable=False, index=True),
        sa.Column("date", sa.Date(), nullable=False, index=True),
        sa.Column("description", sa.String(length=1000), nullable=True),
        # Audit & Common fields
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), index=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_table("transactions")
    op.drop_table("invoices")
    op.drop_table("project_allocations")
    op.drop_table("resources")
    op.drop_table("projects")

    transaction_category_enum.drop(op.get_bind(), checkfirst=True)
    transaction_type_enum.drop(op.get_bind(), checkfirst=True)
    invoice_status_enum.drop(op.get_bind(), checkfirst=True)
    project_status_enum.drop(op.get_bind(), checkfirst=True)
```

---

## `scripts/seed_business_data.py`

```py
import asyncio
import random
import sys
import os
import uuid
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import delete, select

# Adjust path to import app correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import AsyncSessionLocal
from app.modules.organizations.models import Organization
from app.modules.business.models import (
    Project, Resource, ProjectAllocation, Invoice, Transaction,
    ProjectStatus, InvoiceStatus, TransactionType, TransactionCategory
)


async def seed_data():
    print("Starting database seed...")
    async with AsyncSessionLocal() as session:
        # 1. Clean existing data
        print("Cleaning old business tools data...")
        await session.execute(delete(Transaction))
        await session.execute(delete(Invoice))
        await session.execute(delete(ProjectAllocation))
        await session.execute(delete(Resource))
        await session.execute(delete(Project))
        await session.commit()

        # 2. Ensure default Organization exists
        org_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
        result = await session.execute(select(Organization).filter_by(id=org_id))
        org = result.scalar_one_or_none()
        if not org:
            print("Creating default organization...")
            org = Organization(
                id=org_id,
                name="Default Organization",
                slug="default-org"
            )
            session.add(org)
            await session.commit()

        # 3. Create Resources
        print("Creating resources...")
        resources = [
            Resource(id=uuid.uuid4(), organization_id=org_id, name="Alice Developer", role="Software Engineer", cost_rate=Decimal("1500.00")),
            Resource(id=uuid.uuid4(), organization_id=org_id, name="Bob Designer", role="UI Designer", cost_rate=Decimal("1200.00")),
            Resource(id=uuid.uuid4(), organization_id=org_id, name="Charlie Devops", role="DevOps Engineer", cost_rate=Decimal("1800.00")),
            Resource(id=uuid.uuid4(), organization_id=org_id, name="Dave Contractor", role="Contractor Engineer", cost_rate=Decimal("2000.00")),
            Resource(id=uuid.uuid4(), organization_id=org_id, name="Eve Sales", role="Sales Executive", cost_rate=Decimal("1000.00")),
        ]
        session.add_all(resources)
        await session.commit()

        # 4. Create Projects
        print("Creating projects...")
        today = date.today()
        projects = [
            Project(
                id=uuid.uuid4(),
                organization_id=org_id,
                name="E-Commerce App",
                description="Core custom shopping application with mobile-first storefront",
                status=ProjectStatus.ACTIVE,
                budget=Decimal("150000.00"),
                start_date=today - timedelta(days=180),
                end_date=today + timedelta(days=180)
            ),
            Project(
                id=uuid.uuid4(),
                organization_id=org_id,
                name="Inventory API Integration",
                description="Backend REST API integrating with supplier databases",
                status=ProjectStatus.COMPLETED,
                budget=Decimal("45000.00"),
                start_date=today - timedelta(days=270),
                end_date=today - timedelta(days=90)
            ),
            Project(
                id=uuid.uuid4(),
                organization_id=org_id,
                name="Mobile App Redesign",
                description="Redesign and transition to React Native for next phase scaling",
                status=ProjectStatus.PLANNING,
                budget=Decimal("85000.00"),
                start_date=today + timedelta(days=30),
                end_date=today + timedelta(days=180)
            ),
        ]
        session.add_all(projects)
        await session.commit()

        # 5. Create Project Allocations
        print("Creating allocations...")
        allocations = [
            ProjectAllocation(
                id=uuid.uuid4(), organization_id=org_id,
                resource_id=resources[0].id, project_id=projects[0].id,
                allocation_percentage=80, role="Lead Developer"
            ),
            ProjectAllocation(
                id=uuid.uuid4(), organization_id=org_id,
                resource_id=resources[1].id, project_id=projects[0].id,
                allocation_percentage=40, role="UI Designer"
            ),
            ProjectAllocation(
                id=uuid.uuid4(), organization_id=org_id,
                resource_id=resources[0].id, project_id=projects[1].id,
                allocation_percentage=20, role="Consulting Developer"
            ),
            ProjectAllocation(
                id=uuid.uuid4(), organization_id=org_id,
                resource_id=resources[2].id, project_id=projects[1].id,
                allocation_percentage=100, role="Lead DevOps Engineer"
            ),
        ]
        session.add_all(allocations)
        await session.commit()

        # 6. Seed Invoices & Transactions (Semi-Deterministic via random.seed(42))
        print("Seeding invoices and transactions...")
        random.seed(42)

        transactions = []
        invoices = []

        start_date = today - timedelta(days=365)
        
        # Pre-generate some clients and invoices
        clients = ["Acme Corporation", "East Africa Retailers", "Safari Adventures", "Kibo Ventures", "Nile Tech Solutions"]
        
        for idx in range(1, 21):
            issue_date = start_date + timedelta(days=random.randint(10, 340))
            due_date = issue_date + timedelta(days=30)
            inv_amount = Decimal(str(random.randint(50, 250) * 100))
            
            # 80% chance it is paid
            is_paid = random.random() < 0.8
            status = InvoiceStatus.PAID if is_paid else (InvoiceStatus.OVERDUE if due_date < today else InvoiceStatus.UNPAID)
            
            inv = Invoice(
                id=uuid.uuid4(),
                organization_id=org_id,
                invoice_number=f"INV-2025-{idx:03d}",
                amount=inv_amount,
                status=status,
                issue_date=issue_date,
                due_date=due_date,
                client_name=random.choice(clients)
            )
            invoices.append(inv)
            
            # If paid, generate corresponding transaction
            if status == InvoiceStatus.PAID:
                pay_date = issue_date + timedelta(days=random.randint(1, 15))
                t = Transaction(
                    id=uuid.uuid4(),
                    organization_id=org_id,
                    invoice_id=inv.id,
                    amount=inv_amount,
                    type=TransactionType.INCOME,
                    category=TransactionCategory.REVENUE,
                    date=pay_date,
                    description=f"Payment for invoice {inv.invoice_number} by {inv.client_name}"
                )
                transactions.append(t)

        session.add_all(invoices)
        await session.commit()

        # Daily / Time-Series cashflow loop for expenses and miscellaneous income
        current_date = start_date
        while current_date <= today:
            # Monthly Rent
            if current_date.day == 1:
                transactions.append(Transaction(
                    id=uuid.uuid4(), organization_id=org_id,
                    amount=Decimal("3000.00"), type=TransactionType.EXPENSE,
                    category=TransactionCategory.OPEX_RENT, date=current_date,
                    description="Monthly Office Space Rent"
                ))

            # Monthly Software Subscriptions
            if current_date.day == 5:
                transactions.append(Transaction(
                    id=uuid.uuid4(), organization_id=org_id,
                    amount=Decimal("850.00"), type=TransactionType.EXPENSE,
                    category=TransactionCategory.OPEX_SOFTWARE, date=current_date,
                    description="Internal SaaS Subscription Billing (Slack, GitHub, GSuite)"
                ))

            # Infrastructure (COGS) with small seed-based variation
            if current_date.day == 10:
                infra_cost = Decimal(str(round(1200.00 + random.uniform(-150.0, 350.0), 2)))
                transactions.append(Transaction(
                    id=uuid.uuid4(), organization_id=org_id,
                    amount=infra_cost, type=TransactionType.EXPENSE,
                    category=TransactionCategory.COGS_INFRASTRUCTURE, date=current_date,
                    description="AWS Cloud Infrastructure Monthly Statement"
                ))

            # Monthly Payroll (OPEX + COGS)
            if current_date.day == 28:
                # OPEX payroll for internal staff
                transactions.append(Transaction(
                    id=uuid.uuid4(), organization_id=org_id,
                    amount=resources[0].cost_rate, type=TransactionType.EXPENSE,
                    category=TransactionCategory.OPEX_PAYROLL, date=current_date,
                    description=f"Salaried payroll - {resources[0].name}"
                ))
                transactions.append(Transaction(
                    id=uuid.uuid4(), organization_id=org_id,
                    amount=resources[1].cost_rate, type=TransactionType.EXPENSE,
                    category=TransactionCategory.OPEX_PAYROLL, date=current_date,
                    description=f"Salaried payroll - {resources[1].name}"
                ))
                transactions.append(Transaction(
                    id=uuid.uuid4(), organization_id=org_id,
                    amount=resources[2].cost_rate, type=TransactionType.EXPENSE,
                    category=TransactionCategory.OPEX_PAYROLL, date=current_date,
                    description=f"Salaried payroll - {resources[2].name}"
                ))
                transactions.append(Transaction(
                    id=uuid.uuid4(), organization_id=org_id,
                    amount=resources[4].cost_rate, type=TransactionType.EXPENSE,
                    category=TransactionCategory.OPEX_PAYROLL, date=current_date,
                    description=f"Salaried payroll - {resources[4].name}"
                ))

                # COGS Contractors
                transactions.append(Transaction(
                    id=uuid.uuid4(), organization_id=org_id,
                    amount=resources[3].cost_rate, type=TransactionType.EXPENSE,
                    category=TransactionCategory.COGS_CONTRACTORS, date=current_date,
                    description=f"Contractor billing - {resources[3].name}"
                ))

            # Random daily/weekly business retail income entries
            # Let's say there is a 35% chance of an income receipt on any non-weekend day
            if current_date.weekday() < 5 and random.random() < 0.35:
                retail_amount = Decimal(str(round(random.uniform(150.0, 1500.0), 2)))
                transactions.append(Transaction(
                    id=uuid.uuid4(), organization_id=org_id,
                    amount=retail_amount, type=TransactionType.INCOME,
                    category=TransactionCategory.REVENUE, date=current_date,
                    description="Daily software subscription / stripe payout revenue"
                ))

            current_date += timedelta(days=1)

        # Batch insert all transactions
        print(f"Batch inserting {len(transactions)} transactions...")
        session.add_all(transactions)
        await session.commit()

        print("Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_data())
```

---

## `alembic/env.py`

```py
"""Alembic environment configuration for MAESTRO.

Supports async SQLAlchemy engine with PostgreSQL (asyncpg).
Run migrations with:
    alembic upgrade head
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import all models so Alembic can detect them
from app.models.base import Base  # noqa: F401
from app.modules.users.models import User  # noqa: F401
from app.modules.organizations.models import Organization, OrganizationMember  # noqa: F401
from app.modules.permissions.models import Role, Permission, RolePermission  # noqa: F401
from app.core.auth.models import RefreshToken, AuditLog  # noqa: F401
from app.modules.ai_conversations.models import Conversation, AIMessageModel  # noqa: F401
from app.modules.business.models import Project, Resource, ProjectAllocation, Invoice, Transaction  # noqa: F401
from app.core.config import settings

config = context.config

# Override sqlalchemy.url from settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection needed)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

