from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from opulent.database import get_db
from opulent.formatter import normalize_format
from opulent.hasher import normalize_content
from opulent.models import Document, DocumentVersion
from opulent.schemas import (
    DiffLineSchema,
    DocumentCompareResponse,
    DocumentCreate,
    DocumentHistoryResponse,
    DocumentListItem,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdate,
    DocumentVersionResponse,
)
from opulent.services.diff_service import compute_diff
from opulent.services.document_service import (
    get_document_by_doc_id,
    get_document_version,
    get_document_versions,
    get_or_create_document,
    list_documents,
    update_document,
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
        updated_at=doc.updated_at,
        views=doc.views,
        version=doc.current_version,
        version_count=doc.version_count,
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
        format_icon_svg=doc.format_icon_svg,
        snippet=doc.snippet,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        effective_updated_at=doc.effective_updated_at,
        views=doc.views,
        version_count=doc.version_count,
        character_count=doc.character_count,
        line_count=doc.line_count,
        url=f"{base}/docs/{doc.doc_id}",
    )


def to_version_response(
    doc: Document, version: DocumentVersion, request: Request
) -> DocumentVersionResponse:
    base = str(request.base_url).rstrip("/")
    return DocumentVersionResponse(
        version=version.version,
        title=version.title,
        format=version.format,
        display_format=version.display_format,
        content=version.content,
        created_at=version.created_at,
        character_count=version.character_count,
        line_count=version.line_count,
        word_count=version.word_count,
        url=f"{base}/docs/{doc.doc_id}/history/{version.version}",
        raw_url=f"{base}/docs/{doc.doc_id}/history/{version.version}/raw",
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


@router.put("/{doc_id}", response_model=DocumentResponse)
async def edit_document(
    doc_id: str,
    doc_update: DocumentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Save edits to an existing document and record a new version in its history.
    """
    cleaned_content = normalize_content(doc_update.content)
    if not cleaned_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document content cannot be empty",
        )

    doc, new_ver, has_changed = await update_document(
        db=db,
        doc_id=doc_id,
        title=doc_update.title,
        format_type=normalize_format(doc_update.format),
        content=cleaned_content,
    )

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


@router.get("/{doc_id}/history", response_model=DocumentHistoryResponse)
async def get_history(
    doc_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """View the version history of any document."""
    doc = await get_document_by_doc_id(db=db, doc_id=doc_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found",
        )

    versions = await get_document_versions(db=db, doc_id=doc_id)
    v_responses = [to_version_response(doc, v, request) for v in versions]

    return DocumentHistoryResponse(
        doc_id=doc.doc_id,
        title=doc.title,
        current_version=doc.current_version,
        total_versions=len(versions),
        versions=v_responses,
    )


@router.get("/{doc_id}/history/{version}", response_model=DocumentVersionResponse)
async def get_historical_version(
    doc_id: str,
    version: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """View a specific historical version of a document."""
    doc, ver = await get_document_version(db=db, doc_id=doc_id, version=version)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found",
        )
    if ver is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version} not found for document '{doc_id}'",
        )

    return to_version_response(doc, ver, request)


@router.get("/{doc_id}/history/{version}/raw", response_class=PlainTextResponse)
async def get_historical_version_raw(
    doc_id: str,
    version: int,
    db: AsyncSession = Depends(get_db),
):
    """Grab the raw full text of a specific historical version."""
    doc, ver = await get_document_version(db=db, doc_id=doc_id, version=version)
    if doc is None or ver is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' version {version} not found",
        )

    return PlainTextResponse(
        content=ver.content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'inline; filename="{doc.doc_id}-v{ver.version}.txt"'
        },
    )


@router.get("/{doc_id}/compare", response_model=DocumentCompareResponse)
async def compare_versions(
    doc_id: str,
    v1: int = Query(..., description="First version number (older)"),
    v2: int = Query(..., description="Second version number (newer)"),
    db: AsyncSession = Depends(get_db),
):
    """Compare two versions of a document and view changes/diff."""
    doc = await get_document_by_doc_id(db=db, doc_id=doc_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found",
        )

    _, ver1 = await get_document_version(db=db, doc_id=doc_id, version=v1)
    if ver1 is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {v1} not found for document '{doc_id}'",
        )

    _, ver2 = await get_document_version(db=db, doc_id=doc_id, version=v2)
    if ver2 is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {v2} not found for document '{doc_id}'",
        )

    diff_res = compute_diff(
        title1=ver1.title,
        format1=ver1.format,
        content1=ver1.content,
        title2=ver2.title,
        format2=ver2.format,
        content2=ver2.content,
    )

    return DocumentCompareResponse(
        doc_id=doc.doc_id,
        v1=ver1.version,
        v2=ver2.version,
        title_v1=diff_res.title_v1,
        title_v2=diff_res.title_v2,
        format_v1=diff_res.format_v1,
        format_v2=diff_res.format_v2,
        additions=diff_res.additions,
        deletions=diff_res.deletions,
        lines=[DiffLineSchema(**line.to_dict()) for line in diff_res.lines],
    )
