# Sub-plan 4.3: Real-Time Multi-Agent Streaming Dashboard

## Objective
Build the Next.js analysis dashboard page that connects to the backend WebSocket server and streams individual outputs for the 4 agents in dedicated grid panels.

## Action Plan
1. Create `frontend/app/dashboard/[id]/page.tsx` that extracts the `id` param.
2. Implement WebSocket connection hook (`useWebSocket` or React `useEffect` websocket lifecycle).
3. Create individual components:
   - `frontend/app/components/AgentPanel.tsx` (Card panel showing current task state, logs, and markdown output).
4. Parse streaming chunks and append them to each agent's active panel state in real-time.

## GSD XML Task Definition
```xml
<task type="auto">
  <name>Build live streaming agent panel dashboard</name>
  <files>
    - frontend/app/dashboard/[id]/page.tsx
    - frontend/app/components/AgentPanel.tsx
    - frontend/app/components/AgentPanel.module.css
  </files>
  <action>
    Create dashboard component.
    Create AgentPanel components.
    Implement WebSocket integration to stream and render agent outputs side-by-side.
  </action>
  <verify>
    Verify that incoming WebSocket messages update the corresponding agent card output live in the browser.
  </verify>
  <done>
    Real-time multi-agent dashboard built and tested.
  </done>
</task>
```
