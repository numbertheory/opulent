import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from opulent.formatter import render_document_html
from opulent.services.document_service import get_or_create_document


@pytest.mark.asyncio
async def test_unicode_and_emojis(client: AsyncClient):
    content = "✨ 🚀 Opulent supports 日本語, 한국어, 中文, and emojis! 🌟\n\n```python\nprint('🎉')\n```"
    post_res = await client.post(
        "/api/docs",
        json={"title": "Unicode Showcase 🎨", "format": "markdown", "content": content},
    )
    assert post_res.status_code == 201
    doc_id = post_res.json()["id"]

    # Verify retrieval
    get_res = await client.get(f"/api/docs/{doc_id}")
    assert get_res.status_code == 200
    assert "✨ 🚀" in get_res.json()["content"]
    assert "日本語" in get_res.json()["content"]

    # Verify web view
    view_res = await client.get(f"/docs/{doc_id}")
    assert view_res.status_code == 200
    assert "Unicode Showcase 🎨" in view_res.text
    assert "日本語" in view_res.text


@pytest.mark.asyncio
async def test_markdown_tables_and_formatting():
    table_md = """
| Feature | Status |
| :--- | :--- |
| Deduplication | Supported |
| REST API | Supported |
| Formatting | Rich & Code |
"""
    html = render_document_html(table_md, "markdown")
    assert "<table" in html
    assert "Deduplication" in html
    assert "Supported" in html


@pytest.mark.asyncio
async def test_multiple_programming_languages():
    langs = ["javascript", "json", "html", "bash", "sql", "rust", "go"]
    snippets = {
        "javascript": "const answer = 42;\nconsole.log(answer);",
        "json": '{\n  "version": "1.0"\n}',
        "html": '<div class="test"><p>Hello</p></div>',
        "bash": '#!/usr/bin/env bash\necho "Hello World"',
        "sql": "SELECT id, title FROM documents WHERE format = 'sql';",
        "rust": 'fn main() {\n    println!("Hello, Opulent!");\n}',
        "go": 'package main\nimport "fmt"\nfunc main() { fmt.Println("Go") }',
    }

    for lang in langs:
        rendered = render_document_html(snippets[lang], lang)
        assert '<table class="highlighttable">' in rendered
        assert 'class="linenos"' in rendered


@pytest.mark.asyncio
async def test_raw_content_disposition_header(client: AsyncClient):
    create_res = await client.post(
        "/api/docs",
        json={"title": "Header Test", "format": "python", "content": "x = 10"},
    )
    doc_id = create_res.json()["id"]

    res = await client.get(f"/api/docs/{doc_id}/raw")
    assert res.status_code == 200
    assert f'filename="{doc_id}.txt"' in res.headers.get("content-disposition", "")

    web_res = await client.get(f"/docs/{doc_id}/raw")
    assert web_res.status_code == 200
    assert f'filename="{doc_id}.txt"' in web_res.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_duplicate_does_not_increment_count(db_session: AsyncSession):
    doc1, is_dup1 = await get_or_create_document(
        db_session, "Repeated", "plain", "Repeated content text"
    )
    assert not is_dup1

    # Insert 5 times
    for _ in range(5):
        doc_n, is_dupn = await get_or_create_document(
            db_session, "Repeated", "plain", "Repeated content text"
        )
        assert is_dupn
        assert doc_n.doc_id == doc1.doc_id
