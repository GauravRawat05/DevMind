import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as aioredis
from backend.core.config import settings

logger = logging.getLogger("devmind.database")

# 1. PostgreSQL (SQLAlchemy Async Engine)
# Force asyncpg driver if postgresql:// is passed instead of postgresql+asyncpg://
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

logger.info(f"Initializing async PostgreSQL engine with URL scheme: {db_url.split('@')[-1] if '@' in db_url else db_url}")
engine = create_async_engine(
    db_url,
    pool_pre_ping=True,
    future=True,
    echo=False
)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 2. MongoDB Client
logger.info("Initializing async MongoDB client")
mongo_client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=2000)
# Determine DB name from URI or default to 'devmind'
mongo_db = mongo_client.get_default_database()
if mongo_db is None or mongo_db.name == "admin":
    mongo_db = mongo_client.get_database("devmind")

# 3. Redis Client
logger.info("Initializing async Redis client")
redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=2.0)


# Dependency injection helper for DB sessions
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Connection Verification Helpers
async def check_postgres() -> bool:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"PostgreSQL connection health check failed: {e}")
        return False


async def check_mongodb() -> bool:
    try:
        # The ping command is cheap and does not require auth
        await mongo_client.admin.command('ping')
        return True
    except Exception as e:
        logger.error(f"MongoDB connection health check failed: {e}")
        return False


async def check_redis() -> bool:
    try:
        return await redis_client.ping()
    except Exception as e:
        logger.error(f"Redis connection health check failed: {e}")
        return False
