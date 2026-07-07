# DevMind AI Multi-Agent Platform - Backend API & Agent Pipeline

The backend of DevMind handles repository analysis using a state machine orchestrated by **LangGraph** and **LangChain**. It fetches repositories, runs parallel intelligence agents, processes code complexity analytics, and indexes files into a local vector store.

---

## 🏗️ Multi-Agent Architecture (Phase 2 Core)

```mermaid
graph TD
    A[Repository Input] --> B[GitHub Parser Service]
    B --> C[Vector Store ChromaDB]
    B --> D[LangGraph Orchestrator]

    D --> E1[Doc Agent]
    D --> E2[Review Agent]
    D --> E3[Q&A Agent]
    D --> E4[Analytics Agent]

    E1 & E2 & E3 & E4 --> F[Results Reducer]
```

### 🤖 Parallel Agent Nodes
1. **Doc Agent:** Auto-generates high-quality markdown READMEs and inline API structure summaries.
2. **Review Agent:** Scans code for anti-patterns, potential security bugs, and design flaws.
3. **Q&A Agent:** Prepares index mappings for interactive, context-aware RAG querying.
4. **Analytics Agent:** Extracts AST-based complexity scores, Lines of Code (LOC) distributions, and class/function density.

---

## 🛠️ Technology Stack & Engine
- **Orchestration:** LangGraph (State Graph) & LangChain
- **Embeddings:** Local CPU-based `sentence-transformers` (`all-MiniLM-L6-v2`)
- **Vector Store:** ChromaDB (Local SQLite-backed persistent client)
- **Programming Language:** Python 3.11+
- **Parsing:** Custom AST parsers (for Python and generic code analysis)

---

## 🚀 Running the Local Pipeline CLI
To test the core LangGraph multi-agent engine locally without the REST API:

```bash
# 1. Activate virtual environment
.venv\Scripts\activate

# 2. Run the test script on a public repository
python backend/scripts/run_pipeline_test.py --repo https://github.com/KennethReitz/envoy
```

---

## 🧪 Unit & Integration Tests
We verify the agents, embeddings, and vector indexing using `pytest`:

```bash
# Run all core pipeline tests
pytest backend/tests/test_github_service.py backend/tests/test_vector_store.py backend/tests/test_graph.py backend/tests/test_analytics.py
```
