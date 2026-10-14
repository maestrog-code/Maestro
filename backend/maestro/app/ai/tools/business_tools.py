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
