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
    original_goal: str = Field(
        ...,
        description="The original overall goal or user request that prompted this delegation, to provide full context."
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

class UpdateTaskStatusInput(BaseModel):
    step: str = Field(..., description="The name or description of the current planning step.")
    status: str = Field(..., description="The status of the step (e.g., 'IN_PROGRESS', 'COMPLETED', 'PENDING', 'FAILED').")
    notes: str = Field(..., description="Internal scratchpad notes, findings, or next actions.")

class UpdateTaskStatusOutput(BaseModel):
    result: str

class UpdateTaskStatusTool(BaseTool):
    """
    Allows an agent to maintain a scratchpad or state tracking for multi-step tasks.
    """
    name: str = "update_task_status"
    description: str = (
        "Maintain a scratchpad of your current plan and progress. Use this to explicitly track "
        "what steps you have completed, what you are currently doing, and what comes next."
    )
    input_schema = UpdateTaskStatusInput
    output_schema = UpdateTaskStatusOutput

    async def execute(self, step: str, status: str, notes: str, **kwargs) -> Any:
        # Just returning it so the LLM has it in the context window
        return f"Task State Updated.\nStep: {step}\nStatus: {status}\nNotes: {notes}"
