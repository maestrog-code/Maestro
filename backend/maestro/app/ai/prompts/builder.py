"""
Prompt building module.
Converts a context object into a rendered system prompt for the LLM.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List

from app.modules.users.models import User
from app.modules.organizations.models import Organization

TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass
class PromptContext:
    """
    Structured context for rendering a system prompt.
    Replaces string concatenation with explicit structured attributes.
    """
    user: User
    organization: Organization
    documents: List[Dict[str, Any]] = field(default_factory=list)
    memories: List[Dict[str, Any]] = field(default_factory=list)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to flat dictionary for template rendering."""
        # Format memory context
        memory_context = ""
        if self.memories:
            mem_texts = ["--- PAST MEMORY ---"]
            for mem in self.memories:
                mem_texts.append(f"[{mem.get('memory_type', 'FACT').upper()}] {mem.get('content', '')}")
            memory_context = "\n".join(mem_texts)
            
        # Format knowledge context if documents exist (implicit RAG)
        knowledge_context = ""
        if self.documents:
            doc_texts = ["--- KNOWLEDGE BASE ---"]
            for doc in self.documents:
                doc_texts.append(
                    f"Document: {doc.get('title', 'Unknown')}\n"
                    f"{doc.get('content', '')}"
                )
            knowledge_context = "\n\n".join(doc_texts)

        return {
            "company_name": self.organization.name,
            "organization_name": self.organization.name,
            "user_first_name": self.user.first_name,
            "user_last_name": self.user.last_name,
            "memory_context": memory_context,
            "knowledge_context": knowledge_context,
            **self.metadata
        }


class PromptBuilder:
    @staticmethod
    def load_template(template_name: str) -> str:
        filepath = TEMPLATES_DIR / f"{template_name}.md"
        if not filepath.exists():
            raise FileNotFoundError(f"Prompt template {template_name}.md not found.")
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def render(template_name: str, context: PromptContext) -> str:
        """
        Renders a system prompt from a template using the structured PromptContext.
        """
        template = PromptBuilder.load_template(template_name)
        
        context_dict = context.to_dict()
        for key, value in context_dict.items():
            # Only replace if the placeholder exists in the template
            placeholder = f"{{{{{key}}}}}"
            if placeholder in template:
                template = template.replace(placeholder, str(value))
            
        return template
