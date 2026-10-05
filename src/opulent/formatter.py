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
    "del", "ins", "sub", "sup", "img", "details", "summary", "kbd", "samp",
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
