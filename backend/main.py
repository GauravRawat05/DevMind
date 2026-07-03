import logging
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from backend.core.database import check_postgres, check_mongodb, check_redis

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
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
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "name": "DevMind API",
        "version": "1.0.0",
        "status": "online"
    }


@app.get("/health")
async def health_check(response: Response):
    pg_ok = await check_postgres()
    mongo_ok = await check_mongodb()
    redis_ok = await check_redis()

    overall_ok = pg_ok and mongo_ok and redis_ok

    # If any connection fails, return a 503 Service Unavailable status code
    if not overall_ok:
        response.status_code = 503

    return {
        "status": "healthy" if overall_ok else "degraded",
        "services": {
            "postgresql": "connected" if pg_ok else "disconnected",
            "mongodb": "connected" if mongo_ok else "disconnected",
            "redis": "connected" if redis_ok else "disconnected"
        }
    }
