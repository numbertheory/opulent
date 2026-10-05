# Opulent 💎

**Opulent** is a modern, frictionless pastebin and text document web service written in Python. It allows users to compose, format, and share text documents directly within the browser without requiring any login.

Every document receives its own distinct URL formatted as `http://opulent-url/docs/<doc-id>`, powered by a deterministic content-addressable identifier that prevents redundant duplicates. Users can edit documents, preserve complete version histories, view previous revisions, and visually compare any two versions. An intuitive REST API allows automated full-text retrieval, creation, updates, and diffing.

---

## Features

- **No Authentication Required**: Immediate, pastebin-style publishing and editing with zero login friction.
- **Smart Deduplication**: The initial `doc-id` is generated deterministically from the document's content, title, and format using SHA-256 hash slicing in Base62. Identical submissions automatically resolve to the existing document's URL without polluting the database with duplicates.
- **Full Version History & Revision Tracking**:
  - Every note records all of its revisions (`v1`, `v2`, `v3`...).
  - Any version can be browsed with full formatting (`/docs/<doc-id>/history/<version>`) or raw text streaming.
  - History timeline view with timestamps, titles, formats, line counts, and word counts.
- **Visual Diff & Comparison**:
  - Compare any two revisions (`/docs/<doc-id>/compare?v1=1&v2=2`).
  - Unified color-coded diff table showing added lines (green `+`), deleted lines (red `-`), line numbers, and metadata differences (title and format changes).
  - Also available as structured JSON in the REST API (`/api/docs/<doc-id>/compare`).
- **Rich Formatting & Syntax Highlighting**:
  - **Markdown**: Full GitHub-flavored Markdown rendering (tables, code blocks, lists, blockquotes) safely sanitized with [Bleach](https://github.com/mozilla/bleach) to prevent XSS.
  - **Code**: Server-side syntax highlighting with line numbering for Python, JavaScript, TypeScript, HTML, CSS, JSON, YAML, SQL, Shell/Bash, Go, Rust, Java, C/C++, Dockerfile, and XML via [Pygments](https://pygments.org/).
  - **Plain Text**: Monospace layout with line numbers and safe HTML escaping.
- **Paginated Document Explorer**: The homepage displays an editor alongside a paginated list of all published documents with snippet previews, version badges, stats, and navigation controls.
- **Full-Text REST API**: JSON endpoints for publishing, editing, fetching full document details, revision history, and diffs, plus dedicated raw text endpoints (`/api/docs/<doc-id>/raw` and `/docs/<doc-id>/raw`) for `curl` and CLI workflows.
- **Modern Opulent Theme**: Obsidian and warm-gold dark aesthetic with responsive design, keyboard shortcuts (`Ctrl+Enter` to submit/save, `Tab` indentation in the editor), and clipboard copy helpers.
- **Containerized Orchestration**: Production-ready `Dockerfile` and `docker-compose.yml` bundling the FastAPI service and PostgreSQL 16 with health checks and persistent volume storage.
- **Fast Package Management**: Managed with [`uv`](https://github.com/astral-sh/uv).

---

## Quick Start with Docker Compose

To launch the entire service (PostgreSQL database + Opulent web app) in Docker containers:

```bash
docker compose up --build -d
```

The service will be accessible at:
- **Web UI**: [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Docs**: [http://localhost:8000/api/docs-ui](http://localhost:8000/api/docs-ui)
- **Health Check**: [http://localhost:8000/healthz](http://localhost:8000/healthz)

To shut down:
```bash
docker compose down
```

---

## Local Development with `uv`

### Prerequisites
- Python 3.13+
- [`uv`](https://github.com/astral-sh/uv)

### Setup & Run
1. **Clone the repository and install dependencies**:
   ```bash
   uv sync
   ```

2. **Run tests**:
   ```bash
   uv run pytest -v
   ```

3. **Run the server locally**:
   ```bash
   uv run uvicorn opulent.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## REST API Reference

### 1. Create a Document
- **Endpoint**: `POST /api/docs`
- **Request Body**:
  ```json
  {
    "title": "Release Notes",
    "format": "markdown",
    "content": "## Version 1.0\n- Initial release"
  }
  ```
- **Responses**:
  - `201 Created` for newly published documents.
  - `200 OK` if the exact document already exists (with `"is_duplicate": true`).

### 2. Grab Full Text of a Document (JSON)
- **Endpoint**: `GET /api/docs/{doc-id}`
- **Curl**:
  ```bash
  curl http://localhost:8000/api/docs/{doc-id}
  ```

### 3. Edit / Update a Document (Creates New Version)
- **Endpoint**: `PUT /api/docs/{doc-id}`
- **Request Body**:
  ```json
  {
    "title": "Release Notes v2",
    "format": "markdown",
    "content": "## Version 1.0\n- Initial release\n## Version 2.0\n- Added editing & history"
  }
  ```
- **Curl**:
  ```bash
  curl -X PUT http://localhost:8000/api/docs/{doc-id} \
    -H "Content-Type: application/json" \
    -d '{"title": "Release Notes v2", "format": "markdown", "content": "## Version 2.0\n- Added history"}'
  ```

### 4. View Document Revision History
- **Endpoint**: `GET /api/docs/{doc-id}/history`
- **Curl**:
  ```bash
  curl http://localhost:8000/api/docs/{doc-id}/history
  ```

### 5. Grab Historical Version
- **Endpoint**: `GET /api/docs/{doc-id}/history/{version}`
- **Curl**:
  ```bash
  curl http://localhost:8000/api/docs/{doc-id}/history/1
  ```

### 6. Compare Two Versions (Diff API)
- **Endpoint**: `GET /api/docs/{doc-id}/compare?v1={v1}&v2={v2}`
- **Curl**:
  ```bash
  curl "http://localhost:8000/api/docs/{doc-id}/compare?v1=1&v2=2"
  ```
- **Response Example**:
  ```json
  {
    "doc_id": "3QhZoXS4vr",
    "v1": 1,
    "v2": 2,
    "title_v1": "Release Notes",
    "title_v2": "Release Notes v2",
    "format_v1": "markdown",
    "format_v2": "markdown",
    "additions": 2,
    "deletions": 0,
    "lines": [
      {"type": "equal", "old_lineno": 1, "new_lineno": 1, "content": "## Version 1.0"},
      {"type": "equal", "old_lineno": 2, "new_lineno": 2, "content": "- Initial release"},
      {"type": "insert", "old_lineno": null, "new_lineno": 3, "content": "## Version 2.0"},
      {"type": "insert", "old_lineno": null, "new_lineno": 4, "content": "- Added editing & history"}
    ]
  }
  ```

### 7. Grab Raw Full Text (Plain Text)
- **Endpoint**: `GET /api/docs/{doc-id}/raw` or `GET /docs/{doc-id}/raw`
- **Historical Raw**: `GET /api/docs/{doc-id}/history/{version}/raw` or `GET /docs/{doc-id}/history/{version}/raw`

### 8. List Documents (Paginated)
- **Endpoint**: `GET /api/docs?page=1&per_page=15`

---

## Web Browser URLs

| URL | Description |
| :--- | :--- |
| `http://localhost:8000/` | Main site: Editor & paginated list of documents |
| `http://localhost:8000/docs/<doc-id>` | View formatted document (with Edit, History & Diff buttons) |
| `http://localhost:8000/docs/<doc-id>/edit` | In-browser editor to save modifications and publish a new version |
| `http://localhost:8000/docs/<doc-id>/history` | Full revision timeline of all document versions |
| `http://localhost:8000/docs/<doc-id>/history/<version>` | View a specific historical version with banner notice |
| `http://localhost:8000/docs/<doc-id>/compare?v1=1&v2=2` | Visual diff comparison highlighting additions & deletions |
| `http://localhost:8000/docs/<doc-id>/raw` | Stream raw plain text directly |

---

## Project Structure

```
opulent/
├── Dockerfile                  # Production container definition using uv & Python 3.13
├── docker-compose.yml          # Postgres 16 + Web app orchestration
├── pyproject.toml              # uv project specification and dependencies
├── uv.lock                     # Deterministic dependency lockfile
├── README.md                   # Documentation
├── src/
│   └── opulent/
│       ├── config.py           # Pydantic BaseSettings (environment variables)
│       ├── database.py         # SQLAlchemy 2.0 async engine & migration runner
│       ├── formatter.py        # Markdown, Pygments syntax highlighting & Bleach sanitizer
│       ├── hasher.py           # Deterministic content hasher & Base62 ID generator
│       ├── main.py             # FastAPI application entrypoint & static mount
│       ├── models.py           # Document & DocumentVersion SQLAlchemy models
│       ├── schemas.py          # Request/response models for editing, history & diffs
│       ├── routes/
│       │   ├── api.py          # REST API endpoints (/api/docs)
│       │   └── web.py          # Web UI routes (view, edit, history, compare)
│       ├── services/
│       │   ├── diff_service.py     # Unified diffing engine & styled HTML renderer
│       │   └── document_service.py # Deduplication, version tracking & querying logic
│       ├── static/
│       │   ├── css/style.css   # Opulent dark theme & diff table stylesheets
│       │   └── js/app.js       # Live stats, tab indentation, clipboard copy
│       └── templates/
│           ├── base.html       # Base layout with navigation and footer
│           ├── index.html      # Editor & paginated document browser
│           ├── view.html       # Formatted document display & action bar
│           ├── edit.html       # Document modification editor
│           ├── history.html    # Version timeline & compare launcher
│           ├── compare.html    # Visual diff page with color-coded diff table
│           └── 404.html        # Not found view
└── tests/
    ├── conftest.py                   # In-memory SQLite async fixtures & ASGI test client
    ├── test_api.py                   # REST API full text & raw endpoints
    ├── test_deduplication.py         # Content deduplication & uniqueness tests
    ├── test_edge_cases.py            # Unicode, emojis, tables, language highlighters
    ├── test_formatter.py             # Markdown & Pygments formatting tests
    ├── test_hasher.py                # Hash calculation & Base62 tests
    ├── test_history_and_editing.py   # Editing, version history & comparison tests
    └── test_web.py                   # Browser UI, pagination, and forms
```

---

## License

MIT
