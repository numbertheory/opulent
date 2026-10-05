from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from opulent.database import get_db
from opulent.formatter import normalize_format
from opulent.hasher import normalize_content
from opulent.models import Document
from opulent.schemas import (
    DocumentCreate,
    DocumentListItem,
    DocumentListResponse,
    DocumentResponse,
)
from opulent.services.document_service import (
    get_document_by_doc_id,
    get_or_create_document,
    list_documents,
)

router = APIRouter(prefix="/api/docs", tags=["documents"])


def to_document_response(
    doc: Document, request: Request, is_duplicate: bool = False
) -> DocumentResponse:
    base = str(request.base_url).rstrip("/")
    return DocumentResponse(
        id=doc.doc_id,
        title=doc.title,
        content=doc.content,
        format=doc.format,
        display_format=doc.display_format,
        created_at=doc.created_at,
        views=doc.views,
        character_count=doc.character_count,
        line_count=doc.line_count,
        word_count=doc.word_count,
        url=f"{base}/docs/{doc.doc_id}",
        raw_url=f"{base}/docs/{doc.doc_id}/raw",
        is_duplicate=is_duplicate,
    )


def to_document_list_item(doc: Document, request: Request) -> DocumentListItem:
    base = str(request.base_url).rstrip("/")
    return DocumentListItem(
        id=doc.doc_id,
        title=doc.title,
        format=doc.format,
        display_format=doc.display_format,
        snippet=doc.snippet,
        created_at=doc.created_at,
        views=doc.views,
        character_count=doc.character_count,
        line_count=doc.line_count,
        url=f"{base}/docs/{doc.doc_id}",
    )


@router.post("", response_model=DocumentResponse)
async def create_document(
    doc_in: DocumentCreate,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new document or return the existing one if content is identical.
    Returns 201 Created for new documents, or 200 OK if duplicate.
    """
    cleaned_content = normalize_content(doc_in.content)
    if not cleaned_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document content cannot be empty",
        )

    doc, is_duplicate = await get_or_create_document(
        db=db,
        title=doc_in.title,
        format_type=normalize_format(doc_in.format),
        content=cleaned_content,
    )

    if not is_duplicate:
        response.status_code = status.HTTP_201_CREATED
    else:
        response.status_code = status.HTTP_200_OK

    return to_document_response(doc, request, is_duplicate=is_duplicate)


@router.get("", response_model=DocumentListResponse)
async def get_documents(
    request: Request,
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=15, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """List documents with pagination."""
    docs, total, total_pages = await list_documents(db=db, page=page, per_page=per_page)
    items = [to_document_list_item(d, request) for d in docs]
    return DocumentListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Grab the full text and metadata of a document by doc-id."""
    doc = await get_document_by_doc_id(db=db, doc_id=doc_id, increment_views=True)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found",
        )
    return to_document_response(doc, request)


@router.get("/{doc_id}/raw", response_class=PlainTextResponse)
async def get_document_raw(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Grab the raw full text of a document as plain text."""
    doc = await get_document_by_doc_id(db=db, doc_id=doc_id, increment_views=True)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found",
        )
    return PlainTextResponse(
        content=doc.content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'inline; filename="{doc.doc_id}.txt"'},
    )
