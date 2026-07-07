import os
from pathlib import Path
from typing import Dict, Any

TEMPLATES_DIR = Path(__file__).parent / "templates"

class PromptBuilder:
    @staticmethod
    def load_template(template_name: str) -> str:
        filepath = TEMPLATES_DIR / f"{template_name}.md"
        if not filepath.exists():
            raise FileNotFoundError(f"Prompt template {template_name}.md not found.")
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def render(template_name: str, context: Dict[str, Any]) -> str:
        """
        Renders a system prompt from a template using the provided context variables.
        For simplicity, it replaces {{variable_name}} with the value.
        """
        template = PromptBuilder.load_template(template_name)
        
        for key, value in context.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
            
        return template
