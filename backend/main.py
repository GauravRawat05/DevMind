import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from backend.core.database import check_postgres, check_mongodb, check_redis, engine
from backend.models.pg_models import Base
from backend.api.routes.analyze import router as analyze_router
from backend.api.routes.results import router as results_router
from backend.api.routes.ws import router as ws_router
from backend.api.routes.download import router as download_router
from backend.api.routes.auth import router as auth_router

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("devmind.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables in Neon PostgreSQL if they do not exist
    try:
        logger.info("Starting up FastAPI application. Creating database tables if they do not exist...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("PostgreSQL database tables verified/created successfully.")
    except Exception as exc:
        logger.critical("Failed to create database tables during startup: %s", exc)
    yield
    # Shutdown (no cleanup required for now)


app = FastAPI(
    title="DevMind AI Multi-Agent Platform API",
    description="REST API and WebSocket server for the DevMind Multi-Agent code intelligence platform.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(analyze_router)
app.include_router(results_router)
app.include_router(ws_router)
app.include_router(download_router)
app.include_router(auth_router)


@app.get("/")
async def root():
    return {
        "name": "DevMind API",
        "status": "online",
        "message": "Welcome to the DevMind AI API Platform. Go to /docs for API schema documentation."
    }


@app.get("/health")
async def health_check(response: Response):
    """Integrated Health Check verifying connection to all three databases."""
    postgres_ok = await check_postgres()
    mongodb_ok = await check_mongodb()
    redis_ok = await check_redis()

    all_connected = postgres_ok and mongodb_ok and redis_ok
    if not all_connected:
        response.status_code = 503

    db_status = {
        "postgresql": "connected" if postgres_ok else "disconnected",
        "postgres": "connected" if postgres_ok else "disconnected",
        "mongodb": "connected" if mongodb_ok else "disconnected",
        "redis": "connected" if redis_ok else "disconnected"
    }

    return {
        "status": "healthy" if all_connected else "unhealthy",
        "services": db_status,
        "databases": db_status
    }
