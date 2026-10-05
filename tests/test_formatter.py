from opulent.formatter import (
    calculate_stats,
    format_code,
    format_markdown,
    format_plain_text,
    get_pygments_css,
    normalize_format,
    render_document_html,
)


def test_normalize_format():
    assert normalize_format("markdown") == "markdown"
    assert normalize_format("MD") == "markdown"
    assert normalize_format("py") == "python"
    assert normalize_format("js") == "javascript"
    assert normalize_format("sh") == "bash"
    assert normalize_format("unknown_lang") == "plain"
    assert normalize_format(None) == "markdown"


def test_format_markdown_elements():
    md_text = "# Header 1\n\n**Bold Text**\n\n- Item 1\n- Item 2\n\n```python\nprint(1)\n```"
    html = format_markdown(md_text)
    assert "<h1" in html
    assert "<strong>Bold Text</strong>" in html
    assert "<li>Item 1</li>" in html


def test_format_markdown_xss_protection():
    malicious = (
        '# Title\n<script>alert("xss")</script>\n<img src=x onerror=alert(1)>\n'
        '[click me](javascript:alert(2))'
    )
    clean = format_markdown(malicious)
    assert "<script>" not in clean
    assert "onerror" not in clean
    assert "javascript:" not in clean


def test_format_code_syntax_highlighting():
    code = "def add(a, b):\n    return a + b"
    html = format_code(code, "python")
    assert '<table class="highlighttable">' in html
    assert "def" in html
    assert "add" in html
    assert '<td class="linenos">' in html


def test_format_plain_text_escaping():
    text = "<script>alert('plain')</script>\nLine 2 & 'quotes'"
    html = format_plain_text(text)
    assert "&lt;script&gt;alert(&#x27;plain&#x27;)&lt;/script&gt;" in html or "&lt;script&gt;" in html
    assert "<script>" not in html
    assert 'class="linenos"' in html


def test_render_document_html_routing():
    md = render_document_html("# Title", "markdown")
    assert 'class="markdown-body"' in md

    py = render_document_html("x = 1", "python")
    assert 'class="highlight"' in py

    txt = render_document_html("plain text", "plain")
    assert 'class="highlight plain-highlight"' in txt


def test_calculate_stats():
    text = "First line\nSecond line with words\nThird"
    stats = calculate_stats(text)
    assert stats["lines"] == 3
    assert stats["words"] == 7
    assert stats["chars"] == len(text)


def test_get_pygments_css():
    css = get_pygments_css()
    assert ".highlight" in css
