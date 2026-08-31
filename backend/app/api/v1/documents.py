import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.repositories.document_repository import DocumentRepository
from app.ingestion.document_ingestion import DocumentIngestionService
from app.normalization.validators import DocumentValidationError
from app.schemas.document import (
    DocumentCreate,
    DocumentIngestionResult,
    DocumentResponse,
    DocumentVersionResponse,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentIngestionResult,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    doc_in: DocumentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Receive raw document -> Normalize & Validate -> Persist Document & Version."""
    ingestion_service = DocumentIngestionService(db)

    try:
        document, version, normalized = await ingestion_service.ingest_document(doc_in)
        await db.commit()
    except DocumentValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        )

    version_response = DocumentVersionResponse.model_validate(version)
    doc_response = DocumentResponse(
        id=document.id,
        organization_id=document.organization_id,
        source_id=document.source_id,
        external_id=document.external_id,
        title=document.title,
        document_type=document.document_type,
        content_uri=document.content_uri,
        content_hash=document.content_hash,
        status=document.status,
        created_at=document.created_at,
        updated_at=document.updated_at,
        versions=[version_response],
    )

    return DocumentIngestionResult(
        document=doc_response,
        current_version=version_response,
        normalized=True,
        message=f"Document ingested successfully with version {version.version_number}. Document type: {normalized.document_type}.",
    )



@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    repo = DocumentRepository(db)
    document = await repo.get_by_id_with_versions(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return DocumentResponse.model_validate(document)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    organization_id: uuid.UUID = Query(..., description="Organization ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    repo = DocumentRepository(db)
    documents = await repo.list_by_organization(
        organization_id=organization_id,
        limit=limit,
        offset=offset,
    )
    return [DocumentResponse.model_validate(d) for d in documents]
