import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_drawer_not_open_on_first_load(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200

    # Verify drawer markup exists in base layout
    assert 'id="docs-drawer"' in response.text
    assert 'id="drawer-backdrop"' in response.text

    # Verify drawer is collapsed / not open by default
    assert 'class="drawer open"' not in response.text
    assert 'class="drawer-backdrop open"' not in response.text

    # Verify files list table is NOT displayed in main page flow on /
    assert '<table class="docs-table">' not in response.text


@pytest.mark.asyncio
async def test_banner_and_drawer_triggers(client: AsyncClient):
    # Create two documents so total > 0
    await client.post(
        "/docs",
        data={"title": "Doc A", "format": "markdown", "content": "Content A"},
    )
    await client.post(
        "/docs",
        data={"title": "Doc B", "format": "markdown", "content": "Content B"},
    )

    response = await client.get("/")
    assert response.status_code == 200

    # 1. "+ New Document" removed from banner
    assert "＋ New Document" not in response.text

    # 2. "Browse Documents" button removed from banner
    assert 'id="nav-drawer-toggle"' not in response.text
    assert "Browse Documents" not in response.text

    # 3. Dedicated button linking to standalone file list view is in the banner
    assert 'href="/documents"' in response.text
    assert 'id="nav-documents-btn"' in response.text

    # 4. Theme switch button is in the banner
    assert 'id="theme-toggle-btn"' in response.text
    assert 'onclick="toggleTheme()"' in response.text

    # 5. Side button on the left edge is kept on the main page
    assert 'id="docked-drawer-tab"' in response.text
    assert "docked-tab-text" in response.text

    # 6. Removed extraneous triggers
    assert "drawer-trigger-card" not in response.text
    assert "Documents Drawer (" not in response.text

    # 7. Count is ONLY shown at the top of the open drawer, not on the side tab trigger
    docked_tab_html = response.text.split('id="docked-drawer-tab"')[1].split("</button>")[0]
    assert "docked-tab-badge" not in docked_tab_html
    assert "badge" not in docked_tab_html

    # The document count IS present at the top of the drawer
    assert 'id="drawer-total-count"' in response.text


@pytest.mark.asyncio
async def test_drawer_works_when_viewing_document(client: AsyncClient):
    post_res = await client.post(
        "/docs",
        data={"title": "Sample Doc", "format": "markdown", "content": "Full document content here"},
        follow_redirects=False,
    )
    doc_id = post_res.headers["location"].split("/docs/")[1]

    # When viewing a document
    view_res = await client.get(f"/docs/{doc_id}")
    assert view_res.status_code == 200

    # 1. The drawer markup exists on the document view page
    assert 'id="docs-drawer"' in view_res.text
    assert 'id="drawer-backdrop"' in view_res.text

    # 2. Banner has documents link and theme switcher, no "Browse Documents" or "+ New Document"
    assert "nav-drawer-toggle" not in view_res.text
    assert "＋ New Document" not in view_res.text
    assert 'href="/documents"' in view_res.text
    assert 'id="theme-toggle-btn"' in view_res.text

    # 3. The side button exists on the view page
    assert 'id="docked-drawer-tab"' in view_res.text

    # 4. The drawer contains the list of documents so it slides out populated
    assert "drawer-doc-card" in view_res.text
    assert "Sample Doc" in view_res.text

    # 5. The side tab trigger does not have count badge, but drawer header has the count
    assert 'id="drawer-total-count"' in view_res.text


@pytest.mark.asyncio
async def test_standalone_documents_view_without_left_flyout_button(client: AsyncClient):
    # Create test notes
    await client.post(
        "/docs",
        data={"title": "Note Alpha", "format": "markdown", "content": "Alpha content snippet"},
    )
    await client.post(
        "/docs",
        data={"title": "Note Beta", "format": "python", "content": "def beta(): pass"},
    )

    response = await client.get("/documents")
    assert response.status_code == 200

    # 1. Full table is present with columns and documents
    assert '<table class="docs-table"' in response.text
    assert "Note Alpha" in response.text
    assert "Note Beta" in response.text
    assert "Alpha content snippet" in response.text

    # 2. Standalone view MUST NOT have the flyout button on the left hand side
    assert 'id="docked-drawer-tab"' not in response.text
    assert "docked-tab-text" not in response.text

    # 3. Banner elements are intact
    assert 'href="/documents"' in response.text
    assert 'id="theme-toggle-btn"' in response.text
    assert "＋ New Document" not in response.text
    assert "nav-drawer-toggle" not in response.text

    # 4. Filter search input and count badge are present on the standalone view
    assert 'id="table-search-input"' in response.text
    assert 'id="table-total-count"' in response.text


@pytest.mark.asyncio
async def test_drawer_open_with_query_param(client: AsyncClient):
    response = await client.get("/?drawer=1")
    assert response.status_code == 200

    # Drawer and backdrop should have 'open' class
    assert 'class="drawer open"' in response.text
    assert 'class="drawer-backdrop open"' in response.text


@pytest.mark.asyncio
async def test_drawer_contains_search_and_pagination(client: AsyncClient):
    for i in range(12):
        await client.post(
            "/docs",
            data={"title": f"Test Note {i}", "format": "markdown", "content": f"Content {i}"},
        )

    response = await client.get("/?drawer=1")
    assert response.status_code == 200

    # Search bar & close button
    assert 'id="drawer-search-input"' in response.text
    assert "drawer-close-btn" in response.text
    assert "Close Drawer" in response.text

    # Pagination inside drawer
    assert "Showing page <strong>1</strong>" in response.text
    assert "Next ›" in response.text
