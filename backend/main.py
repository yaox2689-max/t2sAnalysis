"""FastAPI application entry point."""

# ── Must be first: force httpx to bypass Windows proxy ──
import os
os.environ.setdefault("no_proxy", "*")
os.environ.setdefault("NO_PROXY", "*")

# Monkey-patch httpx transport to not use proxy
import httpx._transports.default
_orig_transport = httpx._transports.default.AsyncHTTPTransport
class _PatchedTransport(_orig_transport):
    def __init__(self, *args, **kwargs):
        kwargs["proxy"] = None
        super().__init__(*args, **kwargs)
httpx._transports.default.AsyncHTTPTransport = _PatchedTransport

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup / shutdown lifecycle."""
    from app.core.logging import logger

    logger.info({"event": "app_start", "version": settings.APP_VERSION})
    yield
    # Clean up connections on shutdown
    from app.core.database import db
    if db.is_initialized:
        await db.close()
    from app.core.redis import redis_client
    await redis_client.close()
    logger.info({"event": "app_shutdown"})


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    lifespan=lifespan,
)

# ── Rate Limiting ─────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ───────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Routes ─────────────────────────────────────────────
from app.api.auth import router as auth_router  # noqa: E402
from app.api.chat import router as chat_router  # noqa: E402
from app.api.connections import router as connections_router  # noqa: E402
from app.api.datasets import router as datasets_router  # noqa: E402
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(connections_router)
app.include_router(datasets_router)


# ── Health ─────────────────────────────────────────────
@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
