import logging
from typing import Any
from pydantic import BaseModel, Field
from app.ai.tools.base import BaseTool
from app.ai.agents.registry import registry

logger = logging.getLogger(__name__)

class DelegateTaskInput(BaseModel):
    target_agent: str = Field(
        ...,
        description="The role name of the specialized agent to delegate to (e.g., 'CFO', 'COO', 'CTO')."
    )
    instructions: str = Field(
        ...,
        description="Detailed instructions and context for the sub-task. Be as explicit as possible."
    )


class DelegateTaskOutput(BaseModel):
    result: str

class DelegateTaskTool(BaseTool):
    """
    Allows a Supervisor agent (like the CEO) to delegate a sub-task to a specialized agent.
    """
    name: str = "delegate_task"
    description: str = (
        "Delegate a sub-task to a specialized agent. Use this when you need domain-specific "
        "analysis (e.g., financial from the CFO) to answer the user's request."
    )
    input_schema = DelegateTaskInput
    output_schema = DelegateTaskOutput

    async def execute(self, target_agent: str, instructions: str, **kwargs) -> Any:
        """
        The actual execution of this tool is intercepted by the AIExecutionPipeline
        to handle recursion, context building, and database persistence.
        This method serves as a fallback or placeholder if invoked directly outside the pipeline.
        """
        if not registry.get_agent(target_agent):
            return f"Error: Agent '{target_agent}' not found in the registry."

        logger.warning("delegate_task was executed without pipeline interception.")
        return "Sub-task delegated successfully."
