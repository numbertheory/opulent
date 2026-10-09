from datetime import datetime, timezone
import html
import bleach
import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.util import ClassNotFound

# Mapping of supported format identifiers to human-readable labels
SUPPORTED_FORMATS: dict[str, str] = {
    "markdown": "Markdown",
    "plain": "Plain Text",
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "html": "HTML",
    "css": "CSS",
    "json": "JSON",
    "yaml": "YAML",
    "sql": "SQL",
    "bash": "Shell / Bash",
    "go": "Go",
    "rust": "Rust",
    "c": "C",
    "cpp": "C++",
    "java": "Java",
    "dockerfile": "Dockerfile",
    "xml": "XML",
}

# Alias mappings for user convenience or extensions
FORMAT_ALIASES: dict[str, str] = {
    "md": "markdown",
    "txt": "plain",
    "text": "plain",
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "sh": "bash",
    "shell": "bash",
    "zsh": "bash",
    "yml": "yaml",
    "golang": "go",
    "rs": "rust",
}

ALLOWED_TAGS = [
    "a", "abbr", "acronym", "b", "blockquote", "code", "em", "i", "li", "ol",
    "strong", "ul", "h1", "h2", "h3", "h4", "h5", "h6", "p", "pre", "hr",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td", "span", "div",
    "del", "ins", "sub", "sup", "img", "details", "summary", "kbd", "samp", "br",
]

ALLOWED_ATTRIBUTES = {
    "*": ["class", "id", "title"],
    "a": ["href", "title", "rel", "target"],
    "img": ["src", "alt", "title", "width", "height"],
    "th": ["align"],
    "td": ["align"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def normalize_format(fmt: str | None) -> str:
    """Normalize format name and check against aliases."""
    if not fmt:
        return "markdown"
    f = fmt.strip().lower()
    return FORMAT_ALIASES.get(f, f if f in SUPPORTED_FORMATS else "plain")


def format_markdown(content: str) -> str:
    """Render markdown safely to HTML with code highlighting and sanitize with bleach."""
    md = markdown.Markdown(
        extensions=[
            "extra",
            "codehilite",
            "nl2br",
            "sane_lists",
            "toc",
        ],
        extension_configs={
            "codehilite": {
                "css_class": "highlight",
                "linenums": False,
                "guess_lang": False,
            }
        },
    )
    raw_html = md.convert(content)

    # Sanitize HTML with bleach
    clean_html = bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    # Ensure links have rel="noopener noreferrer" and target="_blank"
    clean_html = bleach.linkify(clean_html, parse_email=True)
    return clean_html


def format_code(content: str, lang: str) -> str:
    """Render code with syntax highlighting using Pygments with line numbers."""
    try:
        lexer = get_lexer_by_name(lang, stripall=False)
    except ClassNotFound:
        lexer = TextLexer(stripall=False)

    formatter = HtmlFormatter(
        cssclass="highlight",
        linenos="table",
        lineanchors="L",
        linespans="line",
        anchorlinenos=True,
    )
    return highlight(content, lexer, formatter)


def format_plain_text(content: str) -> str:
    """Render plain text with safe escaping and line numbering table."""
    lines = content.split("\n")
    table_rows = []
    for idx, line in enumerate(lines, start=1):
        escaped_line = html.escape(line) if line else "&nbsp;"
        table_rows.append(
            f'<tr><td class="linenos"><a href="#L{idx}" id="L{idx}">{idx}</a></td>'
            f'<td class="code"><span id="line-{idx}">{escaped_line}</span></td></tr>'
        )
    table_body = "".join(table_rows)
    return f'<div class="highlight plain-highlight"><table class="highlighttable"><tbody>{table_body}</tbody></table></div>'


def render_document_html(content: str, format_type: str) -> str:
    """
    Format document content into safe, styled HTML based on the specified format.
    """
    normalized_format = normalize_format(format_type)

    if normalized_format == "markdown":
        return f'<div class="markdown-body">{format_markdown(content)}</div>'
    elif normalized_format == "plain":
        return format_plain_text(content)
    else:
        # Programming language syntax highlighting
        return format_code(content, normalized_format)


def get_pygments_css(style_name: str = "one-dark") -> str:
    """Generate Pygments CSS stylesheet for syntax highlighting."""
    formatter = HtmlFormatter(style=style_name, cssclass="highlight")
    return formatter.get_style_defs(".highlight")


def calculate_stats(content: str) -> dict[str, int]:
    """Calculate lines, words, and character counts for content."""
    lines = content.count("\n") + (1 if content else 0)
    words = len(content.split())
    chars = len(content)
    return {
        "lines": lines,
        "words": words,
        "chars": chars,
    }


def to_iso_utc(dt: datetime | None) -> str:
    """Format datetime into ISO 8601 string in UTC for client-side local conversion."""
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


def format_datetime_12h(dt: datetime | None, include_seconds: bool = False) -> str:
    """
    Format a datetime in 12-hour format: YYYY-MM-DD h:mm[am|pm], e.g. 2026-10-05 1:19pm.
    No leading zero on the hour, leading zero on the minute, lowercase am/pm directly adjacent.
    """
    if not dt:
        return ""
    hour = str(int(dt.strftime("%I")))
    mins = dt.strftime("%M")
    ampm = dt.strftime("%p").lower()
    date_str = dt.strftime("%Y-%m-%d")
    if include_seconds:
        secs = dt.strftime("%S")
        return f"{date_str} {hour}:{mins}:{secs}{ampm}"
    return f"{date_str} {hour}:{mins}{ampm}"


FORMAT_ICONS_SVG: dict[str, str] = {
    "markdown": (
        '<svg class="format-icon format-icon-markdown" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-label="Markdown">'
        '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 15V9l3 4 3-4v6"/><path d="M17 12l2 2 2-2"/><path d="M19 9v5"/>'
        '</svg>'
    ),
    "plain": (
        '<svg class="format-icon format-icon-plain" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-label="Plain Text">'
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="14" y2="17"/>'
        '</svg>'
    ),
    "python": (
        '<svg class="format-icon format-icon-python" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-label="Python">'
        '<path d="M17 7.5c0-2.5-2-4-4.5-4s-4.5 1.8-4.5 4.2c0 2.8 2.2 3.8 4.5 4.8 2.5 1 4.5 2.2 4.5 4.8 0 2.5-2 4.2-4.5 4.2-3 0-5-2-5.5-4.5"/>'
        '<path d="M17 7.5h2.5l1.5-1m-1.5 1l1.5 1"/>'
        '<circle cx="14.5" cy="6" r="0.8" fill="#10b981"/>'
        '</svg>'
    ),
    "javascript": (
        '<svg class="format-icon format-icon-javascript" width="18" height="18" viewBox="0 0 24 24" fill="none" aria-label="JavaScript">'
        '<rect width="22" height="22" x="1" y="1" rx="4" fill="#F7DF1E"/>'
        '<path d="M8 17.5c0 .8-.5 1.2-1.3 1.2-.7 0-1.2-.4-1.3-.9l1.1-.6c0 .3.1.5.3.5.2 0 .3-.1.3-.3v-4.6h1.2v4.7zm4.2-.1c.5 0 .9-.3.9-.7 0-.5-.4-.7-1.1-.9-.9-.3-1.6-.7-1.6-1.7 0-1 .8-1.7 2-1.7.9 0 1.6.4 1.8 1.1l-1 .6c-.1-.3-.4-.5-.8-.5-.4 0-.7.2-.7.5 0 .3.2.5.8.7 1 .4 1.9.7 1.9 1.9 0 1.2-.9 1.9-2.2 1.9-1.1 0-1.9-.5-2.2-1.3l1.1-.6c.2.4.5.7 1 .7z" fill="#000"/>'
        '</svg>'
    ),
    "typescript": (
        '<svg class="format-icon format-icon-typescript" width="18" height="18" viewBox="0 0 24 24" fill="none" aria-label="TypeScript">'
        '<rect width="22" height="22" x="1" y="1" rx="4" fill="#3178C6"/>'
        '<path d="M5.5 8h6v2h-2v7h-2v-7h-2V8zm7.5 5.8c.4.2.9.4 1.5.4.6 0 .9-.2.9-.5s-.2-.4-.8-.6c-1.1-.4-1.8-.9-1.8-1.9 0-1.2.9-2.2 2.5-2.2.8 0 1.5.2 2 .5l-.5 1.6c-.4-.2-.8-.4-1.4-.4-.5 0-.8.2-.8.5s.2.4.9.6c1.1.4 1.7 1 1.7 1.9 0 1.3-1 2.2-2.6 2.2-.9 0-1.7-.2-2.2-.5l.8-1.6z" fill="#FFF"/>'
        '</svg>'
    ),
    "html": (
        '<svg class="format-icon format-icon-html" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-label="HTML">'
        '<polyline points="7 8 3 12 7 16"/><polyline points="17 8 21 12 17 16"/><line x1="14" y1="4" x2="10" y2="20"/>'
        '</svg>'
    ),
    "css": (
        '<svg class="format-icon format-icon-css" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-label="CSS">'
        '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M7 8h10M7 12h10M7 16h6"/>'
        '</svg>'
    ),
    "json": (
        '<svg class="format-icon format-icon-json" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-label="JSON">'
        '<path d="M8 3H6a2 2 0 0 0-2 2v4a2 2 0 0 1-2 2 2 2 0 0 1 2 2v4a2 2 0 0 0 2 2h2"/><path d="M16 3h2a2 2 0 0 1 2 2v4a2 2 0 0 0 2 2 2 2 0 0 0-2 2v4a2 2 0 0 1-2 2h-2"/>'
        '</svg>'
    ),
    "yaml": (
        '<svg class="format-icon format-icon-yaml" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-label="YAML">'
        '<path d="M4 5h5v5H4zM4 14h5v5H4zM15 9.5h5v5h-5z"/><path d="M9 7.5h3.5a2 2 0 0 1 2 2v3m0 0v2a2 2 0 0 1-2 2H9m5.5-4H15"/>'
        '</svg>'
    ),
    "sql": (
        '<svg class="format-icon format-icon-sql" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-label="SQL">'
        '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>'
        '</svg>'
    ),
    "bash": (
        '<svg class="format-icon format-icon-bash" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#34d399" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-label="Bash">'
        '<polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>'
        '</svg>'
    ),
    "go": (
        '<svg class="format-icon format-icon-go" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00ADD8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-label="Go">'
        '<path d="M2 9.5h3.5M1 12h5M2.5 14.5h3"/>'
        '<path d="M14.5 9c-.8-.9-2-1.5-3.5-1.5-2.8 0-4.5 2-4.5 4.5s1.7 4.5 4.5 4.5c2.3 0 3.8-1.2 4.3-2.8H11.5"/>'
        '<ellipse cx="19" cy="12" rx="3" ry="4.2"/>'
        '</svg>'
    ),
    "rust": (
        '<svg class="format-icon format-icon-rust" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-label="Rust">'
        '<path d="M6 13c0-3.3 2.7-5 6-5s6 1.7 6 5c0 3-2.7 5-6 5s-6-2-6-5z"/>'
        '<path d="M9 8V6.5M15 8V6.5"/>'
        '<circle cx="9" cy="5.5" r="1" fill="#ef4444"/>'
        '<circle cx="15" cy="5.5" r="1" fill="#ef4444"/>'
        '<path d="M6 12C4 10 3 8 3 6c2-1 4 1 4 2.5"/>'
        '<path d="M3 6c1.5-2 4-1 4.5.5"/>'
        '<path d="M18 12c2-2 3-4 3-6-2-1-4 1-4 2.5"/>'
        '<path d="M21 6c-1.5-2-4-1-4.5.5"/>'
        '<path d="M5 14l-3 1M5 16l-2 2M6 18l-2 2"/>'
        '<path d="M19 14l3 1M19 16l2 2M18 18l2 2"/>'
        '</svg>'
    ),
    "c": (
        '<svg class="format-icon format-icon-c" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-label="C">'
        '<path d="M12 2l8 4.5v11L12 22l-8-4.5v-11L12 2z"/><path d="M15 9.5a3.5 3.5 0 1 0 0 5"/>'
        '</svg>'
    ),
    "cpp": (
        '<svg class="format-icon format-icon-cpp" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-label="C++">'
        '<path d="M12 2l8 4.5v11L12 22l-8-4.5v-11L12 2z"/><path d="M13 10a2.5 2.5 0 1 0 0 4M17 11v2M16 12h2"/>'
        '</svg>'
    ),
    "java": (
        '<svg class="format-icon format-icon-java" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-label="Java">'
        '<path d="M18 8h1a4 4 0 0 1 0 8h-1"/><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"/><line x1="6" y1="1" x2="6" y2="4"/><line x1="10" y1="1" x2="10" y2="4"/><line x1="14" y1="1" x2="14" y2="4"/>'
        '</svg>'
    ),
    "dockerfile": (
        '<svg class="format-icon format-icon-dockerfile" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-label="Dockerfile">'
        '<path d="M2 13c0-4 4-6 9-6 4 0 7 2 8 4l2-2v5l-2-1c-1 3-4 4-7 4-5 0-9-1.5-10-4z"/>'
        '<path d="M7 14c1 2 3 3 5 2"/>'
        '<circle cx="5.5" cy="11.5" r="0.75" fill="#0ea5e9"/>'
        '<path d="M10 4c0 1.5-.5 3-1.5 3M10 4c0 1.5.5 3 1.5 3M10 2v2"/>'
        '</svg>'
    ),
    "xml": (
        '<svg class="format-icon format-icon-xml" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-label="XML">'
        '<polyline points="7 8 3 12 7 16"/><polyline points="17 8 21 12 17 16"/><line x1="14" y1="4" x2="10" y2="20"/>'
        '</svg>'
    ),
}

DEFAULT_FORMAT_ICON_SVG = (
    '<svg class="format-icon format-icon-default" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-label="Document">'
    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>'
    '</svg>'
)


def get_format_icon_svg(format_type: str) -> str:
    """Return an SVG icon representing the document format."""
    normalized = normalize_format(format_type)
    return FORMAT_ICONS_SVG.get(normalized, DEFAULT_FORMAT_ICON_SVG)
