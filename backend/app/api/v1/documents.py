import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
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
    if doc_in.title:
        doc_in.title = doc_in.title.replace("\x00", "")
    if doc_in.content:
        doc_in.content = doc_in.content.replace("\x00", "")
    if doc_in.external_id:
        doc_in.external_id = doc_in.external_id.replace("\x00", "")
    if doc_in.document_type:
        doc_in.document_type = doc_in.document_type.replace("\x00", "")

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


@router.post(
    "/upload",
    response_model=DocumentIngestionResult,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document_file(
    file: UploadFile = File(...),
    organization_id: uuid.UUID = Form(uuid.UUID("11111111-1111-1111-1111-111111111111")),
    source_id: uuid.UUID = Form(uuid.UUID("44444444-4444-4444-4444-444444444444")),
    title: str | None = Form(None),
    document_type: str = Form("policy"),
    external_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file (.pdf, .docx, .txt, .md, .json, .csv) and ingest into PostgreSQL."""
    import io
    raw_bytes = await file.read()
    filename = file.filename or "uploaded_doc.txt"
    doc_title = title or filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
    doc_title = doc_title.replace("\x00", "").strip()
    doc_external_id = (external_id or f"file://{filename}").replace("\x00", "").strip()

    content_text = ""
    lower_filename = filename.lower()

    if lower_filename.endswith(".pdf"):
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
            pages_text = []
            for page_num, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    pages_text.append(f"## Page {page_num}\n{page_text.strip()}")
            if pages_text:
                content_text = f"# {doc_title}\n\n" + "\n\n".join(pages_text)
            else:
                content_text = f"# {doc_title}\n\nIngested PDF document {filename} ({len(reader.pages)} pages)."
        except Exception:
            try:
                content_text = raw_bytes.decode("utf-8", errors="ignore")
            except Exception:
                content_text = f"# {doc_title}\n\nIngested PDF document {filename}."
    elif lower_filename.endswith((".docx", ".doc")):
        try:
            import docx
            doc = docx.Document(io.BytesIO(raw_bytes))
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        paragraphs.append(row_text)
            if paragraphs:
                content_text = f"# {doc_title}\n\n" + "\n\n".join(paragraphs)
            else:
                content_text = f"# {doc_title}\n\nIngested Word document {filename}."
        except Exception:
            try:
                import zipfile
                import xml.etree.ElementTree as ET
                with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                    xml_content = zf.read("word/document.xml")
                    tree = ET.fromstring(xml_content)
                    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                    paragraphs = []
                    for p in tree.findall(".//w:p", ns):
                        texts = [node.text for node in p.findall(".//w:t", ns) if node.text]
                        if texts:
                            paragraphs.append("".join(texts).strip())
                    paragraphs = [p for p in paragraphs if p]
                    if paragraphs:
                        content_text = f"# {doc_title}\n\n" + "\n\n".join(paragraphs)
                    else:
                        content_text = f"# {doc_title}\n\nIngested Word document {filename}."
            except Exception:
                content_text = f"# {doc_title}\n\nIngested Word document {filename}."
    else:
        try:
            content_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content_text = raw_bytes.decode("latin-1", errors="replace")
            except Exception:
                content_text = f"# {doc_title}\n\nIngested file {filename}."

    # Strip any null bytes (PostgreSQL UTF-8 restriction)
    content_text = content_text.replace("\x00", "")

    if not content_text.strip():
        content_text = f"# {doc_title}\n\nIngested from file {filename}."

    doc_in = DocumentCreate(
        organization_id=organization_id,
        source_id=source_id,
        title=doc_title,
        content=content_text,
        document_type=document_type.replace("\x00", ""),
        external_id=doc_external_id,
        metadata={"filename": filename, "file_size": len(raw_bytes)},
    )

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
        message=f"File '{filename}' ingested successfully with version {version.version_number}.",
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
