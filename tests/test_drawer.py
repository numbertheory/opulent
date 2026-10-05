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

    # Verify files list table is NOT displayed in main page flow
    assert '<table class="docs-table">' not in response.text


@pytest.mark.asyncio
async def test_only_allowed_triggers_present_without_count_badges(client: AsyncClient):
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

    # 1. Persistent "Browse" documents button in the top banner is kept
    assert 'id="nav-drawer-toggle"' in response.text
    assert "Browse Documents" in response.text

    # 2. Side button on the left edge is kept
    assert 'id="docked-drawer-tab"' in response.text
    assert "docked-tab-text" in response.text

    # 3. Removed triggers:
    # Banner above the "Create Document" frame must be removed
    assert "drawer-trigger-card" not in response.text
    # No extra drawer buttons in the editor card header or footer
    assert "Documents Drawer (" not in response.text
    assert "Browse Drawer" not in response.text

    # 4. Count is ONLY shown at the top of the open drawer, not on triggers
    # Verify the triggers do NOT show the count badge
    nav_btn_html = response.text.split('id="nav-drawer-toggle"')[1].split("</button>")[0]
    assert "badge" not in nav_btn_html

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

    # 2. The persistent top banner "Browse Documents" button exists and opens the drawer
    assert 'id="nav-drawer-toggle"' in view_res.text
    assert 'onclick="openDrawer()"' in view_res.text

    # 3. The side button also exists on the view page
    assert 'id="docked-drawer-tab"' in view_res.text

    # 4. The drawer contains the list of documents so it slides out populated
    assert "drawer-doc-card" in view_res.text
    assert "Sample Doc" in view_res.text

    # 5. The triggers do not have count badges, but drawer header has the count
    assert 'id="drawer-total-count"' in view_res.text


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
