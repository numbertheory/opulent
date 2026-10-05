from datetime import datetime, timezone
import pytest
from httpx import AsyncClient

from opulent.formatter import SUPPORTED_FORMATS, get_format_icon_svg, to_iso_utc


def test_get_format_icon_svg_supported_formats():
    """Verify SVG icons are generated for all supported formats."""
    for fmt in SUPPORTED_FORMATS:
        svg = get_format_icon_svg(fmt)
        assert "<svg" in svg
        assert "</svg>" in svg
        assert "format-icon" in svg
        assert f"format-icon-{fmt}" in svg


def test_get_format_icon_svg_fallback():
    """Verify fallback SVG icon is returned for unknown formats."""
    svg = get_format_icon_svg("unknown_format_xyz")
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "format-icon" in svg


def test_to_iso_utc_timezone_handling():
    """Verify naive and aware datetimes are formatted with UTC timezone info."""
    naive_dt = datetime(2026, 10, 5, 20, 35, 17)
    iso_naive = to_iso_utc(naive_dt)
    assert iso_naive.endswith("+00:00") or iso_naive.endswith("Z")

    aware_dt = datetime(2026, 10, 5, 20, 35, 17, tzinfo=timezone.utc)
    iso_aware = to_iso_utc(aware_dt)
    assert "+00:00" in iso_aware

    assert to_iso_utc(None) == ""


@pytest.mark.asyncio
async def test_all_pages_use_local_time_tags_without_hardcoded_utc(client: AsyncClient):
    """Verify timestamps on all pages use <time class="local-time"> and have no hardcoded 'UTC' strings."""
    # Create document
    create_res = await client.post(
        "/docs",
        data={"title": "Timestamp Test", "format": "markdown", "content": "Initial text"},
        follow_redirects=False,
    )
    doc_id = create_res.headers["location"].split("/docs/")[1]

    # Edit document to create version 2
    await client.post(
        f"/docs/{doc_id}/edit",
        data={"title": "Timestamp Test (Edited)", "format": "python", "content": "Updated code"},
    )

    # 1. Standalone documents list
    docs_res = await client.get("/documents")
    assert docs_res.status_code == 200
    assert 'class="local-time"' in docs_res.text
    # Should not display hardcoded 'UTC' in timestamp text
    assert "UTC" not in docs_res.text.split("<tbody>")[1].split("</tbody>")[0]

    # 2. View page
    view_res = await client.get(f"/docs/{doc_id}")
    assert view_res.status_code == 200
    assert 'class="local-time"' in view_res.text
    # Ensure hardcoded "UTC" is removed from metadata bar
    meta_bar_html = view_res.text.split('class="doc-meta-bar"')[1].split('</div>\n  </div>')[0]
    assert "UTC" not in meta_bar_html
    assert "Created:" in meta_bar_html
    assert "Updated:" in meta_bar_html

    # 3. History page
    history_res = await client.get(f"/docs/{doc_id}/history")
    assert history_res.status_code == 200
    assert 'class="local-time"' in history_res.text
    assert "UTC" not in history_res.text

    # 4. Compare page
    compare_res = await client.get(f"/docs/{doc_id}/compare?v1=1&v2=2")
    assert compare_res.status_code == 200
    assert 'class="local-time"' in compare_res.text


@pytest.mark.asyncio
async def test_standalone_documents_list_columns_and_versions_link(client: AsyncClient):
    """Verify documents list has exactly Document, Updated, Versions columns."""
    create_res = await client.post(
        "/docs",
        data={"title": "Columns Test", "format": "javascript", "content": "console.log('hi');"},
        follow_redirects=False,
    )
    doc_id = create_res.headers["location"].split("/docs/")[1]

    res = await client.get("/documents")
    assert res.status_code == 200

    # Header columns check
    assert "<th>Document</th>" in res.text
    assert "<th>Updated</th>" in res.text
    assert "<th>Versions</th>" in res.text

    # Removed columns
    assert "<th>Format</th>" not in res.text
    assert "<th>Document ID</th>" not in res.text
    assert "<th>Lines</th>" not in res.text
    assert "<th>Actions</th>" not in res.text

    # Format icon directly beside title
    assert 'class="format-icon format-icon-javascript"' in res.text

    # Plain clickable version count linking to history
    assert f'href="/docs/{doc_id}/history"' in res.text
    assert 'class="version-count-link"' in res.text
    # Must not be a full button
    assert 'class="btn ' not in res.text.split(f'href="/docs/{doc_id}/history"')[1].split("</a>")[0]
