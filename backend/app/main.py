from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config import get_settings
from app.cache.database import init_db, close_db
from app.api.routes import router as api_router
from app.tasks.scheduler import start_scheduler, stop_scheduler


structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("starting_up", log_level=settings.log_level)
    await init_db()
    start_scheduler()
    yield
    logger.info("shutting_down")
    stop_scheduler()
    await close_db()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="GitHub Profile Filter API",
        version="0.1.0",
        description="Internal tool for recruiters to filter GitHub profiles by technical criteria",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["X-API-Key", "Content-Type"],
    )

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health")
    async def health():
        from app.cache.repository import get_cache_stats
        stats = await get_cache_stats()
        return {
            "status": "ok",
            "cache_users": stats["users"],
            "cache_repos": stats["repos"],
            "cache_contributions": stats["contributions"],
        }

    return app


app = create_app()