from dataclasses import asdict, dataclass
import difflib
import html


@dataclass
class DiffLine:
    type: str  # 'equal', 'insert', 'delete'
    old_lineno: int | None
    new_lineno: int | None
    content: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DiffResult:
    title_v1: str
    title_v2: str
    format_v1: str
    format_v2: str
    additions: int
    deletions: int
    lines: list[DiffLine]

    @property
    def has_changes(self) -> bool:
        return (
            self.additions > 0
            or self.deletions > 0
            or self.title_v1 != self.title_v2
            or self.format_v1 != self.format_v2
        )


def compute_diff(
    title1: str,
    format1: str,
    content1: str,
    title2: str,
    format2: str,
    content2: str,
) -> DiffResult:
    """
    Compute structured diff between two document revisions.
    """
    lines1 = content1.splitlines()
    lines2 = content2.splitlines()

    matcher = difflib.SequenceMatcher(None, lines1, lines2)
    diff_lines: list[DiffLine] = []
    additions = 0
    deletions = 0

    old_idx = 1
    new_idx = 1

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for line in lines1[i1:i2]:
                diff_lines.append(
                    DiffLine(
                        type="equal",
                        old_lineno=old_idx,
                        new_lineno=new_idx,
                        content=line,
                    )
                )
                old_idx += 1
                new_idx += 1
        elif tag == "delete":
            for line in lines1[i1:i2]:
                diff_lines.append(
                    DiffLine(
                        type="delete",
                        old_lineno=old_idx,
                        new_lineno=None,
                        content=line,
                    )
                )
                old_idx += 1
                deletions += 1
        elif tag == "insert":
            for line in lines2[j1:j2]:
                diff_lines.append(
                    DiffLine(
                        type="insert",
                        old_lineno=None,
                        new_lineno=new_idx,
                        content=line,
                    )
                )
                new_idx += 1
                additions += 1
        elif tag == "replace":
            for line in lines1[i1:i2]:
                diff_lines.append(
                    DiffLine(
                        type="delete",
                        old_lineno=old_idx,
                        new_lineno=None,
                        content=line,
                    )
                )
                old_idx += 1
                deletions += 1
            for line in lines2[j1:j2]:
                diff_lines.append(
                    DiffLine(
                        type="insert",
                        old_lineno=None,
                        new_lineno=new_idx,
                        content=line,
                    )
                )
                new_idx += 1
                additions += 1

    return DiffResult(
        title_v1=title1,
        title_v2=title2,
        format_v1=format1,
        format_v2=format2,
        additions=additions,
        deletions=deletions,
        lines=diff_lines,
    )


def render_diff_html(diff: DiffResult) -> str:
    """Render unified diff table into styled HTML."""
    rows = []
    for line in diff.lines:
        old_num = str(line.old_lineno) if line.old_lineno is not None else ""
        new_num = str(line.new_lineno) if line.new_lineno is not None else ""
        escaped_content = html.escape(line.content) if line.content else "&nbsp;"

        if line.type == "insert":
            symbol = "+"
            css_class = "diff-line diff-add"
        elif line.type == "delete":
            symbol = "-"
            css_class = "diff-line diff-del"
        else:
            symbol = " "
            css_class = "diff-line diff-equal"

        rows.append(
            f'<tr class="{css_class}">'
            f'<td class="diff-gutter old-num">{old_num}</td>'
            f'<td class="diff-gutter new-num">{new_num}</td>'
            f'<td class="diff-symbol">{symbol}</td>'
            f'<td class="diff-code"><code>{escaped_content}</code></td>'
            f"</tr>"
        )

    tbody = "\n".join(rows)
    return (
        f'<table class="diff-table">\n'
        f"<thead><tr>"
        f'<th class="diff-gutter">Old</th>'
        f'<th class="diff-gutter">New</th>'
        f'<th class="diff-symbol"></th>'
        f'<th class="diff-code">Content</th>'
        f"</tr></thead>\n"
        f"<tbody>\n{tbody}\n</tbody>\n"
        f"</table>"
    )
