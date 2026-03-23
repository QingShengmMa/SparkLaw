# SparkLaw

An engineering-oriented AI legal assistant for Chinese legal scenarios.

---

## Main Functions

- **Supervisor-based multi-agent orchestration (LangGraph)**  
  A supervisor node dispatches tasks to specialized workers, validates outputs, and supports rework/review loops.

- **Advanced RAG retrieval pipeline**  
  Retrieval path: `Query Rewrite -> Vector Recall Top-15 -> Cross-Encoder Rerank -> Top-3`.

- **FastAPI + SSE streaming**  
  Async backend with real-time status events (`tool_call`, `tool_result`, `final`) for better UX and observability.

- **Celery async processing**  
  Long-running contract review tasks are moved out of request threads via Celery + Redis.

- **Offline evaluation baseline (LLM-as-a-Judge)**  
  `eval/` provides dataset generation, auto-scoring, and Markdown/JSON report output.

---

## Implemented scope (v1.0.0)

### 1) Legal chat with LangGraph ReAct tool loop

Workflow:
- `agent` node: reasoning and tool selection
- `tools` node: actual execution via `ToolNode`
- conditional edge:
  - with `tool_calls` -> `tools`
  - without `tool_calls` -> `END`
- tool outputs are appended as `ToolMessage` for the next reasoning turn
- tool errors are converted to recoverable observations

### 2) Retrieval with Advanced RAG

Current path:

`raw query -> query rewrite -> vector recall (Top-15) -> rerank -> final Top-3`

Key modules:
- `query_rewriter.py`: maps colloquial legal queries into retrieval-friendly legal terms
- `reranker.py`: lightweight local cross-encoder with external API extension point
- `rag_service.py`: orchestrates the full retrieval pipeline and fallback behavior

### 3) Supervisor-style multi-agent analysis

`supervisor_agent.py` introduces dispatch-and-review orchestration:
- Supervisor handles routing and validation
- Workers specialize in legal research, contract analysis, and litigation strategy
- Supervisor can accept, rework, or reassign before finalizing output

### 4) Async processing for long-running tasks

Contract review supports Celery + Redis to avoid blocking request threads.

### 5) Offline evaluation support

`eval/` includes:
- dataset generation
- LLM-as-a-Judge scoring
- markdown/json report generation

---

## Stack

### Backend
- FastAPI
- LangChain + LangGraph
- ChromaDB
- sentence-transformers
- Celery + Redis

### Frontend
- Next.js 14
- TypeScript
- Zustand

---

## Repository layout (core)

```text
app/
  routers/
  services/
    legal_agent.py         # ReAct + ToolNode orchestration
    rag_service.py         # Advanced RAG orchestration
    retrieval/
      query_rewriter.py
      reranker.py
    supervisor_agent.py
    multimodal_contract_reviewer.py
  core/

frontend/src/
  app/
  components/
  lib/api.ts
  store/chatStore.ts

eval/
  generate_eval_dataset.py
  run_evaluation.py
```

---

## Quick start

### Backend

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

### Optional async worker

```bash
celery -A app.celery_app.celery_app worker --loglevel=info
```

---

## Selected API endpoints

- `POST /api/legal/chat`
- `POST /api/legal/chat/stream`
- `POST /api/document/upload`
- `POST /api/document/retrieve`
- `POST /api/analysis/*`

OpenAPI docs: `http://localhost:8000/docs`

---

## Engineering notes

- First startup may download embedding/reranker model files.
- Retrieval remains available when reranker is unavailable (fallback to vector ranking).
- Current session-state approach optimizes iteration speed; production deployment should externalize persistence.

---

## Practical roadmap

- Hybrid retrieval (BM25 + dense fusion)
- Structured supervisor evaluation rubric
- CI regression gate for evaluation metrics
- Stronger state persistence and observability

---

## License

MIT
