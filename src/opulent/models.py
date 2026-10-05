from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from opulent.formatter import SUPPORTED_FORMATS


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(
        String(255), default="Untitled", nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(
        String(50), default="markdown", nullable=False
    )
    content_hash: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    @property
    def display_format(self) -> str:
        return SUPPORTED_FORMATS.get(self.format, self.format.capitalize())

    @property
    def snippet(self) -> str:
        """Return the first few lines of content for preview in lists."""
        lines = [line.strip() for line in self.content.splitlines() if line.strip()]
        if not lines:
            return ""
        preview = " ".join(lines[:2])
        if len(preview) > 160:
            return preview[:157] + "..."
        return preview

    @property
    def character_count(self) -> int:
        return len(self.content)

    @property
    def line_count(self) -> int:
        return self.content.count("\n") + (1 if self.content else 0)

    @property
    def word_count(self) -> int:
        return len(self.content.split())
