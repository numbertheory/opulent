from datetime import datetime, timezone
from math import ceil
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from opulent.formatter import normalize_format
from opulent.hasher import compute_content_hash, generate_doc_id, normalize_content
from opulent.models import Document, DocumentVersion


async def get_or_create_document(
    db: AsyncSession,
    title: str,
    format_type: str,
    content: str,
) -> tuple[Document, bool]:
    """
    Get an existing document if identical content already exists,
    or create a new document with a unique doc_id derived from its content hash.
    Also creates the initial Version 1 record.

    Returns:
        tuple[Document, bool]: (document, is_duplicate)
    """
    clean_title = (title or "").strip() or "Untitled"
    clean_format = normalize_format(format_type)
    clean_content = normalize_content(content)

    content_hash = compute_content_hash(clean_title, clean_format, clean_content)

    # Check if a document with identical content hash already exists
    stmt = (
        select(Document)
        .options(selectinload(Document.versions))
        .where(Document.content_hash == content_hash)
    )
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
        await db.flush()

        # Create initial Version 1
        v1 = DocumentVersion(
            document_id=new_doc.id,
            version=1,
            title=clean_title,
            content=clean_content,
            format=clean_format,
            content_hash=content_hash,
        )
        db.add(v1)

        await db.commit()
        await db.refresh(new_doc)
        return new_doc, False
    except IntegrityError:
        # Concurrent insert of identical content or collision
        await db.rollback()
        retry_stmt = (
            select(Document)
            .options(selectinload(Document.versions))
            .where(Document.content_hash == content_hash)
        )
        retry_res = await db.execute(retry_stmt)
        duplicate_doc = retry_res.scalars().first()
        if duplicate_doc is not None:
            return duplicate_doc, True
        raise


async def update_document(
    db: AsyncSession,
    doc_id: str,
    title: str,
    format_type: str,
    content: str,
) -> tuple[Document | None, DocumentVersion | None, bool]:
    """
    Update an existing document and record a new version in its history.
    If the content/title/format hasn't changed, returns (doc, latest_version, False).

    Returns:
        tuple[Document | None, DocumentVersion | None, bool]: (doc, version, has_changed)
    """
    doc = await get_document_by_doc_id(db, doc_id=doc_id)
    if doc is None:
        return None, None, False

    clean_title = (title or "").strip() or "Untitled"
    clean_format = normalize_format(format_type)
    clean_content = normalize_content(content)
    new_hash = compute_content_hash(clean_title, clean_format, clean_content)

    # Check if identical to current version
    if (
        doc.title == clean_title
        and doc.format == clean_format
        and doc.content == clean_content
    ):
        latest_v = doc.versions[-1] if doc.versions else None
        return doc, latest_v, False

    # Determine next version number
    current_max_v = 0
    if doc.versions:
        current_max_v = max(v.version for v in doc.versions)
    else:
        # If no version 1 existed, create v1 for previous state
        v1 = DocumentVersion(
            document_id=doc.id,
            version=1,
            title=doc.title,
            content=doc.content,
            format=doc.format,
            content_hash=doc.content_hash,
            created_at=doc.created_at,
        )
        db.add(v1)
        current_max_v = 1

    next_version_num = current_max_v + 1

    # Update document state
    doc.title = clean_title
    doc.format = clean_format
    doc.content = clean_content
    doc.content_hash = new_hash
    doc.updated_at = datetime.now(timezone.utc)

    # Create new version record
    new_version = DocumentVersion(
        document_id=doc.id,
        version=next_version_num,
        title=clean_title,
        content=clean_content,
        format=clean_format,
        content_hash=new_hash,
    )
    db.add(new_version)

    await db.commit()
    await db.refresh(doc)
    await db.refresh(new_version)

    return doc, new_version, True


async def get_document_by_doc_id(
    db: AsyncSession,
    doc_id: str,
    increment_views: bool = False,
) -> Document | None:
    """Fetch a document by its public doc_id, optionally incrementing view count."""
    stmt = (
        select(Document)
        .options(selectinload(Document.versions))
        .where(Document.doc_id == doc_id)
    )
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


async def get_document_versions(
    db: AsyncSession,
    doc_id: str,
) -> list[DocumentVersion]:
    """Fetch all historical versions of a document ordered by version descending."""
    doc = await get_document_by_doc_id(db, doc_id=doc_id)
    if doc is None:
        return []

    stmt = (
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc.id)
        .order_by(DocumentVersion.version.desc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def get_document_version(
    db: AsyncSession,
    doc_id: str,
    version: int,
) -> tuple[Document | None, DocumentVersion | None]:
    """Fetch a specific version of a document."""
    doc = await get_document_by_doc_id(db, doc_id=doc_id)
    if doc is None:
        return None, None

    stmt = select(DocumentVersion).where(
        DocumentVersion.document_id == doc.id,
        DocumentVersion.version == version,
    )
    res = await db.execute(stmt)
    ver = res.scalars().first()
    return doc, ver


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
        .options(selectinload(Document.versions))
        .order_by(Document.updated_at.desc(), Document.id.desc())
        .offset(offset)
        .limit(per_page)
    )
    res = await db.execute(stmt)
    documents = list(res.scalars().all())

    return documents, total, total_pages
