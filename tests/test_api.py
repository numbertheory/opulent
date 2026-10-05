import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_api_create_document(client: AsyncClient):
    payload = {
        "title": "API Test",
        "format": "python",
        "content": "def hello():\n    return 'world'",
    }
    response = await client.post("/api/docs", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["title"] == "API Test"
    assert data["format"] == "python"
    assert data["display_format"] == "Python"
    assert data["content"] == payload["content"]
    assert data["is_duplicate"] is False
    assert "id" in data
    assert data["url"].endswith(f"/docs/{data['id']}")
    assert data["raw_url"].endswith(f"/docs/{data['id']}/raw")


@pytest.mark.asyncio
async def test_api_deduplication(client: AsyncClient):
    payload = {
        "title": "Dedup API Test",
        "format": "markdown",
        "content": "# Deduplicated Content",
    }
    res1 = await client.post("/api/docs", json=payload)
    assert res1.status_code == 201
    data1 = res1.json()

    # Submit again
    res2 = await client.post("/api/docs", json=payload)
    assert res2.status_code == 200
    data2 = res2.json()

    assert data2["is_duplicate"] is True
    assert data2["id"] == data1["id"]


@pytest.mark.asyncio
async def test_api_get_full_text(client: AsyncClient):
    payload = {
        "title": "Grab Full Text",
        "format": "json",
        "content": '{\n  "status": "ok"\n}',
    }
    create_res = await client.post("/api/docs", json=payload)
    doc_id = create_res.json()["id"]

    # Grab full text via REST API JSON
    get_res = await client.get(f"/api/docs/{doc_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["content"] == payload["content"]
    assert data["title"] == "Grab Full Text"
    assert data["views"] >= 1


@pytest.mark.asyncio
async def test_api_get_raw_text(client: AsyncClient):
    content = "RAW TEXT CONTENT\nSECOND LINE\n"
    create_res = await client.post(
        "/api/docs",
        json={"title": "Raw Test", "format": "plain", "content": content},
    )
    doc_id = create_res.json()["id"]

    # Grab full text via REST API raw endpoint
    raw_res = await client.get(f"/api/docs/{doc_id}/raw")
    assert raw_res.status_code == 200
    assert "text/plain" in raw_res.headers["content-type"]
    assert raw_res.text.strip() == content.strip()


@pytest.mark.asyncio
async def test_api_get_nonexistent_doc(client: AsyncClient):
    res_json = await client.get("/api/docs/does_not_exist")
    assert res_json.status_code == 404
    assert "not found" in res_json.json()["detail"].lower()

    res_raw = await client.get("/api/docs/does_not_exist/raw")
    assert res_raw.status_code == 404


@pytest.mark.asyncio
async def test_api_list_pagination(client: AsyncClient):
    # Create 7 documents
    for i in range(7):
        await client.post(
            "/api/docs",
            json={
                "title": f"Doc {i}",
                "format": "markdown",
                "content": f"Content {i}",
            },
        )

    res = await client.get("/api/docs?page=1&per_page=3")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 7
    assert data["page"] == 1
    assert data["per_page"] == 3
    assert data["total_pages"] == 3
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_api_create_empty_fails(client: AsyncClient):
    res = await client.post(
        "/api/docs",
        json={"title": "Empty", "format": "plain", "content": "   "},
    )
    assert res.status_code == 400
