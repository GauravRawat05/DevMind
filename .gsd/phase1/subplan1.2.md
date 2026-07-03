# Sub-plan 1.2: Environment Configurations & Cloud Database Connection Verification

## Objective
Create the environment variable configuration template and write helper scripts to verify successful connections to the cloud databases (Neon PostgreSQL, MongoDB Atlas, Upstash Redis).

## Action Plan
1. Create a root-level `.env.example` containing placeholders for:
   - `NEON_DATABASE_URL` (Neon PostgreSQL connection string)
   - `MONGO_URI` (MongoDB Atlas connection string)
   - `REDIS_URL` (Upstash Redis URL)
   - `GROQ_API_KEY` (Groq LLM key)
   - `OPENROUTER_API_KEY` (OpenRouter LLM key)
2. Create a test script `backend/scripts/test_connections.py` that uses:
   - `psycopg2` or `asyncpg` to test Neon Postgres connection.
   - `pymongo` or `motor` to test MongoDB Atlas connection.
   - `redis-py` to test Upstash Redis connection.

## GSD XML Task Definition
```xml
<task type="auto">
  <name>Configure env and test cloud connections</name>
  <files>
    - .env.example
    - backend/scripts/test_connections.py
  </files>
  <action>
    Create .env.example with database and API key placeholders.
    Write a Python connection test script that attempts to connect to PostgreSQL, MongoDB, and Redis and print status logs.
  </action>
  <verify>
    Execute Python test script and confirm it reports successful connection logs.
  </verify>
  <done>
    Environment variables mapped and cloud connection verification script completed.
  </done>
</task>
```
