import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_drawer_not_open_on_first_load(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200

    # Verify drawer markup exists
    assert 'id="docs-drawer"' in response.text
    assert 'id="drawer-backdrop"' in response.text

    # Verify drawer is collapsed / not open by default
    assert 'class="drawer open"' not in response.text
    assert 'class="drawer-backdrop open"' not in response.text

    # Verify files list table is NOT displayed in main page flow
    assert '<table class="docs-table">' not in response.text


@pytest.mark.asyncio
async def test_obvious_drawer_triggers_present(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200

    # 1. Obvious trigger in top navbar
    assert 'id="nav-drawer-toggle"' in response.text
    assert "Browse Documents" in response.text

    # 2. Obvious docked tab on left edge of viewport
    assert 'id="docked-drawer-tab"' in response.text
    assert "docked-tab-text" in response.text

    # 3. Obvious in-page banner above editor
    assert "drawer-trigger-card" in response.text
    assert "Browse Saved Documents" in response.text
    assert "Open Drawer" in response.text


@pytest.mark.asyncio
async def test_drawer_open_with_query_param(client: AsyncClient):
    # When navigated to with drawer=1 (e.g. from pagination or direct link)
    response = await client.get("/?drawer=1")
    assert response.status_code == 200

    # Drawer and backdrop should have 'open' class
    assert 'id="docs-drawer" class="drawer open"' in response.text or 'class="drawer open"' in response.text
    assert 'class="drawer-backdrop open"' in response.text


@pytest.mark.asyncio
async def test_drawer_contains_documents_and_search(client: AsyncClient):
    # Create two documents
    await client.post(
        "/docs",
        data={"title": "Drawer Note 1", "format": "markdown", "content": "Content of note 1"},
    )
    await client.post(
        "/docs",
        data={"title": "Drawer Note 2", "format": "python", "content": "print('hello')"},
    )

    response = await client.get("/?drawer=1")
    assert response.status_code == 200

    # Verify search input is present
    assert 'id="drawer-search-input"' in response.text

    # Verify document cards inside drawer
    assert "drawer-doc-card" in response.text
    assert "Drawer Note 1" in response.text
    assert "Drawer Note 2" in response.text

    # Verify close button
    assert "drawer-close-btn" in response.text
    assert "Close Drawer" in response.text


@pytest.mark.asyncio
async def test_drawer_pagination(client: AsyncClient):
    # Create 12 documents
    for i in range(12):
        await client.post(
            "/docs",
            data={"title": f"Doc {i}", "format": "markdown", "content": f"Content {i}"},
        )

    # Page 1
    res_p1 = await client.get("/?page=1&per_page=5&drawer=1")
    assert res_p1.status_code == 200
    assert "Showing page <strong>1</strong> of <strong>3</strong>" in res_p1.text
    assert "Next ›" in res_p1.text
    assert "drawer=1" in res_p1.text

    # Page 2
    res_p2 = await client.get("/?page=2&per_page=5&drawer=1")
    assert res_p2.status_code == 200
    assert "Showing page <strong>2</strong> of <strong>3</strong>" in res_p2.text
    assert "‹ Previous" in res_p2.text
