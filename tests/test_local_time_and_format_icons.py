from datetime import datetime, timezone
import pytest
from httpx import AsyncClient

from opulent.formatter import (
    FORMAT_ICONS_SVG,
    SUPPORTED_FORMATS,
    format_datetime_12h,
    get_format_icon_svg,
    to_iso_utc,
)


def test_format_datetime_12h():
    """Verify 12-hour clock format with lowercase am/pm and no leading zero on hour."""
    # 1:19pm (13:19)
    dt1 = datetime(2026, 10, 5, 13, 19, 0)
    assert format_datetime_12h(dt1) == "2026-10-05 1:19pm"

    # 1:09pm (13:09) - no leading zero on hour, leading zero on minute
    dt2 = datetime(2026, 10, 5, 13, 9, 0)
    assert format_datetime_12h(dt2) == "2026-10-05 1:09pm"

    # 1:09am (01:09)
    dt3 = datetime(2026, 10, 5, 1, 9, 0)
    assert format_datetime_12h(dt3) == "2026-10-05 1:09am"

    # 12:00am (midnight)
    dt_midnight = datetime(2026, 10, 5, 0, 0, 0)
    assert format_datetime_12h(dt_midnight) == "2026-10-05 12:00am"

    # 12:00pm (noon)
    dt_noon = datetime(2026, 10, 5, 12, 0, 0)
    assert format_datetime_12h(dt_noon) == "2026-10-05 12:00pm"

    # With seconds
    assert format_datetime_12h(dt1, include_seconds=True) == "2026-10-05 1:19:00pm"
    assert format_datetime_12h(dt2, include_seconds=True) == "2026-10-05 1:09:00pm"

    # None handling
    assert format_datetime_12h(None) == ""


def test_format_icons_specifications():
    """Verify specific format icon designs per prompt requirements."""
    # Python: line drawing of a green snake icon
    python_svg = get_format_icon_svg("python")
    assert 'stroke="#10b981"' in python_svg
    assert 'fill="none"' in python_svg
    assert "format-icon-python" in python_svg

    # Rust: red line drawing of a crab
    rust_svg = get_format_icon_svg("rust")
    assert 'stroke="#ef4444"' in rust_svg
    assert 'fill="none"' in rust_svg
    assert "format-icon-rust" in rust_svg

    # Go: minimalist line format matching GoLang icon
    go_svg = get_format_icon_svg("go")
    assert 'stroke="#00ADD8"' in go_svg
    assert 'fill="none"' in go_svg
    assert "format-icon-go" in go_svg

    # Dockerfile: line drawing of a whale, not copying Docker company logo (no stacked container rects)
    docker_svg = get_format_icon_svg("dockerfile")
    assert "format-icon-dockerfile" in docker_svg
    assert 'fill="none"' in docker_svg
    # Must not have the 4 stacked container rectangles of Docker logo
    assert '<rect x="4" y="9"' not in docker_svg
    assert '<rect x="8" y="5"' not in docker_svg

    # XML and HTML: HTML uses the exact same logo as XML
    xml_svg = get_format_icon_svg("xml")
    html_svg = get_format_icon_svg("html")
    # Both use the code bracket polyline points
    assert 'points="7 8 3 12 7 16"' in xml_svg
    assert 'points="7 8 3 12 7 16"' in html_svg
    assert 'points="17 8 21 12 17 16"' in xml_svg
    assert 'points="17 8 21 12 17 16"' in html_svg
    assert 'x1="14" y1="4" x2="10" y2="20"' in xml_svg
    assert 'x1="14" y1="4" x2="10" y2="20"' in html_svg


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
    import re
    assert re.search(r'<time class="local-time"[^>]*>\s*\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}(?:am|pm)\s*</time>', docs_res.text)

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
