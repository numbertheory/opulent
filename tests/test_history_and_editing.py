import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from opulent.services.diff_service import compute_diff, render_diff_html
from opulent.services.document_service import (
    get_document_version,
    get_document_versions,
    get_or_create_document,
    update_document,
)


@pytest.mark.asyncio
async def test_initial_document_creates_version_1(db_session: AsyncSession):
    doc, is_dup = await get_or_create_document(
        db_session,
        title="Initial Doc",
        format_type="markdown",
        content="First line of content",
    )
    assert not is_dup
    assert doc.current_version == 1
    assert doc.version_count == 1

    versions = await get_document_versions(db_session, doc.doc_id)
    assert len(versions) == 1
    assert versions[0].version == 1
    assert versions[0].title == "Initial Doc"
    assert versions[0].content == "First line of content"


@pytest.mark.asyncio
async def test_edit_document_creates_new_version(db_session: AsyncSession):
    doc, _ = await get_or_create_document(
        db_session,
        title="Note v1",
        format_type="markdown",
        content="Line 1\nLine 2",
    )

    # Edit document
    updated_doc, new_ver, has_changed = await update_document(
        db_session,
        doc_id=doc.doc_id,
        title="Note v2",
        format_type="markdown",
        content="Line 1\nLine 2 modified\nLine 3 added",
    )

    assert has_changed is True
    assert updated_doc.title == "Note v2"
    assert updated_doc.current_version == 2
    assert updated_doc.version_count == 2
    assert new_ver.version == 2

    # Check that Version 1 remains unchanged in history
    _, v1 = await get_document_version(db_session, doc.doc_id, version=1)
    assert v1 is not None
    assert v1.title == "Note v1"
    assert v1.content == "Line 1\nLine 2"

    # Check Version 2
    _, v2 = await get_document_version(db_session, doc.doc_id, version=2)
    assert v2 is not None
    assert v2.title == "Note v2"
    assert v2.content == "Line 1\nLine 2 modified\nLine 3 added"


@pytest.mark.asyncio
async def test_edit_without_changes_skips_version(db_session: AsyncSession):
    doc, _ = await get_or_create_document(
        db_session,
        title="Static Note",
        format_type="plain",
        content="Unchanged text",
    )

    updated_doc, ver, has_changed = await update_document(
        db_session,
        doc_id=doc.doc_id,
        title="Static Note",
        format_type="plain",
        content="Unchanged text",
    )

    assert has_changed is False
    assert updated_doc.current_version == 1
    assert updated_doc.version_count == 1


@pytest.mark.asyncio
async def test_diff_service_computation():
    t1 = "Line A\nLine B\nLine C"
    t2 = "Line A\nLine B changed\nLine C\nLine D"

    diff = compute_diff(
        title1="Title 1",
        format1="plain",
        content1=t1,
        title2="Title 2",
        format2="markdown",
        content2=t2,
    )

    assert diff.title_v1 == "Title 1"
    assert diff.title_v2 == "Title 2"
    assert diff.format_v1 == "plain"
    assert diff.format_v2 == "markdown"
    assert diff.additions >= 2  # 'Line B changed' and 'Line D'
    assert diff.deletions >= 1  # 'Line B'

    html_diff = render_diff_html(diff)
    assert '<table class="diff-table">' in html_diff
    assert "diff-add" in html_diff
    assert "diff-del" in html_diff


@pytest.mark.asyncio
async def test_api_edit_and_history_flow(client: AsyncClient):
    # 1. Create document
    create_res = await client.post(
        "/api/docs",
        json={"title": "Roadmap", "format": "markdown", "content": "- Phase 1"},
    )
    assert create_res.status_code == 201
    doc_id = create_res.json()["id"]
    assert create_res.json()["version"] == 1

    # 2. Edit document via PUT
    edit_payload = {
        "title": "Roadmap 2026",
        "format": "markdown",
        "content": "- Phase 1 (Completed)\n- Phase 2 (In Progress)",
    }
    edit_res = await client.put(f"/api/docs/{doc_id}", json=edit_payload)
    assert edit_res.status_code == 200
    edit_data = edit_res.json()
    assert edit_data["title"] == "Roadmap 2026"
    assert edit_data["version"] == 2
    assert edit_data["version_count"] == 2

    # 3. Retrieve history via API
    history_res = await client.get(f"/api/docs/{doc_id}/history")
    assert history_res.status_code == 200
    hist_data = history_res.json()
    assert hist_data["total_versions"] == 2
    assert hist_data["current_version"] == 2
    assert len(hist_data["versions"]) == 2

    # 4. Retrieve specific historical version v1
    v1_res = await client.get(f"/api/docs/{doc_id}/history/1")
    assert v1_res.status_code == 200
    v1_data = v1_res.json()
    assert v1_data["version"] == 1
    assert v1_data["title"] == "Roadmap"
    assert v1_data["content"] == "- Phase 1"

    # 5. Retrieve historical raw text
    v1_raw = await client.get(f"/api/docs/{doc_id}/history/1/raw")
    assert v1_raw.status_code == 200
    assert v1_raw.text == "- Phase 1"

    # 6. Compare v1 vs v2 via API
    compare_res = await client.get(f"/api/docs/{doc_id}/compare?v1=1&v2=2")
    assert compare_res.status_code == 200
    comp_data = compare_res.json()
    assert comp_data["v1"] == 1
    assert comp_data["v2"] == 2
    assert comp_data["title_v1"] == "Roadmap"
    assert comp_data["title_v2"] == "Roadmap 2026"
    assert comp_data["additions"] > 0
    assert len(comp_data["lines"]) > 0


@pytest.mark.asyncio
async def test_web_edit_and_compare_flow(client: AsyncClient):
    # 1. Create document via web form
    post_res = await client.post(
        "/docs",
        data={"title": "Draft Document", "format": "markdown", "content": "Initial Draft"},
        follow_redirects=False,
    )
    doc_id = post_res.headers["location"].split("/docs/")[1]

    # 2. Get edit page
    edit_page = await client.get(f"/docs/{doc_id}/edit")
    assert edit_page.status_code == 200
    assert "Edit Document" in edit_page.text
    assert "Draft Document" in edit_page.text
    assert "Initial Draft" in edit_page.text

    # 3. Post edits
    edit_submit = await client.post(
        f"/docs/{doc_id}/edit",
        data={
            "title": "Final Document",
            "format": "markdown",
            "content": "Initial Draft modified\nSecond paragraph",
        },
        follow_redirects=False,
    )
    assert edit_submit.status_code == 303
    assert edit_submit.headers["location"] == f"/docs/{doc_id}?edited=1"

    # 4. View updated document
    view_page = await client.get(f"/docs/{doc_id}?edited=1")
    assert view_page.status_code == 200
    assert "Document Updated" in view_page.text
    assert "Final Document" in view_page.text
    assert "v2" in view_page.text

    # 5. View history page
    hist_page = await client.get(f"/docs/{doc_id}/history")
    assert hist_page.status_code == 200
    assert "Version History" in hist_page.text
    assert "v1" in hist_page.text
    assert "v2" in hist_page.text

    # 6. View historical version 1
    v1_page = await client.get(f"/docs/{doc_id}/history/1")
    assert v1_page.status_code == 200
    assert "Historical Revision" in v1_page.text
    assert "Draft Document" in v1_page.text

    # 7. View comparison page
    comp_page = await client.get(f"/docs/{doc_id}/compare?v1=1&v2=2")
    assert comp_page.status_code == 200
    assert "Compare Versions" in comp_page.text
    assert "Draft Document" in comp_page.text
    assert "Final Document" in comp_page.text
    assert "diff-table" in comp_page.text


@pytest.mark.asyncio
async def test_compare_nonexistent_versions_error(client: AsyncClient):
    create_res = await client.post(
        "/api/docs",
        json={"title": "Doc", "format": "plain", "content": "Content"},
    )
    doc_id = create_res.json()["id"]

    # Invalid version in API
    bad_api = await client.get(f"/api/docs/{doc_id}/compare?v1=1&v2=99")
    assert bad_api.status_code == 404

    # Invalid version in Web
    bad_web = await client.get(f"/docs/{doc_id}/compare?v1=1&v2=99")
    assert bad_web.status_code == 404
