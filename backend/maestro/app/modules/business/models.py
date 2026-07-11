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
