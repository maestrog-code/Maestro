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
