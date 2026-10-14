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

