# SPECification: DevMind AI Multi-Agent Platform

## 1. Project Vision & Goals
DevMind is an AI-powered Multi-Agent Code Intelligence Platform that enables developers to analyze public GitHub repositories. By running specialized LangGraph agents in parallel, it streams documentation, reviews code smells, answers codebase questions, and charts complexity metrics.

The project is built to demonstrate full-stack AI engineering, database integration, containerization, real-time WebSockets, and asynchronous task queues.

---

## 2. Target Audience & Features
- **Target Audience:** Developers onboarding to new projects, open-source maintainers, and portfolio reviewers evaluating modern AI systems.
- **Core Features (P0):**
  - **GitHub Repo Fetcher:** Downloads public repositories for analysis.
  - **Doc Agent:** Auto-generates README.md and inline API documentation.
  - **Review Agent:** Identifies code smells, security flaws, and syntax errors.
  - **Q&A Agent:** RAG-powered chatbot answering natural language questions about the code.
  - **Analytics Agent:** Extracts AST complexity metrics, file sizes, and dependency graphs.
  - **WebSocket Streaming:** Streams agent outputs to the client in real-time.
  - **Next.js UI:** A high-end dashboard built with Vanilla CSS / CSS Modules.

---

## 3. Technology Stack & Hosting (Cloud Free-Tier)
- **Backend:** FastAPI (Python), SQLAlchemy ORM, LangGraph, LangChain, Celery.
- **LLM / Inference:** Groq + OpenRouter (Free tier models).
- **Embeddings:** Local `sentence-transformers` (CodeBERT-based if possible) to search codebase chunks.
- **Databases (Cloud hosted):**
  - Neon PostgreSQL (User data, analysis jobs, code reviews)
  - MongoDB Atlas (Q&A history, detailed agent runs logs)
  - Upstash Redis (Celery broker, caching)
- **Vector Store:** ChromaDB (Local file-based store).
- **Frontend:** Next.js (React) using Vanilla CSS.
- **Mock Services:** Local file system mimicking AWS S3 storage.
- **Containerization:** Docker & Docker Compose.

---

## 4. Status
- **Status:** ACTIVE (Phase 1 completed, executing Phase 2)
