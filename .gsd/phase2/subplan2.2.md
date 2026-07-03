# Sub-plan 2.2: Local Code Semantic Embeddings & ChromaDB Setup

## Objective
Configure a local text embedding service utilizing `sentence-transformers` and set up ChromaDB to store code chunk vector embeddings for RAG semantic search.

## Action Plan
1. Create `backend/services/embedding_service.py` to initialize `sentence-transformers` (e.g. using `all-MiniLM-L6-v2` or `sentence-transformers/all-mpnet-base-v2` for local, fast operations).
2. Create `backend/services/vector_store.py` to configure a local file-based ChromaDB instance.
3. Write indexing functions that take code files, split them into logical chunks, embed them, and save them in ChromaDB.

## GSD XML Task Definition
```xml
<task type="auto">
  <name>Configure local vector search database</name>
  <files>
    - backend/services/embedding_service.py
    - backend/services/vector_store.py
  </files>
  <action>
    Create embedding_service.py to load sentence-transformers.
    Create vector_store.py with ChromaDB integration, document chunking, and search helper methods.
  </action>
  <verify>
    Write a test script to embed a sample code string, store it, search for a semantic phrase, and confirm the document is retrieved.
  </verify>
  <done>
    Vector database and embedding search pipeline completed.
  </done>
</task>
```
