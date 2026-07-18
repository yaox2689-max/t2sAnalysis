"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup / shutdown lifecycle."""
    from app.core.logging import logger

    logger.info({"event": "app_start", "version": settings.APP_VERSION})
    yield
    logger.info({"event": "app_shutdown"})


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ─────────────────────────────────────────────
from app.api.chat import router as chat_router  # noqa: E402
app.include_router(chat_router)


# ── Health ─────────────────────────────────────────────
@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
