# Sub-plan 3.1: FastAPI REST API Development

## Objective
Develop FastAPI REST API endpoints that handle repository analysis requests, manage job states, and connect to PostgreSQL/MongoDB databases.

## Action Plan
1. Define PostgreSQL schema in `backend/models/pg_models.py` (Users, Jobs) using SQLAlchemy.
2. Define MongoDB schema in `backend/models/mongo_models.py` (Q&A history, detailed run logs).
3. Build API routes:
   - `POST /analyze` (Receives Repo URL, creates Job ID, returns 202 Accepted)
   - `GET /results/{job_id}` (Returns completed analysis details)

## GSD XML Task Definition
```xml
<task type="auto">
  <name>Build database models and core REST endpoints</name>
  <files>
    - backend/models/pg_models.py
    - backend/models/mongo_models.py
    - backend/api/routes/analyze.py
    - backend/api/routes/results.py
  </files>
  <action>
    Create PostgreSQL schemas for user jobs.
    Create MongoDB schemas for Q&A history.
    Write FastAPI analyze endpoint (adds job to DB) and results endpoint (fetches job details).
  </action>
  <verify>
    Submit a dummy POST request to /analyze and verify a job row is created in Postgres, returning a valid job UUID.
  </verify>
  <done>
    Database connections and REST endpoints integrated.
  </done>
</task>
```
