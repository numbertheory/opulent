from collections.abc import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from opulent.config import get_settings
from opulent.models import Base

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Initialize database tables and apply lightweight non-destructive migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Ensure updated_at column exists on documents table if upgrading from earlier schema
        try:
            # PostgreSQL syntax
            await conn.execute(
                text(
                    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"
                )
            )
        except Exception:
            try:
                # SQLite fallback
                await conn.execute(
                    text(
                        "ALTER TABLE documents ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                    )
                )
            except Exception:
                pass

        # Backfill version 1 for any legacy documents that don't have version records yet
        try:
            await conn.execute(
                text(
                    """
                    INSERT INTO document_versions (document_id, version, title, content, format, content_hash, created_at)
                    SELECT d.id, 1, d.title, d.content, d.format, d.content_hash, d.created_at
                    FROM documents d
                    WHERE NOT EXISTS (
                        SELECT 1 FROM document_versions dv WHERE dv.document_id = d.id
                    );
                    """
                )
            )
        except Exception:
            pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining an asynchronous database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
