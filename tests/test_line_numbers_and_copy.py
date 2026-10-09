import re
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_code_document_line_numbers_and_copy_button(client: AsyncClient):
    """
    Test line numbers toggle checkbox and compact icon copy button for code files.
    - Checkbox in top left corner of content frame
    - Copy button in top right corner of content frame without the word 'Copy'
    - Redundant 'Copy Text' button removed
    - Code highlight table has line numbers
    """
    create_res = await client.post(
        "/docs",
        data={
            "title": "Python Script",
            "format": "python",
            "content": "def hello():\n    return 'world'\n",
        },
        follow_redirects=False,
    )
    assert create_res.status_code == 303
    doc_id = create_res.headers["location"].split("/docs/")[1]

    view_res = await client.get(f"/docs/{doc_id}")
    assert view_res.status_code == 200
    html = view_res.text

    # Frame and toolbar structure
    assert 'class="doc-content-frame show-line-numbers"' in html or 'id="doc-content-frame"' in html
    assert 'class="doc-frame-toolbar"' in html
    assert 'class="doc-frame-toolbar-left"' in html
    assert 'class="doc-frame-toolbar-right"' in html

    # Checkbox in top-left
    assert 'id="line-numbers-checkbox"' in html
    assert 'type="checkbox"' in html
    assert 'onchange="toggleLineNumbers(this.checked)"' in html

    # Copy button in top-right
    assert 'id="frame-copy-btn"' in html
    assert 'onclick="copyFrameDocumentContent()"' in html

    # Ensure the frame-copy-btn does NOT contain the text "Copy" inside its inner HTML
    btn_match = re.search(r'<button[^>]*id="frame-copy-btn"[^>]*>(.*?)</button>', html, re.DOTALL)
    assert btn_match is not None
    btn_inner = btn_match.group(1).strip()
    # It must contain an icon (SVG) and NOT the text 'Copy'
    assert "<svg" in btn_inner
    assert "Copy" not in btn_inner

    # Redundant "Copy Text" button must be removed from document view
    assert "Copy Text" not in html

    # "Copy URL" should remain
    assert "Copy URL" in html

    # Raw document content textarea exists for clipboard copying
    assert 'id="raw-doc-content"' in html
    assert "def hello():" in html


@pytest.mark.asyncio
async def test_markdown_document_line_numbers_and_copy_button(client: AsyncClient):
    """
    Test line numbers toggle checkbox and compact copy button for markdown files.
    """
    create_res = await client.post(
        "/docs",
        data={
            "title": "Markdown Notes",
            "format": "markdown",
            "content": "# Heading\n\nParagraph text.\n\n- Item 1\n- Item 2",
        },
        follow_redirects=False,
    )
    assert create_res.status_code == 303
    doc_id = create_res.headers["location"].split("/docs/")[1]

    view_res = await client.get(f"/docs/{doc_id}")
    assert view_res.status_code == 200
    html = view_res.text

    # Checkbox and copy button present
    assert 'id="line-numbers-checkbox"' in html
    assert 'id="frame-copy-btn"' in html
    assert "Copy Text" not in html

    # Verify frame copy button does not contain the word 'Copy'
    btn_match = re.search(r'<button[^>]*id="frame-copy-btn"[^>]*>(.*?)</button>', html, re.DOTALL)
    assert btn_match is not None
    assert "Copy" not in btn_match.group(1)

    # Markdown rendered content present
    assert 'class="markdown-body"' in html
    assert "Heading" in html
    assert "Paragraph text." in html


@pytest.mark.asyncio
async def test_historical_version_view(client: AsyncClient):
    """
    Test that historical document versions also have the frame toolbar and no redundant copy button.
    """
    create_res = await client.post(
        "/docs",
        data={"title": "Versioned Doc", "format": "python", "content": "v = 1"},
        follow_redirects=False,
    )
    doc_id = create_res.headers["location"].split("/docs/")[1]

    # Create v2
    await client.post(
        f"/docs/{doc_id}/edit",
        data={"title": "Versioned Doc v2", "format": "python", "content": "v = 2"},
        follow_redirects=False,
    )

    # View historical revision v1
    v1_res = await client.get(f"/docs/{doc_id}/history/1")
    assert v1_res.status_code == 200
    html = v1_res.text

    assert 'id="line-numbers-checkbox"' in html
    assert 'id="frame-copy-btn"' in html
    assert "Copy Text" not in html


@pytest.mark.asyncio
async def test_css_line_numbers_and_toolbar_rules(client: AsyncClient):
    """
    Test that stylesheet contains toggleable line number rules and frame toolbar styling.
    """
    css_res = await client.get("/static/css/style.css")
    assert css_res.status_code == 200
    css = css_res.text

    # Toolbar and button rules
    assert ".doc-content-frame" in css
    assert ".doc-frame-toolbar" in css
    assert ".line-numbers-toggle" in css
    assert ".frame-copy-btn" in css

    # Toggling linenos for code
    assert ".highlighttable td.linenos" in css
    assert "display: none !important" in css

    # Markdown line numbering rules
    assert "counter-reset: md-line" in css
    assert "counter-increment: md-line" in css
    assert "show-line-numbers" in css


@pytest.mark.asyncio
async def test_js_line_numbers_and_copy_functions(client: AsyncClient):
    """
    Test that JavaScript bundle includes functions for copying frame content and toggling line numbers.
    """
    js_res = await client.get("/static/js/app.js")
    assert js_res.status_code == 200
    js = js_res.text

    assert "copyFrameDocumentContent" in js
    assert "toggleLineNumbers" in js
    assert "initLineNumbers" in js
    assert "opulent_show_line_numbers" in js
