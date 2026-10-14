"""
Knowledge base tools for AI agents.

These tools allow agents to search the organization's knowledge base and read
specific documents. The tools enforce organization-level scoping implicitly
via the execution context.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.ai.tools.base import BaseTool
from app.modules.knowledge.services import KnowledgeService


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SearchKnowledgeBaseInput(BaseModel):
    query: str = Field(..., description="The semantic search query.")
    doc_type: Optional[str] = Field(None, description="Optional filter by document type (e.g. 'policy', 'sop', 'note').")
    limit: int = Field(5, description="Maximum number of chunks to return (max 10).")


class SearchKnowledgeBaseOutput(BaseModel):
    results: List[Dict[str, Any]]
    total_found: int


class GetDocumentInput(BaseModel):
    document_id: str = Field(..., description="The UUID of the document to retrieve.")


class GetDocumentOutput(BaseModel):
    id: str
    title: str
    content: str
    doc_type: str


class ListDocumentsInput(BaseModel):
    limit: int = Field(20, description="Max documents to return")
    page: int = Field(1, description="Page number")


class ListDocumentsOutput(BaseModel):
    documents: List[Dict[str, Any]]
    total: int


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

class SearchKnowledgeBaseTool(BaseTool):
    name = "search_knowledge_base"
    description = "Searches the organization's internal knowledge base for information."
    input_schema = SearchKnowledgeBaseInput
    output_schema = SearchKnowledgeBaseOutput

    def __init__(self, knowledge_service: KnowledgeService, org_id: UUID, user_id: UUID):
        self.service = knowledge_service
        self.org_id = org_id
        # We need the user to enforce private doc visibility
        from app.modules.users.models import User
        self.user = User(id=user_id) # Mock user object with just ID for the service

    async def execute(self, **kwargs) -> Any:
        # Pydantic validation handles parsing
        query = kwargs.get("query")
        limit = min(kwargs.get("limit", 5), 10)
        doc_type = kwargs.get("doc_type")

        filters = {}
        if doc_type:
            filters["doc_type"] = doc_type

        search_resp = await self.service.search(
            org_id=self.org_id,
            user=self.user,
            query=query,
            top_k=limit,
            filters=filters
        )

        results = []
        for r in search_resp.results:
            results.append({
                "document_id": str(r.document_id),
                "title": r.document_title,
                "content_snippet": r.content,
                "score": round(r.score, 3),
                "page": r.page_number,
                "section": r.section
            })

        return {
            "results": results,
            "total_found": search_resp.total_results
        }


class GetDocumentTool(BaseTool):
    name = "get_document"
    description = "Retrieves the full content of a specific knowledge document by its ID."
    input_schema = GetDocumentInput
    output_schema = GetDocumentOutput

    def __init__(self, knowledge_service: KnowledgeService, org_id: UUID):
        self.service = knowledge_service
        self.org_id = org_id

    async def execute(self, **kwargs) -> Any:
        try:
            doc_uuid = UUID(kwargs.get("document_id"))
        except ValueError:
            return {"error": "Invalid document_id format."}

        doc = await self.service.get_document(org_id=self.org_id, doc_id=doc_uuid)
        if not doc:
            return {"error": "Document not found or access denied."}

        return {
            "id": str(doc.id),
            "title": doc.title,
            "content": doc.content or "No text content available.",
            "doc_type": doc.doc_type.value
        }


class ListDocumentsTool(BaseTool):
    name = "list_documents"
    description = "Lists all available knowledge documents in the organization."
    input_schema = ListDocumentsInput
    output_schema = ListDocumentsOutput

    def __init__(self, knowledge_service: KnowledgeService, org_id: UUID):
        self.service = knowledge_service
        self.org_id = org_id

    async def execute(self, **kwargs) -> Any:
        limit = min(kwargs.get("limit", 20), 50)
        page = max(kwargs.get("page", 1), 1)

        result = await self.service.list_documents(org_id=self.org_id, page=page, page_size=limit)
        
        docs = []
        for d in result["items"]:
            docs.append({
                "id": str(d.id),
                "title": d.title,
                "doc_type": d.doc_type.value,
                "status": d.status.value
            })

        return {
            "documents": docs,
            "total": result["total"]
        }
