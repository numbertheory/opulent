import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_all_documents_view_has_deletion_controls(client: AsyncClient):
    """Verify that /documents has checkboxes, delete button, and form."""
    # Create two documents
    res1 = await client.post(
        "/docs",
        data={"title": "Doc Alpha", "format": "markdown", "content": "Content Alpha"},
        follow_redirects=False,
    )
    doc_id1 = res1.headers["location"].split("/docs/")[1]

    res2 = await client.post(
        "/docs",
        data={"title": "Doc Beta", "format": "plain", "content": "Content Beta"},
        follow_redirects=False,
    )
    doc_id2 = res2.headers["location"].split("/docs/")[1]

    # Visit /documents
    doc_list_res = await client.get("/documents")
    assert doc_list_res.status_code == 200
    html = doc_list_res.text

    # Check for select all checkbox and individual checkboxes
    assert 'id="select-all-docs"' in html
    assert 'id="delete-selected-docs-btn"' in html
    assert 'action="/documents/delete"' in html
    assert f'value="{doc_id1}"' in html
    assert f'value="{doc_id2}"' in html
    assert 'class="form-checkbox doc-select-checkbox"' in html


@pytest.mark.asyncio
async def test_delete_single_document_web(client: AsyncClient):
    """Test deleting a single document from /documents."""
    # Create document
    res = await client.post(
        "/docs",
        data={"title": "To Delete 1", "format": "markdown", "content": "Will be deleted"},
        follow_redirects=False,
    )
    doc_id = res.headers["location"].split("/docs/")[1]

    # Delete via POST /documents/delete
    del_res = await client.post(
        "/documents/delete",
        data={"selected_docs": [doc_id]},
        follow_redirects=False,
    )
    assert del_res.status_code == 303
    assert del_res.headers["location"] == "/documents?notice=Successfully+deleted+1+document"

    # Confirm it redirects with notice and document is gone
    final_res = await client.get(del_res.headers["location"])
    assert final_res.status_code == 200
    assert "Successfully deleted 1 document" in final_res.text
    assert "To Delete 1" not in final_res.text

    # Verify viewing the document returns 404
    view_res = await client.get(f"/docs/{doc_id}")
    assert view_res.status_code == 404


@pytest.mark.asyncio
async def test_delete_multiple_documents_web(client: AsyncClient):
    """Test selecting and deleting multiple documents at once."""
    # Create three documents
    doc_ids = []
    for i in range(3):
        res = await client.post(
            "/docs",
            data={"title": f"Batch Doc {i}", "format": "markdown", "content": f"Batch Content {i}"},
            follow_redirects=False,
        )
        doc_ids.append(res.headers["location"].split("/docs/")[1])

    # Delete two of them
    del_res = await client.post(
        "/documents/delete",
        data={"selected_docs": [doc_ids[0], doc_ids[1]]},
        follow_redirects=False,
    )
    assert del_res.status_code == 303
    assert del_res.headers["location"] == "/documents?notice=Successfully+deleted+2+documents"

    # Verify the two are gone, and the third remains
    view1 = await client.get(f"/docs/{doc_ids[0]}")
    assert view1.status_code == 404
    view2 = await client.get(f"/docs/{doc_ids[1]}")
    assert view2.status_code == 404
    view3 = await client.get(f"/docs/{doc_ids[2]}")
    assert view3.status_code == 200
    assert "Batch Doc 2" in view3.text


@pytest.mark.asyncio
async def test_delete_documents_validation_empty(client: AsyncClient):
    """Test submitting delete with no documents selected."""
    del_res = await client.post(
        "/documents/delete",
        data={},
        follow_redirects=False,
    )
    assert del_res.status_code == 303
    assert "error=No+documents+were+selected+for+deletion" in del_res.headers["location"]


@pytest.mark.asyncio
async def test_history_view_has_revision_deletion_controls(client: AsyncClient):
    """Verify that /docs/{doc_id}/history has checkboxes, delete button, and form."""
    # Create a document and make edits to have 3 versions
    res = await client.post(
        "/docs",
        data={"title": "Revision Test", "format": "markdown", "content": "Version 1 content"},
        follow_redirects=False,
    )
    doc_id = res.headers["location"].split("/docs/")[1]

    await client.post(
        f"/docs/{doc_id}/edit",
        data={"title": "Revision Test v2", "format": "markdown", "content": "Version 2 content"},
        follow_redirects=False,
    )

    await client.post(
        f"/docs/{doc_id}/edit",
        data={"title": "Revision Test v3", "format": "markdown", "content": "Version 3 content"},
        follow_redirects=False,
    )

    # View history
    hist_res = await client.get(f"/docs/{doc_id}/history")
    assert hist_res.status_code == 200
    html = hist_res.text

    assert 'id="select-all-revisions"' in html
    assert 'id="delete-selected-revisions-btn"' in html
    assert f'action="/docs/{doc_id}/history/delete"' in html
    assert 'value="1"' in html
    assert 'value="2"' in html
    assert 'value="3"' in html
    assert 'class="form-checkbox revision-select-checkbox"' in html


@pytest.mark.asyncio
async def test_delete_intermediate_revision(client: AsyncClient):
    """Deleting an intermediate revision leaves current version intact and removes that revision."""
    res = await client.post(
        "/docs",
        data={"title": "Inter Doc", "format": "markdown", "content": "Version 1"},
        follow_redirects=False,
    )
    doc_id = res.headers["location"].split("/docs/")[1]

    await client.post(
        f"/docs/{doc_id}/edit",
        data={"title": "Inter Doc", "format": "markdown", "content": "Version 2"},
        follow_redirects=False,
    )
    await client.post(
        f"/docs/{doc_id}/edit",
        data={"title": "Inter Doc", "format": "markdown", "content": "Version 3"},
        follow_redirects=False,
    )

    # Delete version 2
    del_res = await client.post(
        f"/docs/{doc_id}/history/delete",
        data={"selected_versions": [2]},
        follow_redirects=False,
    )
    assert del_res.status_code == 303
    assert del_res.headers["location"] == f"/docs/{doc_id}/history?notice=Successfully+deleted+1+revision"

    # Check history: v2 should be gone, v1 and v3 should remain
    hist_res = await client.get(del_res.headers["location"])
    assert hist_res.status_code == 200
    assert "Successfully deleted 1 revision" in hist_res.text
    assert 'id="checkbox-ver-2"' not in hist_res.text
    assert 'id="checkbox-ver-1"' in hist_res.text
    assert 'id="checkbox-ver-3"' in hist_res.text

    # Document view should still show Version 3
    view_res = await client.get(f"/docs/{doc_id}")
    assert view_res.status_code == 200
    assert "Version 3" in view_res.text


@pytest.mark.asyncio
async def test_delete_latest_revision_rolls_back_document_state(client: AsyncClient):
    """Deleting the latest revision updates the document to the previous remaining version."""
    res = await client.post(
        "/docs",
        data={"title": "Rollback Test v1", "format": "markdown", "content": "Content v1"},
        follow_redirects=False,
    )
    doc_id = res.headers["location"].split("/docs/")[1]

    await client.post(
        f"/docs/{doc_id}/edit",
        data={"title": "Rollback Test v2", "format": "markdown", "content": "Content v2"},
        follow_redirects=False,
    )

    # Delete version 2 (the current latest)
    del_res = await client.post(
        f"/docs/{doc_id}/history/delete",
        data={"selected_versions": [2]},
        follow_redirects=False,
    )
    assert del_res.status_code == 303
    assert del_res.headers["location"] == f"/docs/{doc_id}/history?notice=Successfully+deleted+1+revision"

    # View document: title and content should now be v1!
    view_res = await client.get(f"/docs/{doc_id}")
    assert view_res.status_code == 200
    assert "Rollback Test v1" in view_res.text
    assert "Content v1" in view_res.text
    assert "Rollback Test v2" not in view_res.text


@pytest.mark.asyncio
async def test_delete_all_revisions_deletes_entire_document(client: AsyncClient):
    """Selecting and deleting all revisions permanently deletes the entire document."""
    res = await client.post(
        "/docs",
        data={"title": "Full Delete Test", "format": "plain", "content": "Initial"},
        follow_redirects=False,
    )
    doc_id = res.headers["location"].split("/docs/")[1]

    await client.post(
        f"/docs/{doc_id}/edit",
        data={"title": "Full Delete Test", "format": "plain", "content": "Second"},
        follow_redirects=False,
    )

    # Delete both version 1 and version 2
    del_res = await client.post(
        f"/docs/{doc_id}/history/delete",
        data={"selected_versions": [1, 2]},
        follow_redirects=False,
    )
    assert del_res.status_code == 303
    assert del_res.headers["location"] == f"/documents?notice=Document+{doc_id}+and+all+its+revisions+were+deleted"

    # Verify document no longer exists
    view_res = await client.get(f"/docs/{doc_id}")
    assert view_res.status_code == 404


@pytest.mark.asyncio
async def test_delete_revisions_empty_selection(client: AsyncClient):
    """Submitting revision deletion with no selected versions redirects with error."""
    res = await client.post(
        "/docs",
        data={"title": "Empty Rev Test", "format": "markdown", "content": "Hello"},
        follow_redirects=False,
    )
    doc_id = res.headers["location"].split("/docs/")[1]

    del_res = await client.post(
        f"/docs/{doc_id}/history/delete",
        data={},
        follow_redirects=False,
    )
    assert del_res.status_code == 303
    assert "error=No+revisions+were+selected+for+deletion" in del_res.headers["location"]


@pytest.mark.asyncio
async def test_prohibited_views_do_not_contain_delete_button(client: AsyncClient):
    """
    CRITICAL CONSTRAINT:
    Do not offer a delete button when simply viewing a document or viewing a diff,
    or in the flyover drawer on the left hand side.
    """
    # Create a document with 2 versions
    res = await client.post(
        "/docs",
        data={"title": "Negative Test Doc", "format": "markdown", "content": "Version 1 line"},
        follow_redirects=False,
    )
    doc_id = res.headers["location"].split("/docs/")[1]

    await client.post(
        f"/docs/{doc_id}/edit",
        data={"title": "Negative Test Doc", "format": "markdown", "content": "Version 2 line"},
        follow_redirects=False,
    )

    # 1. Viewing a document (/docs/{doc_id})
    view_res = await client.get(f"/docs/{doc_id}")
    assert view_res.status_code == 200
    view_html = view_res.text
    # Should NOT have any delete button or delete form in view.html
    assert "delete-selected" not in view_html
    assert "/documents/delete" not in view_html
    assert "/history/delete" not in view_html
    assert "Delete Document" not in view_html
    assert "🗑️ Delete" not in view_html

    # 2. Viewing a diff / compare (/docs/{doc_id}/compare)
    diff_res = await client.get(f"/docs/{doc_id}/compare?v1=1&v2=2")
    assert diff_res.status_code == 200
    diff_html = diff_res.text
    # Should NOT have any delete button or delete form in compare.html
    assert "delete-selected" not in diff_html
    assert "/documents/delete" not in diff_html
    assert "/history/delete" not in diff_html
    assert "Delete Document" not in diff_html
    assert "🗑️ Delete" not in diff_html

    # 3. Flyover drawer (#docs-drawer)
    # The drawer is rendered in base.html; let's check its inner HTML on the home page
    home_res = await client.get("/")
    assert home_res.status_code == 200
    home_html = home_res.text
    assert 'id="docs-drawer"' in home_html

    # Extract the drawer HTML
    drawer_start = home_html.find('<aside\n    id="docs-drawer"')
    if drawer_start == -1:
        drawer_start = home_html.find('id="docs-drawer"')
    drawer_end = home_html.find("</aside>", drawer_start)
    drawer_html = home_html[drawer_start:drawer_end]

    assert "delete" not in drawer_html.lower()
    assert "🗑️" not in drawer_html


@pytest.mark.asyncio
async def test_rest_api_deletion(client: AsyncClient):
    """Test REST API endpoints for deleting documents and versions."""
    # Create doc
    res = await client.post(
        "/api/docs",
        json={"title": "API Del Doc", "format": "markdown", "content": "V1"},
    )
    doc_id = res.json()["id"]

    # Add v2
    await client.put(
        f"/api/docs/{doc_id}",
        json={"title": "API Del Doc", "format": "markdown", "content": "V2"},
    )

    # Delete v2 via API
    del_v_res = await client.delete(f"/api/docs/{doc_id}/history/2")
    assert del_v_res.status_code == 200
    assert del_v_res.json()["deleted"] is True
    assert del_v_res.json()["doc_deleted"] is False

    # Check doc is rolled back to v1
    doc_check = await client.get(f"/api/docs/{doc_id}")
    assert doc_check.status_code == 200
    assert doc_check.json()["version"] == 1
    assert doc_check.json()["content"] == "V1"

    # Delete document via API
    del_doc_res = await client.delete(f"/api/docs/{doc_id}")
    assert del_doc_res.status_code == 200
    assert del_doc_res.json()["deleted"] is True

    # Check 404
    get_after = await client.get(f"/api/docs/{doc_id}")
    assert get_after.status_code == 404
