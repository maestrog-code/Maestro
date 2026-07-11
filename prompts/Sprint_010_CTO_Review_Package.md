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

## `app/ai/tools/business_tools.py`

```py
import logging
from typing import Any, Optional, Dict, List
from datetime import date
from uuid import UUID
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.ai.tools.base import BaseTool
from app.modules.business.models import (
    Transaction, ProjectAllocation, Resource, Project,
    TransactionType, TransactionCategory
)

logger = logging.getLogger(__name__)


# ─── Fetch Financial Metrics (CFO Tool) ─────────────────────────────────────────

class FetchFinancialMetricsInput(BaseModel):
    start_date: Optional[date] = Field(None, description="Start date for metrics aggregation (YYYY-MM-DD).")
    end_date: Optional[date] = Field(None, description="End date for metrics aggregation (YYYY-MM-DD).")


class FetchFinancialMetricsOutput(BaseModel):
    metrics: Dict[str, Any]


class FetchFinancialMetricsTool(BaseTool):
    """
    Queries the database for financial transactions and aggregates revenue,
    COGS, OPEX, gross margins, and net margins.
    """
    name: str = "fetch_financial_metrics"
    description: str = (
        "Retrieve and aggregate organizational financial metrics (revenue, COGS, "
        "OPEX, gross and net profit, margins) over a specified date range."
    )
    input_schema = FetchFinancialMetricsInput
    output_schema = FetchFinancialMetricsOutput

    def __init__(self, db: AsyncSession, organization_id: UUID):
        self.db = db
        self.organization_id = organization_id

    async def execute(self, start_date: Optional[date] = None, end_date: Optional[date] = None, **kwargs) -> Any:
        filters = [Transaction.organization_id == self.organization_id]
        if start_date:
            filters.append(Transaction.date >= start_date)
        if end_date:
            filters.append(Transaction.date <= end_date)

        # Run query to fetch transactions matching filters
        query = select(Transaction).where(and_(*filters))
        result = await self.db.execute(query)
        transactions = result.scalars().all()

        total_revenue = 0.0
        total_cogs = 0.0
        total_opex = 0.0

        category_breakdown = {cat.value: 0.0 for cat in TransactionCategory}

        for tx in transactions:
            amount = float(tx.amount)
            if tx.type == TransactionType.INCOME:
                total_revenue += amount
                category_breakdown[tx.category.value] += amount
            elif tx.type == TransactionType.EXPENSE:
                category_breakdown[tx.category.value] += amount
                if tx.category in [TransactionCategory.COGS_INFRASTRUCTURE, TransactionCategory.COGS_CONTRACTORS]:
                    total_cogs += amount
                else:
                    total_opex += amount

        gross_profit = total_revenue - total_cogs
        net_profit = gross_profit - total_opex

        gross_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0.0
        net_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0

        return {
            "metrics": {
                "total_revenue": round(total_revenue, 2),
                "total_cogs": round(total_cogs, 2),
                "total_opex": round(total_opex, 2),
                "gross_profit": round(gross_profit, 2),
                "net_profit": round(net_profit, 2),
                "gross_margin_percentage": round(gross_margin, 2),
                "net_margin_percentage": round(net_margin, 2),
                "category_breakdown": {k: round(v, 2) for k, v in category_breakdown.items() if v > 0}
            }
        }


# ─── Check Resource Allocation (COO Tool) ─────────────────────────────────────────

class CheckResourceAllocationInput(BaseModel):
    project_id: Optional[UUID] = Field(None, description="Filter allocations by a specific project UUID.")
    resource_id: Optional[UUID] = Field(None, description="Filter allocations by a specific resource UUID.")


class CheckResourceAllocationOutput(BaseModel):
    allocations: List[Dict[str, Any]]


class CheckResourceAllocationTool(BaseTool):
    """
    Queries resource allocations, projects, and resources to compute bandwidth
    and project staffing allocations.
    """
    name: str = "check_resource_allocation"
    description: str = (
        "Check resource allocation percentages, roles, and project workloads "
        "across the organization."
    )
    input_schema = CheckResourceAllocationInput
    output_schema = CheckResourceAllocationOutput

    def __init__(self, db: AsyncSession, organization_id: UUID):
        self.db = db
        self.organization_id = organization_id

    async def execute(self, project_id: Optional[UUID] = None, resource_id: Optional[UUID] = None, **kwargs) -> Any:
        filters = [ProjectAllocation.organization_id == self.organization_id]
        if project_id:
            filters.append(ProjectAllocation.project_id == project_id)
        if resource_id:
            filters.append(ProjectAllocation.resource_id == resource_id)

        query = (
            select(
                ProjectAllocation.allocation_percentage,
                ProjectAllocation.role.label("allocation_role"),
                Resource.name.label("resource_name"),
                Resource.role.label("resource_role"),
                Project.name.label("project_name"),
                Project.status.label("project_status")
            )
            .join(Resource, ProjectAllocation.resource_id == Resource.id)
            .join(Project, ProjectAllocation.project_id == Project.id)
            .where(and_(*filters))
        )

        result = await self.db.execute(query)
        rows = result.mappings().all()

        allocations_list = []
        for r in rows:
            allocations_list.append({
                "resource_name": r["resource_name"],
                "resource_role": r["resource_role"],
                "project_name": r["project_name"],
                "project_status": r["project_status"].value,
                "allocation_percentage": r["allocation_percentage"],
                "allocation_role": r["allocation_role"]
            })

        return {"allocations": allocations_list}
```

---

## `app/ai/pipeline/executor.py`

```py
import json
import logging
import time
from uuid import UUID
from typing import AsyncGenerator, Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_settings import ai_settings
from app.ai.agents.registry import registry
from app.ai.providers.factory import get_llm_provider
from app.ai.prompts.builder import PromptBuilder, PromptContext
from app.ai.pipeline.tool_executor import ToolExecutor
from app.ai.schemas import (
    AIMessage, MessageRole, ToolCall,
    StreamEvent, TokenEvent, OrchestrationEvent, TaskUpdateEvent, ToolCallEvent
)
from app.ai.telemetry.logger import telemetry
from app.ai.safety.guards import AISafetyGuards
from app.modules.ai_conversations.models import AIMessageModel, Conversation
from app.modules.users.models import User
from app.modules.organizations.models import Organization

# Import tools for dynamic instantiation
from app.ai.tools.knowledge_tools import SearchKnowledgeBaseTool, GetDocumentTool, ListDocumentsTool
from app.ai.tools.memory_tools import RememberFactTool, ForgetFactTool
from app.ai.tools.orchestration_tools import DelegateTaskTool, UpdateTaskStatusTool
from app.ai.tools.business_tools import FetchFinancialMetricsTool, CheckResourceAllocationTool
from app.ai.embedding.google import GeminiEmbeddingProvider
from app.modules.knowledge.services import KnowledgeService

logger = logging.getLogger(__name__)


class AIExecutionPipeline:
    def __init__(self, db: AsyncSession, user: User, organization: Organization, conversation: Conversation):
        self.db = db
        self.user = user
        self.organization = organization
        self.conversation = conversation

    async def _resolve_tools(self, tool_names: List[str]) -> List[Any]:
        """Instantiate tools based on names, injecting required context."""
        instances = []
        knowledge_service = KnowledgeService(self.db)

        for name in tool_names:
            if name == "search_knowledge_base":
                instances.append(SearchKnowledgeBaseTool(knowledge_service, self.organization.id, self.user.id))
            elif name == "get_document":
                instances.append(GetDocumentTool(knowledge_service, self.organization.id))
            elif name == "list_documents":
                instances.append(ListDocumentsTool(knowledge_service, self.organization.id))
            elif name == "remember_fact":
                instances.append(RememberFactTool())
            elif name == "forget_fact":
                instances.append(ForgetFactTool())
            elif name == "delegate_task":
                instances.append(DelegateTaskTool())
            elif name == "update_task_status":
                instances.append(UpdateTaskStatusTool())
            elif name == "fetch_financial_metrics":
                instances.append(FetchFinancialMetricsTool(self.db, self.organization.id))
            elif name == "check_resource_allocation":
                instances.append(CheckResourceAllocationTool(self.db, self.organization.id))
        return instances

    async def _fetch_implicit_context(self, user_prompt: str) -> List[Dict[str, Any]]:
        """
        Implicit RAG: run a quick search on the user's prompt to inject highly relevant
        context directly into the system prompt, saving a tool call round-trip.
        """
        if self.db.bind and self.db.bind.dialect.name == "sqlite":
            return []
        try:
            knowledge_service = KnowledgeService(self.db)
            search_resp = await knowledge_service.search(
                org_id=self.organization.id,
                user=self.user,
                query=user_prompt,
                top_k=3 # Only top 3 for implicit context
            )
            
            documents = []
            for r in search_resp.results:
                # Basic relevance threshold
                if r.score >= 0.70:
                    documents.append({
                        "title": r.document_title,
                        "content": r.content
                    })
            return documents
        except Exception as e:
            # Don't fail the chat if RAG errors
            logger.exception("Implicit RAG failed: %s", e)
            return []

    async def _fetch_implicit_memory(self, user_prompt: str) -> List[Dict[str, Any]]:
        """Fetch highly relevant long-term memory for implicit injection."""
        if self.db.bind and self.db.bind.dialect.name == "sqlite":
            return []
        try:
            from app.modules.memory.services import MemoryService
            memory_service = MemoryService(self.db, embedding_provider=GeminiEmbeddingProvider())
            search_resp = await memory_service.search(
                organization_id=self.organization.id,
                query=user_prompt,
                top_k=5,
                context="implicit_prompt_injection"
            )
            
            memories = []
            for m in search_resp:
                memories.append({
                    "memory_type": m.memory_type.value,
                    "content": m.content
                })
            return memories
        except Exception as e:
            logger.warning("Implicit memory fetch failed: %s", e)
            return []

    async def execute(
        self,
        user_prompt: str,
        current_depth: int = 0,
        parent_message_id: Optional[UUID] = None,
        target_agent: str = "CEO",
        history_messages: Optional[List[AIMessage]] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Executes the AI conversation stream.
        """
        start_time = time.time()
        
        # 1. Select Agent
        agent_id = target_agent or self.conversation.active_agent or "CEO"
        agent = registry.get_agent(agent_id)
        if not agent:
            yield f"Error: Agent '{agent_id}' not found in registry."
            return

        try:
            provider = get_llm_provider(agent.provider)
        except Exception as e:
            yield f"Error: Could not initialize AI provider '{agent.provider}': {e}"
            return

        # 2. Safety Guards
        try:
            AISafetyGuards.check_prompt_injection(user_prompt)
            user_prompt = AISafetyGuards.check_pii_redaction(user_prompt)
        except Exception as e:
            yield f"Safety guard blocked execution: {e}"
            return

        # 3. Implicit Retrieval
        implicit_memories = await self._fetch_implicit_memory(user_prompt)
        implicit_docs = await self._fetch_implicit_context(user_prompt)

        # 4. Build Prompt Context using structured PromptContext
        context = PromptContext(
            user=self.user,
            organization=self.organization,
            documents=implicit_docs,
            memories=implicit_memories
        )
        system_content = PromptBuilder.render(agent.system_prompt_template, context)

        # Inject Summarization at Source if this is a delegated task
        if current_depth > 0:
            system_content += "\n\nCRITICAL DIRECTIVE: You are executing a delegated sub-task for the CEO. You MUST return a concise, highly-structured executive summary of your findings. Do NOT return raw data rows unless explicitly requested."

        messages = [AIMessage(role=MessageRole.SYSTEM, content=system_content)]

        if history_messages is None:
            history_messages = []
            history_models = self.conversation.messages[-10:] # last 10 messages
            for msg_model in history_models:
                tool_calls = None
                if msg_model.tool_calls:
                    tool_calls = [ToolCall(**tc) for tc in msg_model.tool_calls]
                history_messages.append(AIMessage(
                    role=msg_model.role,
                    content=msg_model.content,
                    name=msg_model.name,
                    tool_calls=tool_calls,
                    tool_call_id=msg_model.tool_call_id
                ))
        
        messages.extend(history_messages)
            
        # Add the new user prompt
        messages.append(AIMessage(role=MessageRole.USER, content=user_prompt))

        # Persist User Prompt
        user_msg_model = AIMessageModel(
            conversation_id=self.conversation.id,
            role=MessageRole.USER,
            content=user_prompt,
            parent_message_id=parent_message_id
        )
        self.db.add(user_msg_model)
        await self.db.commit()

        # 6. Tool Setup
        agent_tools = await self._resolve_tools(agent.tools)
        tool_executor = ToolExecutor(tools=agent_tools)
        tool_schemas = tool_executor.get_tool_schemas()

        iteration_count = 0
        max_iterations = ai_settings.MAX_TOOL_CALLS

        while iteration_count < max_iterations:
            iteration_count += 1

            # 7. Stream from Provider
            full_response_text = ""
            tool_calls_to_execute = []

            async for chunk in provider.stream(
                messages=messages,
                tools=tool_schemas if tool_schemas else None,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens
            ):
                if isinstance(chunk, str):
                    full_response_text += chunk
                    yield TokenEvent(text=chunk)
                elif isinstance(chunk, ToolCall):
                    tool_calls_to_execute.append(chunk)

            # We exit after the first stream response since full tool calling loop is disabled for Sprint 004
            # UNLESS there are tool calls, in which case we execute them and loop (Sprint 007 upgrade)
            assistant_msg_model = AIMessageModel(
                conversation_id=self.conversation.id,
                role=MessageRole.ASSISTANT,
                content=full_response_text,
                parent_message_id=parent_message_id,
                tool_calls=[tc.model_dump() for tc in tool_calls_to_execute] if tool_calls_to_execute else None
            )
            self.db.add(assistant_msg_model)
            await self.db.commit()

            messages.append(AIMessage(
                role=MessageRole.ASSISTANT,
                content=full_response_text,
                tool_calls=tool_calls_to_execute if tool_calls_to_execute else None
            ))

            if not tool_calls_to_execute:
                break

            # Execute Tools
            for tc in tool_calls_to_execute:
                if tc.name == "update_task_status":
                    yield TaskUpdateEvent(
                        step=tc.arguments.get("step", ""),
                        status=tc.arguments.get("status", ""),
                        notes=tc.arguments.get("notes")
                    )
                
                if tc.name == "delegate_task":
                    # Hard Guardrail
                    if current_depth >= 3:
                        tool_result = "Error: Maximum delegation depth (3) exceeded."
                    else:
                        target = tc.arguments.get("target_agent", "CEO")
                        instructions = tc.arguments.get("instructions", "")
                        original_goal = tc.arguments.get("original_goal", "")
                        
                        combined_prompt = f"Original Goal: {original_goal}\n\nTask Instructions:\n{instructions}" if original_goal else instructions

                        yield OrchestrationEvent(
                            target_agent=target,
                            message=f"Delegating sub-task to {target}..."
                        )

                        sub_task_result = ""
                        
                        try:
                            # Recursively call the pipeline without passing raw history
                            async for sub_chunk in self.execute(
                                user_prompt=combined_prompt,
                                current_depth=current_depth + 1,
                                parent_message_id=user_msg_model.id,
                                target_agent=target,
                                history_messages=[] # Force context isolation
                            ):
                                if isinstance(sub_chunk, TokenEvent):
                                    sub_task_result += sub_chunk.text
                                else:
                                    yield sub_chunk
                        except Exception as e:
                            logger.error("Delegated sub-task failed: %s", e)
                            sub_task_result = f"Error: The delegated task to {target} failed unexpectedly. Details: {e}"

                        # Middle-out Truncation
                        if len(sub_task_result) > ai_settings.DELEGATION_MAX_CHARS:
                            half = ai_settings.DELEGATION_MAX_CHARS // 2 - 50
                            sub_task_result = sub_task_result[:half] + "\n\n...[TRUNCATED]...\n\n" + sub_task_result[-half:]

                        tool_result = sub_task_result
                else:
                    if tc.name != "update_task_status":
                        yield ToolCallEvent(tool_name=tc.name, status="started")
                    
                    # Normal tool execution
                    try:
                        tool_result = await tool_executor.execute(
                            db=self.db,
                            tool_name=tc.name,
                            tool_args=tc.arguments,
                            user_id=self.user.id,
                            organization_id=self.organization.id,
                            agent_id=agent.id,
                        )
                        if tc.name != "update_task_status":
                            yield ToolCallEvent(tool_name=tc.name, status="completed")
                    except Exception as e:
                        logger.error("Tool execution failed: %s", e)
                        tool_result = f"Error executing tool {tc.name}: {e}"
                        if tc.name != "update_task_status":
                            yield ToolCallEvent(tool_name=tc.name, status="failed")

                if not isinstance(tool_result, str):
                    tool_result = json.dumps(tool_result, default=str)

                tool_msg_model = AIMessageModel(
                    conversation_id=self.conversation.id,
                    role=MessageRole.TOOL,
                    content=tool_result,
                    tool_call_id=tc.id,
                    name=tc.name,
                    parent_message_id=parent_message_id
                )
                self.db.add(tool_msg_model)
                await self.db.commit()

                messages.append(AIMessage(
                    role=MessageRole.TOOL,
                    content=tool_result,
                    tool_call_id=tc.id,
                    name=tc.name
                ))

            # 8. Telemetry
            latency = (time.time() - start_time) * 1000
            telemetry.log_execution(
                request_id=f"req_{self.conversation.id}",
                organization_id=self.organization.id,
                conversation_id=self.conversation.id,
                agent=agent.id,
                provider=provider.__class__.__name__,
                model=agent.provider, # assuming provider string acts as model
                latency_ms=latency,
                input_tokens=0,
                output_tokens=0,
            )
```

---

## `app/ai/agents/definitions/coo.py`

```py
from app.ai.agents.registry import AgentDefinition, registry
from app.core.ai_settings import ai_settings

coo_agent = AgentDefinition(
    id="COO",
    name="Chief Operations Officer",
    version="1.0",
    system_prompt_template="coo_system",
    tools=[
        "search_knowledge_base",
        "get_document",
        "list_documents",
        "remember_fact",
        "forget_fact",
        "check_resource_allocation"
    ],
    provider=ai_settings.DEFAULT_PROVIDER,
    temperature=ai_settings.DEFAULT_TEMPERATURE,
    max_tokens=2048,
    enabled=True,
)

registry.register(coo_agent)
```

---

## `app/ai/agents/definitions/cfo.py`

```py
from app.ai.agents.registry import AgentDefinition, registry
from app.core.ai_settings import ai_settings

cfo_agent = AgentDefinition(
    id="CFO",
    name="Chief Financial Officer",
    version="1.0",
    system_prompt_template="cfo_system",
    tools=[
        "search_knowledge_base",
        "get_document",
        "list_documents",
        "remember_fact",
        "forget_fact",
        "fetch_financial_metrics"
    ],
    provider=ai_settings.DEFAULT_PROVIDER,
    temperature=ai_settings.DEFAULT_TEMPERATURE,
    max_tokens=2048,
    enabled=True,
)

registry.register(cfo_agent)
```

---

## `app/ai/agents/registry.py`

```py
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.core.ai_settings import ai_settings


class AgentDefinition(BaseModel):
    id: str
    name: str
    version: str
    system_prompt_template: str
    tools: List[str]  # List of tool names
    provider: str
    temperature: float
    max_tokens: int
    enabled: bool


class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, AgentDefinition] = {}

    def register(self, agent: AgentDefinition) -> None:
        self._agents[agent.id] = agent

    def get_agent(self, agent_id: str) -> Optional[AgentDefinition]:
        return self._agents.get(agent_id)

    def list_agents(self) -> List[AgentDefinition]:
        return [agent for agent in self._agents.values() if agent.enabled]


registry = AgentRegistry()

# Import definitions to register them
from app.ai.agents.definitions import ceo, cfo, coo
```

---

## `app/ai/prompts/templates/coo_system.md`

```markdown
You are the Chief Operations Officer (COO) of {{company_name}}.
Your role is to optimize operations, track project resource allocations, and manage personnel bandwidth.

## Context
**Organization Name:** {{organization_name}}
**Current User:** {{user_first_name}} {{user_last_name}}

## Objectives
- Maximize engineering and personnel resource efficiency.
- Track ongoing project statuses and delivery timelines.
- Assess personnel utilization and prevent overallocation bottlenecks.

## Guidelines
- Rely on operational data. Always use the `check_resource_allocation` tool to check engineering bandwidth and allocations before drawing conclusions.
- Help the supervisor agent (CEO) understand if projects are adequately staffed or if some team members are overallocated.
- Cite your sources when using organizational knowledge.

## Past Memory
The following historical context, facts, and preferences are relevant to the current conversation:
{{memory_context}}

## Internal Knowledge
The following internal documents and knowledge base articles may be relevant to the user's request:
{{knowledge_context}}
```

---

## `app/workers/business_tasks.py`

```py
import asyncio
import logging
import uuid
from datetime import date, datetime
from sqlalchemy import select, and_, delete

from app.workers.celery_app import celery_app
from app.core.database import CelerySessionLocal
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.users.models import User
from app.modules.ai_conversations.models import Conversation, AIMessageModel
from app.modules.business.models import Briefing, BriefingStatus
from app.ai.pipeline.executor import AIExecutionPipeline
from app.ai.schemas import MessageRole

logger = logging.getLogger(__name__)


def run_async_synchronously(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError as e:
        if "running event loop" in str(e):
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        raise


@celery_app.task(name="business.generate_daily_briefings")
def generate_daily_briefings() -> dict:
    """
    Beat-scheduled task that iterates through all active organizations
    and spawns a sub-task to generate the daily morning executive briefing.
    """
    return run_async_synchronously(_generate_daily_briefings_async())


async def _generate_daily_briefings_async() -> dict:
    async with CelerySessionLocal() as db:
        # Fetch all non-deleted organizations
        query = select(Organization).where(Organization.is_deleted == False)
        result = await db.execute(query)
        orgs = result.scalars().all()

        logger.info("Found %d organizations to generate briefings for.", len(orgs))
        for org in orgs:
            generate_org_daily_briefing.delay(str(org.id))

        return {"status": "enqueued", "org_count": len(orgs)}


@celery_app.task(
    name="business.generate_org_daily_briefing",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def generate_org_daily_briefing(self, organization_id: str) -> dict:
    """
    Asynchronously runs the multi-agent execution pipeline headlessly
    for a specific organization to generate their morning brief.
    """
    try:
        return run_async_synchronously(_generate_org_daily_briefing_async(organization_id))
    except Exception as exc:
        logger.exception("Failed to generate daily briefing for org %s. Retrying...", organization_id)
        # Record failure trace in the DB before retrying
        run_async_synchronously(_mark_briefing_failed(organization_id, str(exc)))
        raise self.retry(exc=exc, countdown=60)


async def _generate_org_daily_briefing_async(organization_id: str) -> dict:
    org_uuid = uuid.UUID(organization_id)
    today = date.today()

    async with CelerySessionLocal() as db:
        # 1. Fetch organization
        query = select(Organization).where(Organization.id == org_uuid)
        res = await db.execute(query)
        org = res.scalar_one_or_none()
        if not org:
            logger.error("Organization %s not found.", organization_id)
            return {"status": "skipped", "reason": f"organization {organization_id} not found"}

        # 2. Get or create today's Briefing record (processing status)
        query = select(Briefing).where(and_(Briefing.organization_id == org_uuid, Briefing.date == today))
        res = await db.execute(query)
        briefing = res.scalar_one_or_none()
        if not briefing:
            briefing = Briefing(
                id=uuid.uuid4(),
                organization_id=org_uuid,
                date=today,
                status=BriefingStatus.PROCESSING
            )
            db.add(briefing)
        else:
            briefing.status = BriefingStatus.PROCESSING
            briefing.content = None
        await db.commit()
        await db.refresh(briefing)

        try:
            # 3. Locate or create System Conversation (wipe messages on start to avoid context leak)
            from sqlalchemy.orm import selectinload
            query = select(Conversation).options(selectinload(Conversation.messages)).where(
                and_(
                    Conversation.organization_id == org_uuid,
                    Conversation.title == "System Daily Briefing Conversation"
                )
            )
            res = await db.execute(query)
            conversation = res.scalar_one_or_none()
            if not conversation:
                conversation = Conversation(
                    id=uuid.uuid4(),
                    organization_id=org_uuid,
                    title="System Daily Briefing Conversation"
                )
                db.add(conversation)
                await db.commit()
                await db.refresh(conversation)
                conversation.messages = []
            else:
                # Wipe historical messages in this system conversation
                await db.execute(delete(AIMessageModel).where(AIMessageModel.conversation_id == conversation.id))
                await db.commit()

            # 4. Fetch the first active user belonging to the organization
            query = (
                select(User)
                .join(OrganizationMember, User.id == OrganizationMember.user_id)
                .where(
                    and_(
                        OrganizationMember.organization_id == org_uuid,
                        User.is_deleted == False
                    )
                )
                .limit(1)
            )
            res = await db.execute(query)
            user = res.scalar_one_or_none()

            # Fallback: fetch any active user if org member isn't found
            if not user:
                res = await db.execute(select(User).where(User.is_deleted == False).limit(1))
                user = res.scalar_one_or_none()

            # Extreme Fallback: create System Automator user if DB is completely empty
            if not user:
                user = User(
                    id=uuid.uuid4(),
                    email="system@maestro.app",
                    first_name="System",
                    last_name="Automator",
                    is_active=True
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)

            # 5. Build prompt and run the headless AIExecutionPipeline
            prompt = (
                f"Today's date is {today.isoformat()}. You are to compile the daily morning executive summary. "
                "You must review financial performance (revenue, COGS, OPEX, gross and net profit margins) "
                "and inspect active projects and team resource allocations. "
                "Delegate tasks to your CFO (for financial analysis) and COO (for resource allocations). "
                "Provide a polished, concise morning brief in markdown including Gross/Net margins and any overallocation warnings."
            )

            pipeline = AIExecutionPipeline(db, user, org, conversation)
            async for _ in pipeline.execute(prompt):
                pass  # headless execution, simply run generator to completion

            # 6. Retrieve the final response message from the pipeline
            query = (
                select(AIMessageModel)
                .where(
                    and_(
                        AIMessageModel.conversation_id == conversation.id,
                        AIMessageModel.role == MessageRole.ASSISTANT
                    )
                )
                .order_by(AIMessageModel.created_at.desc())
                .limit(1)
            )
            res = await db.execute(query)
            last_message = res.scalar_one_or_none()

            if last_message and last_message.content:
                briefing.content = last_message.content
                briefing.status = BriefingStatus.COMPLETED
            else:
                briefing.status = BriefingStatus.FAILED
                briefing.content = "Error: CEO agent did not produce a summary response."
            
            await db.commit()
            return {"status": "completed", "organization_id": organization_id, "briefing_id": str(briefing.id)}

        except Exception as inner_exc:
            logger.exception("Error executing briefing pipeline for org %s", organization_id)
            briefing.status = BriefingStatus.FAILED
            briefing.content = f"Execution failed:\n{str(inner_exc)}"
            await db.commit()
            raise


async def _mark_briefing_failed(organization_id: str, error_msg: str):
    """Fallback helper to ensure failure is registered on database errors."""
    org_uuid = uuid.UUID(organization_id)
    today = date.today()
    async with CelerySessionLocal() as db:
        query = select(Briefing).where(and_(Briefing.organization_id == org_uuid, Briefing.date == today))
        res = await db.execute(query)
        briefing = res.scalar_one_or_none()
        if briefing:
            briefing.status = BriefingStatus.FAILED
            briefing.content = f"System error:\n{error_msg}"
            await db.commit()
```

---

## `app/workers/celery_app.py`

```py
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.task_routes = {
    "app.workers.tasks.*": "main-queue",
    "app.workers.memory_tasks.*": "memory-queue",
    "knowledge.*": "knowledge-queue",
}

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "decay-memories-daily": {
        "task": "app.workers.memory_tasks.decay_memories_task",
        "schedule": crontab(hour=0, minute=0),  # Run daily at midnight
    },
    "generate-daily-briefings-daily": {
        "task": "business.generate_daily_briefings",
        "schedule": crontab(hour=6, minute=0),  # Run daily at 6:00 AM
    },
}


# Example task
@celery_app.task(acks_late=True)
def example_task(word: str) -> str:
    return f"Processed: {word}"
```

---

## `tests/test_business_tools.py`

```py
import pytest
import pytest_asyncio
import uuid
from decimal import Decimal
from datetime import date
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.modules.users.models import User  # noqa: F401
from app.modules.organizations.models import Organization, OrganizationMember  # noqa: F401
from app.modules.permissions.models import Role, Permission, RolePermission  # noqa: F401
from app.core.auth.models import RefreshToken, AuditLog  # noqa: F401
from app.modules.ai_conversations.models import Conversation, AIMessageModel  # noqa: F401
from app.modules.business.models import (
    Project, Resource, ProjectAllocation, Invoice, Transaction,
    ProjectStatus, InvoiceStatus, TransactionType, TransactionCategory
)
from app.ai.tools.business_tools import FetchFinancialMetricsTool, CheckResourceAllocationTool

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, autocommit=False, autoflush=False, expire_on_commit=False
)


@pytest_asyncio.fixture(autouse=True, scope="function")
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_fetch_financial_metrics_tool():
    org_id = uuid.uuid4()
    async with TestSessionLocal() as session:
        # Create organization
        org = Organization(id=org_id, name="Test Org", slug="test-org")
        session.add(org)

        # Seed Transactions
        transactions = [
            Transaction(
                id=uuid.uuid4(), organization_id=org_id, amount=Decimal("10000.00"),
                type=TransactionType.INCOME, category=TransactionCategory.REVENUE,
                date=date(2025, 6, 15), description="Milestone payout"
            ),
            Transaction(
                id=uuid.uuid4(), organization_id=org_id, amount=Decimal("1500.00"),
                type=TransactionType.EXPENSE, category=TransactionCategory.COGS_INFRASTRUCTURE,
                date=date(2025, 6, 10), description="AWS billing"
            ),
            Transaction(
                id=uuid.uuid4(), organization_id=org_id, amount=Decimal("2500.00"),
                type=TransactionType.EXPENSE, category=TransactionCategory.COGS_CONTRACTORS,
                date=date(2025, 6, 28), description="Contractor billing"
            ),
            Transaction(
                id=uuid.uuid4(), organization_id=org_id, amount=Decimal("3000.00"),
                type=TransactionType.EXPENSE, category=TransactionCategory.OPEX_RENT,
                date=date(2025, 6, 1), description="Rent"
            ),
        ]
        session.add_all(transactions)
        await session.commit()

    async with TestSessionLocal() as session:
        tool = FetchFinancialMetricsTool(session, org_id)
        
        # Test full range
        res = await tool.execute(start_date=date(2025, 6, 1), end_date=date(2025, 6, 30))
        metrics = res["metrics"]
        
        assert metrics["total_revenue"] == 10000.00
        assert metrics["total_cogs"] == 4000.00  # 1500 + 2500
        assert metrics["total_opex"] == 3000.00  # Rent
        assert metrics["gross_profit"] == 6000.00  # 10000 - 4000
        assert metrics["net_profit"] == 3000.00  # 6000 - 3000
        assert metrics["gross_margin_percentage"] == 60.00  # (6000 / 10000) * 100
        assert metrics["net_margin_percentage"] == 30.00  # (3000 / 10000) * 100
        assert metrics["category_breakdown"]["revenue"] == 10000.00
        assert metrics["category_breakdown"]["cogs_infrastructure"] == 1500.00


@pytest.mark.asyncio
async def test_check_resource_allocation_tool():
    org_id = uuid.uuid4()
    async with TestSessionLocal() as session:
        # Create organization
        org = Organization(id=org_id, name="Test Org", slug="test-org")
        session.add(org)

        # Seed projects
        p1 = Project(
            id=uuid.uuid4(), organization_id=org_id, name="Project A",
            status=ProjectStatus.ACTIVE, budget=Decimal("50000.00"),
            start_date=date(2025, 1, 1)
        )
        session.add(p1)

        # Seed resources
        r1 = Resource(
            id=uuid.uuid4(), organization_id=org_id, name="Alice",
            role="Dev", cost_rate=Decimal("1500.00")
        )
        session.add(r1)

        # Seed allocations
        alloc = ProjectAllocation(
            id=uuid.uuid4(), organization_id=org_id,
            resource_id=r1.id, project_id=p1.id,
            allocation_percentage=80, role="Lead Engineer"
        )
        session.add(alloc)
        await session.commit()

    async with TestSessionLocal() as session:
        tool = CheckResourceAllocationTool(session, org_id)
        res = await tool.execute()
        allocations = res["allocations"]

        assert len(allocations) == 1
        item = allocations[0]
        assert item["resource_name"] == "Alice"
        assert item["resource_role"] == "Dev"
        assert item["project_name"] == "Project A"
        assert item["project_status"] == "active"
        assert item["allocation_percentage"] == 80
        assert item["allocation_role"] == "Lead Engineer"
```

---

## `tests/test_celery_briefing.py`

```py
import pytest
import pytest_asyncio
import uuid
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch
from sqlalchemy import select, and_

from app.models.base import Base
from app.modules.users.models import User
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.ai_conversations.models import Conversation, AIMessageModel
from app.modules.business.models import Project, Resource, ProjectAllocation, Transaction, Invoice, Briefing, BriefingStatus, TransactionType, TransactionCategory
from app.workers.celery_app import celery_app
from app.workers.business_tasks import generate_daily_briefings
from app.ai.schemas import MessageRole


@pytest.fixture(autouse=True)
def configure_celery_eager():
    old_eager = celery_app.conf.task_always_eager
    celery_app.conf.task_always_eager = True
    yield
    celery_app.conf.task_always_eager = old_eager


@pytest.fixture
def mock_google_provider():
    with patch("app.ai.pipeline.executor.get_llm_provider") as mock_get_provider:
        mock_provider_instance = mock_get_provider.return_value
        
        async def mock_stream(*args, **kwargs):
            yield "## Morning Executive Briefing\n\n"
            yield "**Financial Performance**:\n"
            yield "- Gross Margin: 60.0%\n"
            yield "- Net Margin: 30.0%\n\n"
            yield "**Resource Utilization**:\n"
            yield "- Alice Developer: 80% (Lead Engineer)\n"

        mock_provider_instance.stream = mock_stream
        yield mock_provider_instance


@pytest.mark.asyncio
async def test_generate_daily_briefings_flow(db, mock_google_provider):
    # 1. Seed database with active organization, member, transactions, and allocations
    org_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    
    # Org
    org = Organization(id=org_id, name="Automated Test Company", slug="automated-test-company")
    db.add(org)
    
    # User
    user = User(
        id=uuid.uuid4(),
        email="ceo@maestro.app",
        first_name="CEO",
        last_name="Owner",
        hashed_password="placeholder",
        is_active=True
    )
    db.add(user)
    await db.commit()
    
    # Org Membership
    member = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=user.id,
        status="active"
    )
    db.add(member)
    
    # Seed transactions
    tx_revenue = Transaction(
        id=uuid.uuid4(), organization_id=org_id, amount=Decimal("10000.00"),
        type=TransactionType.INCOME, category=TransactionCategory.REVENUE, date=date.today() - timedelta(days=1),
        description="Revenue inflow"
    )
    tx_cogs = Transaction(
        id=uuid.uuid4(), organization_id=org_id, amount=Decimal("4000.00"),
        type=TransactionType.EXPENSE, category=TransactionCategory.COGS_INFRASTRUCTURE, date=date.today() - timedelta(days=1),
        description="Infra cost"
    )
    db.add_all([tx_revenue, tx_cogs])
    
    # Seed project & allocation
    proj = Project(
        id=uuid.uuid4(), organization_id=org_id, name="Test Project",
        status="active", budget=Decimal("50000.00"), start_date=date.today() - timedelta(days=30)
    )
    db.add(proj)
    await db.commit()
    
    res = Resource(
        id=uuid.uuid4(), organization_id=org_id, name="Alice Developer",
        role="Engineer", cost_rate=Decimal("1500.00")
    )
    db.add(res)
    await db.commit()
    
    alloc = ProjectAllocation(
        id=uuid.uuid4(), organization_id=org_id, resource_id=res.id, project_id=proj.id,
        allocation_percentage=80, role="Lead Engineer"
    )
    db.add(alloc)
    await db.commit()

    # 2. Trigger the daily briefings Celery task (running synchronously via eager mode)
    task_res = generate_daily_briefings.delay()
    assert task_res.status == "SUCCESS"

    # 3. Verify Briefing record was generated in the DB
    query = select(Briefing).where(and_(Briefing.organization_id == org_id, Briefing.date == date.today()))
    res_query = await db.execute(query)
    briefing = res_query.scalar_one_or_none()
    
    assert briefing is not None
    assert briefing.status == BriefingStatus.COMPLETED
    assert "Morning Executive Briefing" in briefing.content
    assert "Gross Margin: 60.0%" in briefing.content
    assert "Alice Developer: 80%" in briefing.content
    
    # 4. Verify system conversation history has exactly 2 messages
    query_msgs = select(AIMessageModel).join(Conversation).where(
        and_(
            Conversation.organization_id == org_id,
            Conversation.title == "System Daily Briefing Conversation"
        )
    )
    res_msgs = await db.execute(query_msgs)
    messages = res_msgs.scalars().all()
    assert len(messages) == 2
    assert messages[0].role == MessageRole.USER
    assert messages[1].role == MessageRole.ASSISTANT
    assert messages[1].content == briefing.content
```

---

## `alembic/versions/009_add_briefings_table.py`

```py
"""add_briefings_table

Revision ID: 009_add_briefings_table
Revises: 008_business_models
Create Date: 2026-07-11 19:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ENUM

# revision identifiers, used by Alembic.
revision: str = '009_add_briefings_table'
down_revision: Union[str, None] = '008_business_models'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enums
briefing_status_enum = ENUM("processing", "completed", "failed", name="briefingstatus", create_type=False)


def upgrade() -> None:
    # 1. Create Enum
    briefing_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create briefings table
    op.create_table(
        "briefings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("date", sa.Date(), nullable=False, index=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("status", briefing_status_enum, nullable=False, server_default="processing", index=True),
        # Audit & Common fields
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), index=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    # 3. Create unique constraint
    op.create_unique_constraint("uq_briefing_org_date", "briefings", ["organization_id", "date"])


def downgrade() -> None:
    op.drop_table("briefings")
    briefing_status_enum.drop(op.get_bind(), checkfirst=True)
```

---

## `tests/conftest.py`

```py
import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
import uuid

from app.main import app
from app.models.base import Base
from app.dependencies.database import get_db
from app.modules.users.models import User
from app.modules.organizations.models import Organization, OrganizationMember
from app.core.security.jwt import create_access_token

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, autocommit=False, autoflush=False, expire_on_commit=False
)

from app.core import database as db_core
db_core.CelerySessionLocal = TestSessionLocal
db_core.AsyncSessionLocal = TestSessionLocal



@pytest_asyncio.fixture(scope="session", autouse=True)
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        from app.modules.users.models import User  # noqa: F401
        from app.modules.organizations.models import Organization, OrganizationMember  # noqa: F401
        from app.modules.permissions.models import Role, Permission, RolePermission  # noqa: F401
        from app.core.auth.models import RefreshToken, AuditLog  # noqa: F401
        from app.modules.ai_conversations.models import Conversation, AIMessageModel  # noqa: F401
        from app.modules.business.models import Project, Resource, ProjectAllocation, Invoice, Transaction, Briefing  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture()
async def db():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture()
async def async_client():
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def test_user(db: AsyncSession):
    user = User(
        id=uuid.uuid4(),
        email="test_user@maestro.app",
        first_name="Test",
        last_name="User",
        hashed_password="hashed_placeholder",
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture()
async def test_organization(db: AsyncSession):
    org = Organization(
        id=uuid.uuid4(),
        name="Test Organization",
        slug="test-organization"
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@pytest_asyncio.fixture()
async def authenticated_headers(test_user: User, test_organization: Organization, db: AsyncSession):
    member = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=test_organization.id,
        user_id=test_user.id,
        role_id=None,
        status="active"
    )
    db.add(member)
    await db.commit()

    token = create_access_token(subject=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture()
async def auth_headers(authenticated_headers):
    return authenticated_headers
```

---

## `app/modules/ai_conversations/router.py`

```py
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.modules.users.models import User
from app.modules.organizations.services import get_organization
from app.modules.ai_conversations.schemas import ChatRequest
from app.modules.ai_conversations.models import Conversation
from app.modules.ai_conversations.services import AIConversationService
from app.ai.agents.registry import registry

router = APIRouter(prefix="/organizations/{organization_id}/ai", tags=["AI Conversations"])

@router.post("/chat", response_class=StreamingResponse)
async def chat_with_ai(
    organization_id: UUID,
    request: ChatRequest,
    conversation_id: Optional[UUID] = Query(None, description="Optional ID of existing conversation"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Sends a message to the AI agent and returns an SSE stream.
    If conversation_id is not provided in query params, a new conversation is created.
    """
    # 1. Authorization and Organization retrieval
    organization = await get_organization(db, org_id=organization_id, requesting_user_id=current_user.id)

    # 2. Get or Create Conversation
    conversation = await AIConversationService.get_or_create_conversation(
        db, organization_id, conversation_id
    )

    # Update active agent if requested
    if request.agent:
        agent_def = registry.get_agent(request.agent)
        if agent_def:
            conversation.active_agent = request.agent
            db.add(conversation)
            await db.commit()
            from sqlalchemy.orm import selectinload
            from sqlalchemy import select
            stmt = select(Conversation).options(selectinload(Conversation.messages)).where(Conversation.id == conversation.id)
            conversation = (await db.execute(stmt)).scalar_one()

    # 3. Return Streaming Response
    return StreamingResponse(
        AIConversationService.chat_stream(db, current_user, organization, conversation, request.message),
        media_type="text/event-stream"
    )
```

---

## `app/modules/ai_conversations/services.py`

```py
from uuid import UUID
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_conversations.models import Conversation
from app.modules.ai_conversations.repositories import conversation_repository
from app.ai.pipeline.executor import AIExecutionPipeline
from app.modules.users.models import User
from app.modules.organizations.models import Organization


class AIConversationService:
    @staticmethod
    async def get_or_create_conversation(
        db: AsyncSession, organization_id: UUID, conversation_id: Optional[UUID] = None
    ) -> Conversation:
        if conversation_id:
            conv = await conversation_repository.get_with_messages(db, conversation_id)
            if conv:
                return conv
        
        conv = Conversation(organization_id=organization_id)
        db.add(conv)
        await db.commit()
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select
        stmt = select(Conversation).options(selectinload(Conversation.messages)).where(Conversation.id == conv.id)
        conv = (await db.execute(stmt)).scalar_one()
        return conv

    @staticmethod
    async def chat_stream(
        db: AsyncSession, user: User, organization: Organization, conversation: Conversation, prompt: str
    ) -> AsyncGenerator[str, None]:
        pipeline = AIExecutionPipeline(db, user, organization, conversation)
        async for chunk in pipeline.execute(prompt):
            # SSE format leveraging Pydantic models
            yield f"event: {chunk.event_type}\ndata: {chunk.model_dump_json()}\n\n"
        yield "event: end\ndata: {}\n\n"
```

---

```

---

