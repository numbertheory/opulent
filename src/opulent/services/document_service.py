from math import ceil
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from opulent.formatter import normalize_format
from opulent.hasher import compute_content_hash, generate_doc_id, normalize_content
from opulent.models import Document


async def get_or_create_document(
    db: AsyncSession,
    title: str,
    format_type: str,
    content: str,
) -> tuple[Document, bool]:
    """
    Get an existing document if identical content already exists,
    or create a new document with a unique doc_id derived from its content hash.

    Returns:
        tuple[Document, bool]: (document, is_duplicate)
    """
    clean_title = (title or "").strip() or "Untitled"
    clean_format = normalize_format(format_type)
    clean_content = normalize_content(content)

    content_hash = compute_content_hash(clean_title, clean_format, clean_content)

    # Check if a document with identical content hash already exists
    stmt = select(Document).where(Document.content_hash == content_hash)
    result = await db.execute(stmt)
    existing_doc = result.scalars().first()
    if existing_doc is not None:
        return existing_doc, True

    # Generate a deterministic doc-id, handling collisions if any
    attempt = 0
    doc_id = ""
    while True:
        candidate_id = generate_doc_id(content_hash, attempt=attempt)
        check_stmt = select(Document.id).where(Document.doc_id == candidate_id)
        check_res = await db.execute(check_stmt)
        if check_res.scalars().first() is None:
            doc_id = candidate_id
            break
        attempt += 1

    new_doc = Document(
        doc_id=doc_id,
        title=clean_title,
        content=clean_content,
        format=clean_format,
        content_hash=content_hash,
    )
    db.add(new_doc)

    try:
        await db.commit()
        await db.refresh(new_doc)
        return new_doc, False
    except IntegrityError:
        # Concurrent insert of identical content or collision
        await db.rollback()
        retry_stmt = select(Document).where(Document.content_hash == content_hash)
        retry_res = await db.execute(retry_stmt)
        duplicate_doc = retry_res.scalars().first()
        if duplicate_doc is not None:
            return duplicate_doc, True
        raise


async def get_document_by_doc_id(
    db: AsyncSession,
    doc_id: str,
    increment_views: bool = False,
) -> Document | None:
    """Fetch a document by its public doc_id, optionally incrementing view count."""
    stmt = select(Document).where(Document.doc_id == doc_id)
    result = await db.execute(stmt)
    doc = result.scalars().first()

    if doc is not None and increment_views:
        await db.execute(
            update(Document)
            .where(Document.id == doc.id)
            .values(views=Document.views + 1)
        )
        await db.commit()
        await db.refresh(doc)

    return doc


async def list_documents(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 15,
) -> tuple[list[Document], int, int]:
    """
    Return a paginated list of documents sorted by most recent first.

    Returns:
        tuple[list[Document], int, int]: (documents, total_items, total_pages)
    """
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = 15

    # Total count
    count_stmt = select(func.count(Document.id))
    count_res = await db.execute(count_stmt)
    total = count_res.scalar_one() or 0

    total_pages = max(1, ceil(total / per_page)) if total > 0 else 1

    # Items for current page
    offset = (page - 1) * per_page
    stmt = (
        select(Document)
        .order_by(Document.created_at.desc(), Document.id.desc())
        .offset(offset)
        .limit(per_page)
    )
    res = await db.execute(stmt)
    documents = list(res.scalars().all())

    return documents, total, total_pages
