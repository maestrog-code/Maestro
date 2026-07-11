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
