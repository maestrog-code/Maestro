from app.ai.agents.registry import AgentDefinition, registry
from app.core.ai_settings import ai_settings

cfo_agent = AgentDefinition(
    id="CFO",
    name="Chief Financial Officer",
    version="1.0",
    system_prompt_template="cfo_system",
    tools=[],  # Will populate as tools are added
    provider=ai_settings.DEFAULT_PROVIDER,
    temperature=ai_settings.DEFAULT_TEMPERATURE,
    max_tokens=2048,
    enabled=True,
)

registry.register(cfo_agent)
