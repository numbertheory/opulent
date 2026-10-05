from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
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
    views: int
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
    views: int
    character_count: int
    line_count: int
    url: str


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem]
    total: int
    page: int
    per_page: int
    total_pages: int

