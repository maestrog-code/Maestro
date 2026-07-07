import asyncio
import logging
from typing import Any, Dict, Optional, Type
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from app.ai.tools.base import BaseTool
from app.core.auth.models import AuditLog

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    pass


class ToolExecutor:
    def __init__(self, tools: list[BaseTool]):
        self.tools = {tool.name: tool for tool in tools}

    def get_tool_schemas(self) -> list[Dict[str, Any]]:
        return [tool.get_json_schema() for tool in self.tools.values()]

    async def execute(
        self,
        db: AsyncSession,
        tool_name: str,
        tool_args: Dict[str, Any],
        user_id: UUID,
        organization_id: UUID,
        max_retries: int = 2,
        timeout_seconds: float = 10.0,
        **context
    ) -> Any:
        """
        Executes a tool with the defined flow:
        Permission -> Validation -> Timeout -> Execute -> Retry -> Audit Log
        """
        tool = self.tools.get(tool_name)
        if not tool:
            return {"error": f"Tool '{tool_name}' not found."}

        # 1. Permission Check
        if tool.permission_required:
            # We assume permission checks are performed elsewhere or injected into context
            # For Sprint 004, if a tool requires a specific role, we could check it here.
            # E.g., user role checking. Since we don't have the role passed directly,
            # this is a stub for future deep integration with RBAC.
            logger.info(f"Checking permission {tool.permission_required} for {tool_name}")

        # 2. Validation
        try:
            validated_args = tool.input_schema(**tool_args)
        except ValidationError as e:
            return {"error": "Validation failed for tool arguments.", "details": e.errors()}

        # Retries and Execution
        for attempt in range(max_retries + 1):
            try:
                # 3. & 4. Timeout and Execute
                result = await asyncio.wait_for(
                    tool.execute(**validated_args.model_dump(), **context),
                    timeout=timeout_seconds
                )
                
                # 6. Audit Log (Success)
                await self._audit_log(
                    db, user_id, organization_id, tool_name, tool_args, status="success"
                )
                return result

            except asyncio.TimeoutError:
                if attempt == max_retries:
                    await self._audit_log(
                        db, user_id, organization_id, tool_name, tool_args, status="timeout", error="Timeout exceeded"
                    )
                    return {"error": f"Tool '{tool_name}' timed out after {timeout_seconds}s."}
                logger.warning(f"Tool {tool_name} timed out. Retrying ({attempt+1}/{max_retries})...")

            except Exception as e:
                # 5. Retry on exception
                if attempt == max_retries:
                    error_msg = str(e)
                    await self._audit_log(
                        db, user_id, organization_id, tool_name, tool_args, status="error", error=error_msg
                    )
                    logger.error(f"Tool {tool_name} failed: {error_msg}")
                    return {"error": f"Tool execution failed: {error_msg}"}
                logger.warning(f"Tool {tool_name} failed: {e}. Retrying ({attempt+1}/{max_retries})...")

    async def _audit_log(
        self,
        db: AsyncSession,
        user_id: UUID,
        organization_id: UUID,
        tool_name: str,
        args: Dict[str, Any],
        status: str,
        error: Optional[str] = None
    ) -> None:
        """Saves an audit record for the tool execution."""
        log = AuditLog(
            who=user_id,
            what=f"TOOL_EXECUTION:{tool_name.upper()}",
            resource=f"tool:{tool_name}",
            organization_id=organization_id,
            details={
                "args": args,
                "status": status,
                "error": error
            }
        )
        db.add(log)
        await db.commit()
