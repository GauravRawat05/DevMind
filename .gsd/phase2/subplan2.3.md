# Sub-plan 2.3: LangGraph Parallel Agents Orchestration

## Objective
Build the multi-agent engine using LangGraph, defining an Orchestrator Node that distributes work to 4 specialized agents (Doc, Review, Q&A, and Analytics) running in parallel.

## Action Plan
1. Create state container in `backend/agents/graph.py`.
2. Implement agents:
   - `backend/agents/doc_agent.py`: Generates repository READMEs.
   - `backend/agents/review_agent.py`: Performs security and quality review.
   - `backend/agents/qa_agent.py`: Handles RAG answers for questions.
   - `backend/agents/analytics_agent.py`: Pre-processed metric node.
3. Hook them up inside a LangGraph state chart, triggering them simultaneously and gathering results.

## GSD XML Task Definition
```xml
<task type="auto">
  <name>Build LangGraph agent state machine</name>
  <files>
    - backend/agents/graph.py
    - backend/agents/doc_agent.py
    - backend/agents/review_agent.py
    - backend/agents/qa_agent.py
    - backend/agents/analytics_agent.py
  </files>
  <action>
    Define the state shape with fields for repo files, documents, reviews, analytics, and QA answers.
    Initialize doc_agent, review_agent, qa_agent, and analytics_agent as graph nodes.
    Set up parallel routing links and compile the graph.
  </action>
  <verify>
    Execute the compiled graph with dummy repository files and check if all 4 output properties in the state are updated.
  </verify>
  <done>
    Stateful multi-agent LangGraph engine compiled and working.
  </done>
</task>
```
