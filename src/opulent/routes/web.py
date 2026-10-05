from pathlib import Path
from fastapi import APIRouter, Depends, Form, Query, Request, Response, status
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from opulent.database import get_db
from opulent.formatter import (
    SUPPORTED_FORMATS,
    get_pygments_css,
    normalize_format,
    render_document_html,
)
from opulent.hasher import normalize_content
from opulent.services.document_service import (
    get_document_by_doc_id,
    get_or_create_document,
    list_documents,
)

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=50),
    error: str | None = None,
    notice: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Main page: display pastebin editor and paginated list of documents.
    """
    documents, total, total_pages = await list_documents(
        db=db, page=page, per_page=per_page
    )

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "documents": documents,
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "formats": SUPPORTED_FORMATS,
            "error": error,
            "notice": notice,
        },
    )


@router.post("/docs")
async def create_document_form(
    title: str = Form(default="Untitled"),
    format: str = Form(default="markdown"),
    content: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle document creation from web browser form.
    """
    clean_content = normalize_content(content)
    if not clean_content:
        return RedirectResponse(
            url="/?error=Document+content+cannot+be+empty",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    clean_format = normalize_format(format)
    clean_title = (title or "").strip() or "Untitled"

    doc, is_duplicate = await get_or_create_document(
        db=db,
        title=clean_title,
        format_type=clean_format,
        content=clean_content,
    )

    redirect_url = f"/docs/{doc.doc_id}"
    if is_duplicate:
        redirect_url += "?duplicate=1"

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/docs/{doc_id}", response_class=HTMLResponse)
async def view_document(
    doc_id: str,
    request: Request,
    duplicate: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    View a document with formatting applied.
    """
    doc = await get_document_by_doc_id(db=db, doc_id=doc_id, increment_views=True)
    if doc is None:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={"doc_id": doc_id},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    rendered_html = render_document_html(doc.content, doc.format)

    base = str(request.base_url).rstrip("/")
    full_url = f"{base}/docs/{doc.doc_id}"
    raw_url = f"{base}/docs/{doc.doc_id}/raw"
    api_url = f"{base}/api/docs/{doc.doc_id}"

    return templates.TemplateResponse(
        request=request,
        name="view.html",
        context={
            "document": doc,
            "rendered_html": rendered_html,
            "full_url": full_url,
            "raw_url": raw_url,
            "api_url": api_url,
            "is_duplicate": bool(duplicate),
        },
    )



@router.get("/docs/{doc_id}/raw", response_class=PlainTextResponse)
async def raw_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Direct raw text endpoint for documents.
    """
    doc = await get_document_by_doc_id(db=db, doc_id=doc_id, increment_views=True)
    if doc is None:
        return PlainTextResponse(
            "Document not found\n", status_code=status.HTTP_404_NOT_FOUND
        )
    return PlainTextResponse(
        content=doc.content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'inline; filename="{doc.doc_id}.txt"'},
    )


@router.get("/pygments.css")
async def pygments_css():
    """Dynamically serve Pygments syntax highlighting CSS stylesheet."""
    css_content = get_pygments_css("one-dark")
    return Response(content=css_content, media_type="text/css")
