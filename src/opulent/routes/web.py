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
from opulent.services.diff_service import compute_diff, render_diff_html
from opulent.services.document_service import (
    get_document_by_doc_id,
    get_document_version,
    get_document_versions,
    get_or_create_document,
    list_documents,
    update_document,
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
    drawer: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Main page: display pastebin editor with documents in collapsible left drawer.
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
            "open_drawer": bool(drawer),
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
    edited: int | None = None,
    notice: str | None = None,
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

    # Fetch documents for the collapsible drawer so it can be revealed while viewing a document
    docs, total, total_pages = await list_documents(db=db, page=1, per_page=15)

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
            "is_edited": bool(edited),
            "notice": notice,
            "is_historical": False,
            "viewed_version": doc.current_version,
            "documents": docs,
            "total": total,
            "total_pages": total_pages,
            "page": 1,
        },
    )



@router.get("/docs/{doc_id}/edit", response_class=HTMLResponse)
async def edit_document_page(
    doc_id: str,
    request: Request,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Show edit form pre-filled with the current document's contents.
    """
    doc = await get_document_by_doc_id(db=db, doc_id=doc_id)
    if doc is None:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={"doc_id": doc_id},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    docs, total, total_pages = await list_documents(db=db, page=1, per_page=15)

    return templates.TemplateResponse(
        request=request,
        name="edit.html",
        context={
            "document": doc,
            "formats": SUPPORTED_FORMATS,
            "error": error,
            "documents": docs,
            "total": total,
            "total_pages": total_pages,
            "page": 1,
        },
    )


@router.post("/docs/{doc_id}/edit")
async def handle_edit_document(
    doc_id: str,
    title: str = Form(default="Untitled"),
    format: str = Form(default="markdown"),
    content: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    """
    Save edits to an existing document.
    """
    clean_content = normalize_content(content)
    if not clean_content:
        return RedirectResponse(
            url=f"/docs/{doc_id}/edit?error=Document+content+cannot+be+empty",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    clean_format = normalize_format(format)
    clean_title = (title or "").strip() or "Untitled"

    doc, new_ver, has_changed = await update_document(
        db=db,
        doc_id=doc_id,
        title=clean_title,
        format_type=clean_format,
        content=clean_content,
    )

    if doc is None:
        return RedirectResponse(
            url="/?error=Document+not+found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if not has_changed:
        return RedirectResponse(
            url=f"/docs/{doc.doc_id}?notice=No+changes+were+made",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return RedirectResponse(
        url=f"/docs/{doc.doc_id}?edited=1",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/docs/{doc_id}/history", response_class=HTMLResponse)
async def document_history(
    doc_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    View the full version history timeline of a document.
    """
    doc = await get_document_by_doc_id(db=db, doc_id=doc_id)
    if doc is None:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={"doc_id": doc_id},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    versions = await get_document_versions(db=db, doc_id=doc_id)
    docs, total, total_pages = await list_documents(db=db, page=1, per_page=15)

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={
            "document": doc,
            "versions": versions,
            "documents": docs,
            "total": total,
            "total_pages": total_pages,
            "page": 1,
        },
    )



@router.get("/docs/{doc_id}/history/{version}", response_class=HTMLResponse)
async def view_historical_version(
    doc_id: str,
    version: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    View a specific historical version of a document.
    """
    doc, ver = await get_document_version(db=db, doc_id=doc_id, version=version)
    if doc is None or ver is None:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={"doc_id": f"{doc_id} (v{version})"},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    docs, total, total_pages = await list_documents(db=db, page=1, per_page=15)
    rendered_html = render_document_html(ver.content, ver.format)

    base = str(request.base_url).rstrip("/")
    full_url = f"{base}/docs/{doc.doc_id}/history/{ver.version}"
    raw_url = f"{base}/docs/{doc.doc_id}/history/{ver.version}/raw"
    api_url = f"{base}/api/docs/{doc.doc_id}/history/{ver.version}"

    return templates.TemplateResponse(
        request=request,
        name="view.html",
        context={
            "document": doc,
            "version_obj": ver,
            "rendered_html": rendered_html,
            "full_url": full_url,
            "raw_url": raw_url,
            "api_url": api_url,
            "is_duplicate": False,
            "is_edited": False,
            "is_historical": True,
            "viewed_version": ver.version,
            "documents": docs,
            "total": total,
            "total_pages": total_pages,
            "page": 1,
        },
    )



@router.get("/docs/{doc_id}/history/{version}/raw", response_class=PlainTextResponse)
async def raw_historical_version(
    doc_id: str,
    version: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Raw plain text endpoint for a historical version.
    """
    doc, ver = await get_document_version(db=db, doc_id=doc_id, version=version)
    if doc is None or ver is None:
        return PlainTextResponse(
            "Version not found\n", status_code=status.HTTP_404_NOT_FOUND
        )
    return PlainTextResponse(
        content=ver.content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'inline; filename="{doc.doc_id}-v{ver.version}.txt"'
        },
    )


@router.get("/docs/{doc_id}/compare", response_class=HTMLResponse)
async def compare_document_versions(
    doc_id: str,
    request: Request,
    v1: int | None = Query(default=None),
    v2: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Compare two versions of a document with visual diffing.
    """
    doc = await get_document_by_doc_id(db=db, doc_id=doc_id)
    if doc is None:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={"doc_id": doc_id},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    versions = await get_document_versions(db=db, doc_id=doc_id)
    if not versions:
        return RedirectResponse(url=f"/docs/{doc_id}")

    # Set default comparison: latest version vs previous version
    if v2 is None:
        v2 = doc.current_version
    if v1 is None:
        v1 = max(1, v2 - 1) if v2 > 1 else 1

    _, ver1 = await get_document_version(db=db, doc_id=doc_id, version=v1)
    _, ver2 = await get_document_version(db=db, doc_id=doc_id, version=v2)

    if ver1 is None or ver2 is None:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={"doc_id": f"{doc_id} compare (v{v1} vs v{v2})"},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    diff_result = compute_diff(
        title1=ver1.title,
        format1=ver1.format,
        content1=ver1.content,
        title2=ver2.title,
        format2=ver2.format,
        content2=ver2.content,
    )

    diff_html = render_diff_html(diff_result)
    docs, total, total_pages = await list_documents(db=db, page=1, per_page=15)

    return templates.TemplateResponse(
        request=request,
        name="compare.html",
        context={
            "document": doc,
            "versions": versions,
            "ver1": ver1,
            "ver2": ver2,
            "v1": v1,
            "v2": v2,
            "diff": diff_result,
            "diff_html": diff_html,
            "documents": docs,
            "total": total,
            "total_pages": total_pages,
            "page": 1,
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
