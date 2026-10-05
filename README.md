# Opulent 💎

**Opulent** is a modern, frictionless pastebin and text document web service written in Python. It allows users to compose, format, and share text documents directly within the browser without requiring any login.

Every document receives its own distinct URL formatted as `http://opulent-url/docs/<doc-id>`, powered by a deterministic content-addressable identifier that prevents redundant duplicates. An intuitive REST API allows automated full-text retrieval and creation.

---

## Features

- **No Authentication Required**: Immediate, pastebin-style publishing with zero login friction.
- **Smart Deduplication**: The `doc-id` is generated deterministically from the document's content, title, and format using SHA-256 hash slicing in Base62. Identical submissions automatically resolve to the existing document's URL without polluting the database with duplicates.
- **Rich Formatting & Syntax Highlighting**:
  - **Markdown**: Full GitHub-flavored Markdown rendering (tables, code blocks, lists, blockquotes) safely sanitized with [Bleach](https://github.com/mozilla/bleach) to prevent XSS.
  - **Code**: Server-side syntax highlighting with line numbering for Python, JavaScript, TypeScript, HTML, CSS, JSON, YAML, SQL, Shell/Bash, Go, Rust, Java, C/C++, Dockerfile, and XML via [Pygments](https://pygments.org/).
  - **Plain Text**: Monospace layout with line numbers and safe HTML escaping.
- **Paginated Document Explorer**: The homepage displays an editor alongside a paginated list of all published documents with snippet previews, stats, and navigation controls.
- **Full-Text REST API**: JSON endpoints for publishing and fetching full document details, plus dedicated raw text endpoints (`/api/docs/<doc-id>/raw` and `/docs/<doc-id>/raw`) for `curl` and CLI workflows.
- **Modern Opulent Theme**: Obsidian and warm-gold dark aesthetic with responsive design, keyboard shortcuts (`Ctrl+Enter` to submit, `Tab` indentation in the editor), and clipboard copy helpers.
- **Containerized Orchestration**: Production-ready `Dockerfile` and `docker-compose.yml` bundling the FastAPI service and PostgreSQL 16 with health checks and persistent volume storage.
- **Fast Package Management**: Managed with [`uv`](https://github.com/astral-sh/uv).

---

## Quick Start with Docker Compose

To launch the entire service (PostgreSQL database + Opulent web app) in Docker containers:

```bash
docker compose up --build
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
   # By default, uses SQLite in local dev or configure DATABASE_URL in .env
   uv run opulent
   ```
   Or directly with Uvicorn:
   ```bash
   uv run uvicorn opulent.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## REST API Reference

### 1. Create a Document
- **Endpoint**: `POST /api/docs`
- **Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "title": "Database Schema Notes",
    "format": "sql",
    "content": "CREATE TABLE users (id SERIAL PRIMARY KEY, username VARCHAR(50));"
  }
  ```
- **Responses**:
  - `201 Created` for newly published documents.
  - `200 OK` if the exact document already exists (with `"is_duplicate": true`).
- **Response Example**:
  ```json
  {
    "id": "eZ9vM8wK1",
    "title": "Database Schema Notes",
    "format": "sql",
    "display_format": "SQL",
    "content": "CREATE TABLE users (id SERIAL PRIMARY KEY, username VARCHAR(50));",
    "created_at": "2026-10-04T23:45:00Z",
    "views": 0,
    "character_count": 68,
    "line_count": 1,
    "word_count": 9,
    "url": "http://localhost:8000/docs/eZ9vM8wK1",
    "raw_url": "http://localhost:8000/docs/eZ9vM8wK1/raw",
    "is_duplicate": false
  }
  ```

### 2. Grab Full Text of a Document (JSON)
- **Endpoint**: `GET /api/docs/{doc-id}`
- **Curl**:
  ```bash
  curl http://localhost:8000/api/docs/eZ9vM8wK1
  ```

### 3. Grab Raw Full Text (Plain Text)
- **Endpoint**: `GET /api/docs/{doc-id}/raw` or `GET /docs/{doc-id}/raw`
- **Curl**:
  ```bash
  curl http://localhost:8000/docs/eZ9vM8wK1/raw
  ```
  *Streams raw text directly with `Content-Type: text/plain; charset=utf-8`.*

### 4. List Documents (Paginated)
- **Endpoint**: `GET /api/docs?page=1&per_page=15`
- **Query Parameters**:
  - `page`: Page number (default: `1`)
  - `per_page`: Number of documents per page (default: `15`, max: `100`)

---

## Deduplication Architecture

When a user posts a document via the web UI or the REST API:
1. **Normalization**: Line endings (`\r\n` to `\n`) and outer whitespace are normalized so minor environment variations don't create false duplicates.
2. **Deterministic Hashing**: A SHA-256 digest is generated from the normalized format, title, and content.
3. **Collision-Resistant ID**: An 8-to-10 character Base62 URL slug is produced from the content hash.
4. **Deduplication Check**:
   - If an identical content hash exists in the database, Opulent returns the existing record's `doc-id` without creating a duplicate row.
   - The web UI automatically redirects the user to the existing URL `http://opulent-url/docs/<doc-id>` with a notice.
   - The REST API responds with `200 OK` and `"is_duplicate": true`.

---

## Project Structure

```
opulent/
├── Dockerfile                  # Production container definition using uv
├── docker-compose.yml          # Postgres 16 + Web app orchestration
├── pyproject.toml              # uv project specification and dependencies
├── uv.lock                     # Deterministic dependency lockfile
├── README.md                   # Documentation
├── src/
│   └── opulent/
│       ├── config.py           # Pydantic BaseSettings (environment variables)
│       ├── database.py         # SQLAlchemy 2.0 async engine & session management
│       ├── formatter.py        # Markdown, Pygments syntax highlighting & Bleach sanitizer
│       ├── hasher.py           # Deterministic content hasher & Base62 ID generator
│       ├── main.py             # FastAPI application entrypoint & static mount
│       ├── models.py           # SQLAlchemy Document ORM model
│       ├── schemas.py          # Pydantic validation and serialization schemas
│       ├── routes/
│       │   ├── api.py          # REST API endpoints (/api/docs)
│       │   └── web.py          # Web UI routes (/, /docs/{id}, /docs/{id}/raw)
│       ├── services/
│       │   └── document_service.py # Deduplication & pagination business logic
│       ├── static/
│       │   ├── css/style.css   # Opulent dark theme stylesheet
│       │   └── js/app.js       # Live stats, tab indentation, clipboard copy
│       └── templates/
│           ├── base.html       # Base layout with navigation and footer
│           ├── index.html      # Editor & paginated document browser
│           ├── view.html       # Formatted document display & action bar
│           └── 404.html        # Not found view
└── tests/
    ├── conftest.py             # In-memory SQLite async fixtures & ASGI test client
    ├── test_api.py             # REST API full text & pagination tests
    ├── test_deduplication.py   # Content deduplication & uniqueness tests
    ├── test_edge_cases.py      # Unicode, emojis, tables, language highlighters
    ├── test_formatter.py       # Markdown & Pygments formatting tests
    ├── test_hasher.py          # Hash calculation & Base62 tests
    └── test_web.py             # Browser UI & routing tests
```

---

## License

MIT
