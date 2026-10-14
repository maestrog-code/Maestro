# MAESTRO — Sprint 011 Step 1 CTO Review Package

Paste this entire document into ChatGPT for the code review.

---

## Context

Sprint 011 Step 1 (Backend Scaffold) is on branch `main`.
This document contains the backend implementation files for the Dashboard API.

---

## `app/api/v1/router.py`

```py
from fastapi import APIRouter
from app.api.v1.endpoints import health
from app.core.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.organizations.router import router as organizations_router
from app.modules.ai_conversations.router import router as ai_conversations_router
from app.modules.knowledge.router import router as knowledge_router
from app.modules.memory.router import router as memory_router
from app.modules.business.router import router as business_router

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(organizations_router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(ai_conversations_router)
api_router.include_router(knowledge_router)
api_router.include_router(memory_router)
api_router.include_router(business_router)
```

---

## `app/modules/business/router.py`

```py
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.modules.users.models import User
from app.modules.organizations.services import get_organization
from app.modules.business.models import Briefing
from app.modules.business.schemas import DashboardMetricsResponse, LatestBriefingResponse
from app.ai.tools.business_tools import FetchFinancialMetricsTool, CheckResourceAllocationTool

router = APIRouter(prefix="/organizations/{organization_id}/dashboard", tags=["Executive Dashboard"])

@router.get("/briefing/latest", response_model=LatestBriefingResponse)
async def get_latest_briefing(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetches the latest autonomous Celery-generated executive brief for the organization."""
    # Enforce organization membership check
    await get_organization(db, org_id=organization_id, requesting_user_id=current_user.id)
    
    query = (
        select(Briefing)
        .where(Briefing.organization_id == organization_id)
        .order_by(Briefing.date.desc())
        .limit(1)
    )
    result = await db.execute(query)
    briefing = result.scalar_one_or_none()
    
    if not briefing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No executive briefings have been generated for this organization yet."
        )
        
    return briefing

@router.get("/metrics", response_model=DashboardMetricsResponse)
async def get_dashboard_metrics(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Aggregates and formats direct database state into unified frontend telemetry."""
    await get_organization(db, org_id=organization_id, requesting_user_id=current_user.id)
    
    # 1. Instantiate our Agent tools programmatically for real-time aggregation
    fin_tool = FetchFinancialMetricsTool(db, organization_id)
    ops_tool = CheckResourceAllocationTool(db, organization_id)
    
    # Define current quarter boundaries (e.g., Q2 trailing window evaluation)
    today = date.today()
    start_of_quarter = date(today.year, 4, 1) # Static placeholder example for dynamic quarter tracking
    
    # Execute tool aggregation logic asynchronously
    fin_data = await fin_tool.execute(start_date=start_of_quarter, end_date=today)
    ops_data = await ops_tool.execute()
    
    metrics = fin_data.get("metrics", {})
    allocations = ops_data.get("allocations", [])
    
    # 2. Compute Engineering Utilization summary metrics
    total_alloc = sum(a["allocation_percentage"] for a in allocations)
    unique_resources = len(set(a["resource_name"] for a in allocations))
    avg_utilization = round(total_alloc / unique_resources, 0) if unique_resources > 0 else 0.0
    
    # Determine risk zone threshold
    status_zone = "warning" if avg_utilization >= 85 else "up"
    
    # 3. Transform database project/resource rows into specific UI component properties
    # Group allocations by project name to mirror v0's ProjectRow structure
    project_map = {}
    for alloc in allocations:
        p_name = alloc["project_name"]
        if p_name not in project_map:
            # Map database status enums to UI string badges
            ui_status = "On Track"
            if alloc["project_status"] == "on_hold":
                ui_status = "At Risk"
            elif alloc["project_status"] == "completed":
                ui_status = "Ahead"
                
            project_map[p_name] = {
                "name": p_name,
                "client": "Enterprise Account", # Placeholder client string or link to client model
                "status": ui_status,
                "allocation": 0
            }
        # Compound utilization limits
        project_map[p_name]["allocation"] = min(project_map[p_name]["allocation"] + alloc["allocation_percentage"], 100)

    return {
        "financials": {
            "total_revenue": f"${metrics.get('total_revenue', 0.0):,}",
            "net_margin": f"{metrics.get('net_margin_percentage', 0.0)}%",
            "gross_revenue_delta": "+6.3%", # Hardcoded or dynamically pulled from historical comparison queries
            "net_margin_delta": "+2.5%",
            "revenue_note": "vs. last quarter trend",
            "margin_note": "Above target threshold"
        },
        "operations": {
            "avg_utilization": f"{int(avg_utilization)}%",
            "delta": "+11%" if avg_utilization > 80 else "Stable",
            "trend": status_zone,
            "note": "Approaching burnout risk zone" if status_zone == "warning" else "Optimal workload limits"
        },
        "active_projects": list(project_map.values())[:5] # Return top 5 projects
    }
```

---

## `app/modules/business/schemas.py`

```py
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from app.modules.business.models import ProjectStatus, InvoiceStatus, TransactionType, TransactionCategory, BriefingStatus


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


# ─── Briefing Schemas ───────────────────────────────────────────────────────────

class BriefingCreate(BaseModel):
    date: date
    content: Optional[str] = None
    status: BriefingStatus = BriefingStatus.PROCESSING


class BriefingUpdate(BaseModel):
    content: Optional[str] = None
    status: Optional[BriefingStatus] = None


class BriefingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    date: date
    content: Optional[str]
    status: BriefingStatus
    created_at: datetime
    updated_at: datetime


# ─── Dashboard Schemas ──────────────────────────────────────────────────────────

class DashboardMetricsResponse(BaseModel):
    financials: Dict[str, Any]
    operations: Dict[str, Any]
    active_projects: List[Dict[str, Any]]

class LatestBriefingResponse(BaseModel):
    id: UUID
    date: date
    status: BriefingStatus
    content: Optional[str]
```

---

