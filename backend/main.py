import logging
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from backend.core.database import check_postgres, check_mongodb, check_redis
from backend.api.routes.analyze import router as analyze_router
from backend.api.routes.results import router as results_router
from backend.api.routes.ws import router as ws_router

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("devmind.main")


app = FastAPI(
    title="DevMind AI Multi-Agent Platform API",
    description="REST API and WebSocket server for the DevMind Multi-Agent code intelligence platform.",
    version="1.0.0"
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


@app.get("/")
async def root():
    return {
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

    return {
        "status": "healthy" if all_connected else "unhealthy",
        "databases": {
            "postgres": "connected" if postgres_ok else "disconnected",
            "mongodb": "connected" if mongodb_ok else "disconnected",
            "redis": "connected" if redis_ok else "disconnected"
        }
    }
