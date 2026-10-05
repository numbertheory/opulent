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

    # 3. Format is displayed as an SVG icon to the left of the title, NOT as a separate column or word tag
    assert "format-icon-markdown" in response.text
    assert "format-icon-python" in response.text
    assert "<th>Format</th>" not in response.text

    # 4. Document ID and Lines columns are removed
    assert "<th>Document ID</th>" not in response.text
    assert "<th>Lines</th>" not in response.text

    # 5. Actions column is removed
    assert "<th>Actions</th>" not in response.text

    # 6. Created column is replaced by "Updated" column showing local time tag
    assert "<th>Updated</th>" in response.text
    assert "<th>Created</th>" not in response.text
    assert 'class="local-time"' in response.text

    # 7. Versions column shows plain clickable number (not a whole button) linking to history
    assert "<th>Versions</th>" in response.text
    assert 'class="version-count-link"' in response.text
    assert "/history" in response.text

    # 8. Banner elements are intact
    assert 'href="/documents"' in response.text
    assert 'id="theme-toggle-btn"' in response.text
    assert "＋ New Document" not in response.text
    assert "nav-drawer-toggle" not in response.text

    # 9. Filter search input and count badge are present on the standalone view
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


@pytest.mark.asyncio
async def test_drawer_compact_icons_no_id_no_lines_and_sorted_by_newest(client: AsyncClient):
    """
    Verify:
    1. Document flyover window uses format SVG icons instead of word tags.
    2. Document ID and lines indicator are removed from drawer entries.
    3. The updated time is displayed on each drawer entry.
    4. Drawer items are sorted by newest (most recently updated/created) by default.
    """
    # 1. Create three documents in sequence
    res1 = await client.post(
        "/docs",
        data={"title": "First Doc", "format": "python", "content": "x = 1"},
        follow_redirects=False,
    )
    doc1_id = res1.headers["location"].split("/docs/")[1]

    res2 = await client.post(
        "/docs",
        data={"title": "Second Doc", "format": "rust", "content": "fn main() {}"},
        follow_redirects=False,
    )
    doc2_id = res2.headers["location"].split("/docs/")[1]

    res3 = await client.post(
        "/docs",
        data={"title": "Third Doc", "format": "go", "content": "package main"},
        follow_redirects=False,
    )
    doc3_id = res3.headers["location"].split("/docs/")[1]

    # Verify initial newest-first order: Third Doc, Second Doc, First Doc
    home_res = await client.get("/?drawer=1")
    assert home_res.status_code == 200

    drawer_cards = home_res.text.split('class="drawer-doc-card"')
    assert len(drawer_cards) >= 4  # at least 3 cards + preamble

    # First card in drawer should be Third Doc
    assert "Third Doc" in drawer_cards[1]
    assert "Second Doc" in drawer_cards[2]
    assert "First Doc" in drawer_cards[3]

    # 2. Edit First Doc to make it the most recently updated
    await client.post(
        f"/docs/{doc1_id}/edit",
        data={"title": "First Doc (Updated)", "format": "python", "content": "x = 2; y = 3"},
    )

    # Re-fetch page: First Doc (Updated) must now be at the very top!
    updated_home_res = await client.get("/?drawer=1")
    assert updated_home_res.status_code == 200

    updated_cards = updated_home_res.text.split('class="drawer-doc-card"')
    assert "First Doc (Updated)" in updated_cards[1]
    assert "Third Doc" in updated_cards[2]
    assert "Second Doc" in updated_cards[3]

    # Inspect the top card content
    top_card_html = updated_cards[1].split('</div>\n            </div>')[0]

    # Verify format icon is present instead of word tag badge
    assert 'class="format-icon format-icon-python"' in top_card_html
    assert '<span class="badge">Python</span>' not in top_card_html
    assert '<span class="badge">Shell / Bash</span>' not in updated_home_res.text.split('class="drawer-content"')[1].split('class="drawer-footer"')[0]

    # Verify document ID and line count are NOT in the drawer card
    assert 'class="doc-id-code"' not in top_card_html
    assert doc1_id not in top_card_html.split('class="drawer-doc-meta"')[1]
    assert "lines" not in top_card_html.split('class="drawer-doc-meta"')[1]

    # Verify updated time is displayed
    assert 'class="local-time"' in top_card_html

    # Also verify /api/docs reflects the same newest-first ordering and includes format_icon_svg
    api_res = await client.get("/api/docs?page=1&per_page=15")
    assert api_res.status_code == 200
    api_data = api_res.json()
    assert api_data["items"][0]["title"] == "First Doc (Updated)"
    assert api_data["items"][0]["format_icon_svg"] != ""
    assert "format-icon-python" in api_data["items"][0]["format_icon_svg"]

