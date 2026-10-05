from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    title: str = Field(default="Untitled", max_length=255)
    content: str = Field(..., min_length=1, max_length=1_000_000)
    format: str = Field(default="markdown", max_length=50)


class DocumentUpdate(BaseModel):
    title: str = Field(default="Untitled", max_length=255)
    content: str = Field(..., min_length=1, max_length=1_000_000)
    format: str = Field(default="markdown", max_length=50)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique document ID (doc-id)")
    title: str
    content: str
    format: str
    display_format: str
    created_at: datetime
    updated_at: datetime | None = None
    views: int
    version: int = 1
    version_count: int = 1
    character_count: int
    line_count: int
    word_count: int
    url: str
    raw_url: str
    is_duplicate: bool = False


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique document ID (doc-id)")
    title: str
    format: str
    display_format: str
    snippet: str
    created_at: datetime
    updated_at: datetime | None = None
    views: int
    version_count: int = 1
    character_count: int
    line_count: int
    url: str


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem]
    total: int
    page: int
    per_page: int
    total_pages: int


class DocumentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version: int
    title: str
    format: str
    display_format: str
    content: str
    created_at: datetime
    character_count: int
    line_count: int
    word_count: int
    url: str
    raw_url: str


class DocumentHistoryResponse(BaseModel):
    doc_id: str
    title: str
    current_version: int
    total_versions: int
    versions: list[DocumentVersionResponse]


class DiffLineSchema(BaseModel):
    type: str  # 'equal', 'insert', 'delete'
    old_lineno: int | None = None
    new_lineno: int | None = None
    content: str


class DocumentCompareResponse(BaseModel):
    doc_id: str
    v1: int
    v2: int
    title_v1: str
    title_v2: str
    format_v1: str
    format_v2: str
    additions: int
    deletions: int
    lines: list[DiffLineSchema]
