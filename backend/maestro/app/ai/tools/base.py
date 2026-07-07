from abc import ABC, abstractmethod
from typing import Any, Dict, Type, Optional
from pydantic import BaseModel

class BaseTool(ABC):
    name: str
    description: str
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]
    permission_required: Optional[str] = None

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        pass

    def get_json_schema(self) -> Dict[str, Any]:
        """Returns the JSON schema representation of the tool for the LLM."""
        schema = self.input_schema.model_json_schema()
        # Clean up schema for typical LLM consumption
        if "$defs" in schema:
            del schema["$defs"]
        return {
            "name": self.name,
            "description": self.description,
            "parameters": schema
        }
