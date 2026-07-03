# Sub-plan 3.2: Celery Background Task Queue Setup

## Objective
Configure Celery with Redis as the broker to process repository analysis jobs asynchronously, ensuring the FastAPI API remains responsive under load.

## Action Plan
1. Create `backend/services/celery_tasks.py` initializing the Celery app with Redis broker URLs.
2. Define a Celery task `analyze_repo_task(job_id, repo_url)` that executes the LangGraph multi-agent pipeline.
3. Update the `POST /analyze` API route to queue this task asynchronously.

## GSD XML Task Definition
```xml
<task type="auto">
  <name>Configure Celery background execution queue</name>
  <files>
    - backend/services/celery_tasks.py
    - backend/api/routes/analyze.py
  </files>
  <action>
    Initialize Celery client pointing to Upstash Redis.
    Define analyze_repo_task to invoke LangGraph.
    Update FastAPI analyze endpoint to dispatch task via delay().
  </action>
  <verify>
    Run celery worker command, trigger analysis via POST request, and confirm task execution output in Celery logs.
  </verify>
  <done>
    Celery background worker queue active and processing jobs.
  </done>
</task>
```
