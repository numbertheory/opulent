import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_viewport_meta_tag_present_on_all_views(client: AsyncClient):
    """Verify that viewport meta tag is properly configured for mobile portrait browsers."""
    # Test index page
    res_index = await client.get("/")
    assert res_index.status_code == 200
    assert '<meta name="viewport" content="width=device-width, initial-scale=1.0">' in res_index.text

    # Test standalone documents list
    res_docs = await client.get("/documents")
    assert res_docs.status_code == 200
    assert '<meta name="viewport" content="width=device-width, initial-scale=1.0">' in res_docs.text

    # Create a document
    create_res = await client.post(
        "/docs",
        data={"title": "Mobile Test", "format": "markdown", "content": "# Responsive Heading\nParagraph."},
        follow_redirects=False,
    )
    doc_id = create_res.headers["location"].split("/docs/")[1]

    # Test document view
    res_view = await client.get(f"/docs/{doc_id}")
    assert res_view.status_code == 200
    assert '<meta name="viewport" content="width=device-width, initial-scale=1.0">' in res_view.text

    # Test history view
    res_hist = await client.get(f"/docs/{doc_id}/history")
    assert res_hist.status_code == 200
    assert '<meta name="viewport" content="width=device-width, initial-scale=1.0">' in res_hist.text

    # Create a second version and test compare view
    await client.post(
        f"/docs/{doc_id}/edit",
        data={"title": "Mobile Test v2", "format": "markdown", "content": "# Responsive Heading\nParagraph edited."},
        follow_redirects=False,
    )
    res_comp = await client.get(f"/docs/{doc_id}/compare?v1=1&v2=2")
    assert res_comp.status_code == 200
    assert '<meta name="viewport" content="width=device-width, initial-scale=1.0">' in res_comp.text


@pytest.mark.asyncio
async def test_mobile_media_queries_in_stylesheet(client: AsyncClient):
    """Verify that stylesheet contains mobile rules: hiding footer and flyover, keeping docs button."""
    css_res = await client.get("/static/css/style.css")
    assert css_res.status_code == 200
    css = css_res.text

    # Check for media queries
    assert "@media (max-width: 768px)" in css
    assert "@media (max-width: 480px)" in css

    # Mobile view removes footer
    assert ".site-footer" in css
    assert "display: none !important" in css

    # Mobile view removes documents flyover and docked trigger
    assert ".docked-drawer-tab" in css
    assert ".drawer" in css

    # Mobile view keeps documents button at the top
    assert ".nav-docs-btn" in css

    # iOS zoom prevention: 16px font-size on inputs/selects/textareas
    assert "font-size: 16px;" in css

    # Touch momentum scrolling
    assert "-webkit-overflow-scrolling: touch;" in css

    # Responsive form column layout
    assert "flex-direction: column" in css

    # Responsive touch button minimum height
    assert "min-height: 44px" in css or "min-height: 38px" in css

    # Mobile action grid for document view
    assert ".doc-actions" in css


@pytest.mark.asyncio
async def test_banner_removed_in_both_views(client: AsyncClient):
    """Verify that Create Document / Public Pastebin banner is removed from index page."""
    res = await client.get("/")
    assert res.status_code == 200
    # Banner text should not be in the page
    assert "Public Pastebin" not in res.text
    # The form itself is still there
    assert 'id="editor-form"' in res.text
    assert 'name="title"' in res.text
    assert 'name="content"' in res.text
    assert "Publish Document" in res.text


@pytest.mark.asyncio
async def test_footer_removed_in_desktop_version(client: AsyncClient):
    """Verify that the site footer is completely removed from the desktop version."""
    res = await client.get("/")
    assert res.status_code == 200
    assert "<footer" not in res.text
    assert "site-footer" not in res.text


@pytest.mark.asyncio
async def test_new_document_input_fills_viewport_length(client: AsyncClient):
    """Verify that the new document editor input is styled to fill the viewport length."""
    res = await client.get("/")
    assert res.status_code == 200
    assert "editor-card" in res.text
    assert "editor-content-group" in res.text

    css_res = await client.get("/static/css/style.css")
    assert css_res.status_code == 200
    assert ".editor-content-group .form-textarea" in css_res.text
    assert "calc(100vh - 340px)" in css_res.text


@pytest.mark.asyncio
async def test_mobile_drawer_touch_swipe_script(client: AsyncClient):
    """Verify that app.js includes mobile touch handling for drawer gestures."""
    js_res = await client.get("/static/js/app.js")
    assert js_res.status_code == 200
    js = js_res.text

    assert "touchstart" in js
    assert "touchend" in js
    assert "changedTouches" in js
    assert "closeDrawer()" in js


@pytest.mark.asyncio
async def test_all_features_available_and_functional_on_mobile(client: AsyncClient):
    """
    Ensure all features remain fully available and functional:
    - Creation form
    - Standalone documents table with deletion
    - History with version comparison and deletion
    - Document viewing
    """
    # 1. Create document
    create_res = await client.post(
        "/docs",
        data={"title": "Feature Test", "format": "markdown", "content": "Initial content"},
        follow_redirects=False,
    )
    assert create_res.status_code == 303
    doc_id = create_res.headers["location"].split("/docs/")[1]

    # 2. View document: verify all action buttons are present
    view_res = await client.get(f"/docs/{doc_id}")
    assert view_res.status_code == 200
    html = view_res.text
    assert "✏️ Edit" in html
    assert "Copy Text" not in html
    assert "frame-copy-btn" in html
    assert "line-numbers-checkbox" in html
    assert "Copy URL" in html
    assert "Raw" in html

    # 3. Edit document to create v2
    edit_res = await client.post(
        f"/docs/{doc_id}/edit",
        data={"title": "Feature Test v2", "format": "markdown", "content": "Updated content"},
        follow_redirects=False,
    )
    assert edit_res.status_code == 303

    # 4. View history: verify comparison form and deletion UI are present
    hist_res = await client.get(f"/docs/{doc_id}/history")
    assert hist_res.status_code == 200
    hist_html = hist_res.text
    assert 'action="/docs/' in hist_html and '/compare"' in hist_html
    assert 'id="delete-selected-revisions-btn"' in hist_html
    assert 'class="form-checkbox revision-select-checkbox"' in hist_html

    # 5. Standalone documents table: verify search filter and deletion UI are present
    docs_res = await client.get("/documents")
    assert docs_res.status_code == 200
    docs_html = docs_res.text
    assert 'id="table-search-input"' in docs_html
    assert 'id="delete-selected-docs-btn"' in docs_html
    assert 'class="form-checkbox doc-select-checkbox"' in docs_html
