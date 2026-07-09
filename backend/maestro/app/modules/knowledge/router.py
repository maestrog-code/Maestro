"""
API Router for Knowledge Management.
Handles document ingestion, listing, search, and retrieval.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth.dependencies import get_current_user
from app.modules.users.models import User
from app.modules.organizations.services import OrganizationPermissionService
from app.modules.knowledge.services import KnowledgeService
from app.modules.knowledge.schemas import (
    DocumentCreate,
    DocumentUploadResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    DocumentResponse,
    DocumentListResponse
)
from app.modules.knowledge.models import DocType, Visibility


router = APIRouter(prefix="/organizations/{organization_id}/knowledge", tags=["Knowledge"])


@router.post("/documents/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    organization_id: UUID,
    file: UploadFile = File(...),
    title: str = Form(...),
    doc_type: DocType = Form(DocType.file),
    visibility: Visibility = Form(Visibility.org),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a file to the knowledge base.
    Returns 202 Accepted because extraction and chunking happen asynchronously.
    """
    await OrganizationPermissionService.require_member(db, organization_id, current_user.id)
    service = KnowledgeService(db)

    document = await service.upload_file(
        org_id=organization_id,
        user=current_user,
        title=title,
        file=file,
        doc_type=doc_type,
        visibility=visibility,
    )
    return DocumentUploadResponse(document_id=document.id, status=document.status)


@router.post("/documents/note", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_inline_note(
    organization_id: UUID,
    title: str = Form(...),
    content: str = Form(...),
    doc_type: DocType = Form(DocType.note),
    visibility: Visibility = Form(Visibility.org),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create an inline text document in the knowledge base without uploading a file.
    """
    await OrganizationPermissionService.require_member(db, organization_id, current_user.id)
    service = KnowledgeService(db)

    document = await service.create_note(
        org_id=organization_id,
        user=current_user,
        data=DocumentCreate(
            title=title,
            content=content,
            doc_type=doc_type,
            visibility=visibility,
        ),
    )
    return DocumentUploadResponse(document_id=document.id, status=document.status)


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    organization_id: UUID,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List documents in the knowledge base."""
    await OrganizationPermissionService.require_member(db, organization_id, current_user.id)
    service = KnowledgeService(db)
    return await service.list_documents(organization_id, page, page_size)


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    organization_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get document details."""
    await OrganizationPermissionService.require_member(db, organization_id, current_user.id)
    service = KnowledgeService(db)
    
    doc = await service.get_document(organization_id, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    return doc


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    organization_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a document and its embeddings."""
    await OrganizationPermissionService.require_member(db, organization_id, current_user.id)
    service = KnowledgeService(db)
    success = await service.delete_document(organization_id, document_id, current_user)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    organization_id: UUID,
    request: KnowledgeSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search the knowledge base via vector similarity."""
    await OrganizationPermissionService.require_member(db, organization_id, current_user.id)
    service = KnowledgeService(db)
    
    return await service.search(
        org_id=organization_id,
        user=current_user,
        query=request.query,
        top_k=request.top_k,
        filters=request.filters
    )
