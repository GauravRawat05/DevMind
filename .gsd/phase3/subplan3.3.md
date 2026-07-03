# Sub-plan 3.3: WebSocket Live Streaming Server

## Objective
Implement WebSocket endpoints in FastAPI to stream agent outputs, progress, and logs in real-time to the frontend.

## Action Plan
1. Create `backend/api/routes/ws.py`.
2. Implement WebSocket route `/ws/{job_id}` that keeps track of active connections.
3. Integrate callbacks inside the LangGraph pipeline/Celery task that publish updates (partial stream text, agent status changes) to the connected WebSocket client.

## GSD XML Task Definition
```xml
<task type="auto">
  <name>Build WebSocket real-time updates pipeline</name>
  <files>
    - backend/api/routes/ws.py
    - backend/services/celery_tasks.py
  </files>
  <action>
    Create WebSocket endpoint.
    Build message pub-sub mapping mechanism using Redis or simple shared state.
    Broadcast agent step updates through WebSocket.
  </action>
  <verify>
    Use a WebSocket test client (e.g. wscat or python-websocket-client) to connect, trigger a job, and verify real-time status stream.
  </verify>
  <done>
    FastAPI WebSocket streaming handler completed.
  </done>
</task>
```
