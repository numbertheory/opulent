from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

from opulent.config import get_settings
from opulent.database import init_db
from opulent.routes import api, web

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema on startup
    await init_db()
    yield


settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Opulent - A frictionless pastebin and text document service with formatting & REST API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs-ui",
    openapi_url="/api/openapi.json",
)

# Ensure static folder exists and mount it
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include routes
app.include_router(web.router)
app.include_router(api.router)


@app.get("/healthz", tags=["health"])
async def health_check():
    """Health check endpoint for Docker container orchestration."""
    return {"status": "ok", "app": settings.APP_NAME}


def main():
    """Entry point for running the application directly."""
    uvicorn.run(
        "opulent.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    main()
