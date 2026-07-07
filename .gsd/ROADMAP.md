# Project Roadmap

## Phase 1: Environment Setup & Project Foundation
- [x] **Sub-plan 1.1:** Setup project folders, ignore files, and local settings.
- [x] **Sub-plan 1.2:** Configure basic environment variables and verify connections.
- [x] **Sub-plan 1.3:** Setup Python package managers, dependencies, and write simple health check.

## Phase 2: Core Agent Pipeline (LangGraph & LangChain)
- [x] **Sub-plan 2.1:** Implement Github parser service to download public repos.
- [x] **Sub-plan 2.2:** Setup local embedding service with sentence-transformers and ChromaDB.
- [x] **Sub-plan 2.3:** Build LangGraph orchestrator graph with 4 parallel agent nodes.
- [x] **Sub-plan 2.4:** Write AST parser logic in Analytics Agent (Pandas + NumPy complexity metrics).

## Phase 3: Backend API, WebSockets, & Asynchronous Task Queue
- [ ] **Sub-plan 3.1:** Create FastAPI REST endpoints (submit repo, read results).
- [ ] **Sub-plan 3.2:** Configure Redis + Celery task queue for background workers.
- [ ] **Sub-plan 3.3:** Implement WebSockets for streaming agent outputs in real-time.

## Phase 4: Next.js Frontend Development
- [ ] **Sub-plan 4.1:** Setup Next.js app with Vanilla CSS modules.
- [ ] **Sub-plan 4.2:** Create homepage with Repo URL submission.
- [ ] **Sub-plan 4.3:** Build real-time streaming dashboard for the 4 agent results.
- [ ] **Sub-plan 4.4:** Integrate charting dashboard (complexity, LOC tiering).

## Phase 5: Mock S3, Auth, & CI/CD
- [ ] **Sub-plan 5.1:** Add S3 local file manager wrapper.
- [ ] **Sub-plan 5.2:** Add JWT login/register functionality in Postgres.
- [ ] **Sub-plan 5.3:** Create Docker configurations and GitHub Actions workflows.
