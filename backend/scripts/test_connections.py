import asyncio
import sys
import os

# Ensure the root of the project is in the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.core.config import settings
from backend.core.database import check_postgres, check_mongodb, check_redis


async def run_tests():
    print("=========================================================")
    print("       DevMind Database Connection Verification          ")
    print("=========================================================")

    # Mask passwords for visual output
    def mask_url(url: str) -> str:
        if "@" in url:
            prefix, rest = url.split("://", 1)
            creds, host = rest.split("@", 1)
            masked_creds = ":" + creds.split(":")[-1] if ":" in creds else ""
            return f"{prefix}://***{masked_creds}@{host}"
        return url

    print(f"PostgreSQL URI: {mask_url(settings.DATABASE_URL)}")
    print(f"MongoDB URI:    {mask_url(settings.MONGODB_URL)}")
    print(f"Redis URI:      {mask_url(settings.REDIS_URL)}")
    print("---------------------------------------------------------")
    print("Starting connection checks...")

    pg_task = check_postgres()
    mongo_task = check_mongodb()
    redis_task = check_redis()

    pg_ok, mongo_ok, redis_ok = await asyncio.gather(pg_task, mongo_task, redis_task)

    print(f"PostgreSQL Status: {'[SUCCESS]' if pg_ok else '[FAILED]'}")
    print(f"MongoDB Status:    {'[SUCCESS]' if mongo_ok else '[FAILED]'}")
    print(f"Redis Status:      {'[SUCCESS]' if redis_ok else '[FAILED]'}")
    print("---------------------------------------------------------")

    if pg_ok and mongo_ok and redis_ok:
        print("SUCCESS: ALL DATABASE CONNECTIONS SUCCESSFULLY VERIFIED!")
        return 0
    else:
        print("Warning: One or more database connection tests failed.")
        print("   Make sure you have copied '.env.example' to '.env' and set valid credentials.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_tests())
    sys.exit(exit_code)
