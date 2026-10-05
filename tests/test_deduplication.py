import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from opulent.models import Document
from opulent.services.document_service import get_or_create_document


@pytest.mark.asyncio
async def test_deduplication_returns_same_doc_id(db_session: AsyncSession):
    title = "My Document"
    content = "This is unique text that will be submitted twice."
    fmt = "markdown"

    doc1, is_dup1 = await get_or_create_document(db_session, title, fmt, content)
    assert not is_dup1
    assert doc1.doc_id is not None

    # Submit exact same document
    doc2, is_dup2 = await get_or_create_document(db_session, title, fmt, content)
    assert is_dup2
    assert doc2.id == doc1.id
    assert doc2.doc_id == doc1.doc_id

    # Verify database has only 1 record
    count_res = await db_session.execute(select(func.count(Document.id)))
    assert count_res.scalar_one() == 1


@pytest.mark.asyncio
async def test_deduplication_normalizes_whitespace(db_session: AsyncSession):
    title = "Sample"
    content_initial = "Hello World\nLine 2"
    content_with_cr = "  Hello World\r\nLine 2\r\n\n  "

    doc1, is_dup1 = await get_or_create_document(
        db_session, title, "markdown", content_initial
    )
    assert not is_dup1

    doc2, is_dup2 = await get_or_create_document(
        db_session, title, "markdown", content_with_cr
    )
    assert is_dup2
    assert doc2.doc_id == doc1.doc_id

    count_res = await db_session.execute(select(func.count(Document.id)))
    assert count_res.scalar_one() == 1


@pytest.mark.asyncio
async def test_distinct_content_creates_new_document(db_session: AsyncSession):
    doc1, is_dup1 = await get_or_create_document(
        db_session, "Doc 1", "markdown", "Content Alpha"
    )
    doc2, is_dup2 = await get_or_create_document(
        db_session, "Doc 2", "markdown", "Content Beta"
    )

    assert not is_dup1
    assert not is_dup2
    assert doc1.doc_id != doc2.doc_id

    count_res = await db_session.execute(select(func.count(Document.id)))
    assert count_res.scalar_one() == 2
