import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_index_page(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    assert "OPULENT" in response.text
    assert "Create Document" in response.text
    assert "No documents created yet" in response.text


@pytest.mark.asyncio
async def test_create_and_view_document_web(client: AsyncClient):
    form_data = {
        "title": "Welcome Guide",
        "format": "markdown",
        "content": "# Hello Opulent\nThis is a **bold** introduction.",
    }
    response = await client.post("/docs", data=form_data, follow_redirects=False)
    assert response.status_code == 303
    redirect_location = response.headers["location"]
    assert redirect_location.startswith("/docs/")
    doc_id = redirect_location.split("/docs/")[1]

    # View the created document
    view_response = await client.get(redirect_location)
    assert view_response.status_code == 200
    assert "Welcome Guide" in view_response.text
    assert "<h1" in view_response.text
    assert "Hello Opulent" in view_response.text
    assert doc_id in view_response.text


@pytest.mark.asyncio
async def test_create_duplicate_document_web(client: AsyncClient):
    form_data = {
        "title": "Config Note",
        "format": "plain",
        "content": "port = 8000\nhost = localhost",
    }
    res1 = await client.post("/docs", data=form_data, follow_redirects=False)
    assert res1.status_code == 303
    first_url = res1.headers["location"]

    # Submit again with same content
    res2 = await client.post("/docs", data=form_data, follow_redirects=False)
    assert res2.status_code == 303
    second_url = res2.headers["location"]

    # Should redirect to the same doc-id with duplicate=1 flag
    assert second_url.startswith(first_url)
    assert "duplicate=1" in second_url

    # Inspect the view response
    view_response = await client.get(second_url)
    assert "Duplicate Document Recognized" in view_response.text


@pytest.mark.asyncio
async def test_create_empty_document_error(client: AsyncClient):
    response = await client.post(
        "/docs",
        data={"title": "Empty", "format": "markdown", "content": "   "},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "error=" in response.headers["location"]


@pytest.mark.asyncio
async def test_view_nonexistent_document_404(client: AsyncClient):
    response = await client.get("/docs/nonexistent999")
    assert response.status_code == 404
    assert "Document Not Found" in response.text


@pytest.mark.asyncio
async def test_raw_document_endpoint(client: AsyncClient):
    content = "print('Hello from raw endpoint!')"
    post_res = await client.post(
        "/docs",
        data={"title": "Script", "format": "python", "content": content},
        follow_redirects=False,
    )
    doc_id = post_res.headers["location"].split("/docs/")[1]

    raw_res = await client.get(f"/docs/{doc_id}/raw")
    assert raw_res.status_code == 200
    assert raw_res.headers["content-type"].startswith("text/plain")
    assert raw_res.text == content


@pytest.mark.asyncio
async def test_pygments_css_endpoint(client: AsyncClient):
    response = await client.get("/pygments.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    assert ".highlight" in response.text


@pytest.mark.asyncio
async def test_pagination_web(client: AsyncClient):
    # Create 15 distinct documents
    for i in range(15):
        await client.post(
            "/docs",
            data={
                "title": f"Doc {i}",
                "format": "markdown",
                "content": f"Content index {i}",
            },
        )

    # Page 1 with per_page=10
    res_p1 = await client.get("/?page=1&per_page=10")
    assert res_p1.status_code == 200
    assert "Showing page <strong>1</strong> of <strong>2</strong>" in res_p1.text
    assert "Next ›" in res_p1.text

    # Page 2
    res_p2 = await client.get("/?page=2&per_page=10")
    assert res_p2.status_code == 200
    assert "Showing page <strong>2</strong> of <strong>2</strong>" in res_p2.text
    assert "‹ Previous" in res_p2.text
