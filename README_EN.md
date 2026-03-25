<div align="center">
  <img src="showcase/branding/sparklaw-logo.png" alt="SparkLaw Logo" width="120" />

# SparkLaw

**Open-Source AI Legal Agent**

Legal AI for everyone: **Legal Chat · Legal Tools · Mock Court**

English · [中文](./README.md)

<p>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-0ea5e9.svg" alt="MIT License" /></a>
  <a href="https://github.com/QingShengmMa/SparkLaw/pulls"><img src="https://img.shields.io/badge/PRs-Welcome-22c55e.svg" alt="PRs Welcome" /></a>
  <a href="https://github.com/QingShengmMa/SparkLaw/stargazers"><img src="https://img.shields.io/github/stars/QingShengmMa/SparkLaw?style=social" alt="GitHub Stars" /></a>
  <a href="https://github.com/QingShengmMa/SparkLaw/issues"><img src="https://img.shields.io/github/issues/QingShengmMa/SparkLaw" alt="Issues" /></a>
</p>
</div>

---

## UI Showcase

### 1) Landing

<p align="center">
  <img src="showcase/screenshots/landing.png" alt="SparkLaw Landing" width="92%" />
</p>

### 2) Legal Chat

<p align="center">
  <img src="showcase/screenshots/legal-chat.png" alt="SparkLaw Legal Chat" width="92%" />
</p>

### 3) Contract Review

<p align="center">
  <img src="showcase/screenshots/contract-review.png" alt="SparkLaw Contract Review" width="92%" />
</p>

### 4) Legal Calculator

<p align="center">
  <img src="showcase/screenshots/legal-calculator.png" alt="SparkLaw Legal Calculator" width="92%" />
</p>

### 5) Document Drafting

<p align="center">
  <img src="showcase/screenshots/document-drafting.png" alt="SparkLaw Document Drafting" width="92%" />
</p>

### Mock Court (GIF)

<p align="center">
  <img src="showcase/gifs/mock-court.gif" alt="SparkLaw Mock Court GIF" width="92%" />
</p>

---

## Core Features

- **Legal Chat**: multi-turn legal Q&A for Chinese legal scenarios.
- **Legal Tools**: contract review, document drafting, and legal calculators.
- **Mock Court**: multi-role courtroom simulation with post-hearing review.

---

## Quick Start

### 1) Requirements
- Python 3.10+
- Node.js 18+
- npm 9+
- Redis (optional, for async tasks)

### 2) Clone

```bash
git clone https://github.com/QingShengmMa/SparkLaw.git
cd SparkLaw
```

### 3) Backend (FastAPI)

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
# source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4) Frontend (Next.js)

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open: `http://localhost:3000`

### 5) Optional Worker

```bash
celery -A app.workers.celery_app worker --loglevel=info
```

---

## Environment Variables (Minimal)

Backend `.env`:

```bash
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
REDIS_URL=redis://localhost:6379/0
```

Frontend `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Tech Stack

| Layer | Stack |
|---|---|
| Frontend | Next.js 16, TypeScript, Tailwind CSS |
| Backend | FastAPI, Pydantic, SSE |
| Agent / Orchestration | LangChain, LangGraph |
| Retrieval | ChromaDB, RAG, Reranker |
| Async | Celery, Redis |

---

## Project Structure (Brief)

```text
SparkLaw/
├─ app/                          # FastAPI backend
│  ├─ api/v1/routes/             # routes
│  ├─ services/                  # services (review/court/chat)
│  ├─ tools/calculators/         # calculator strategies
│  └─ orchestration/workflows/   # LangGraph workflows
├─ frontend/                     # Next.js frontend
│  └─ src/app/                   # route pages
├─ showcase/                     # README media assets
├─ README.md
└─ README_EN.md
```

---

## Contributing

Issues and PRs are welcome.

1. Fork this repository
2. Create a branch: `feat/xxx` or `fix/xxx`
3. Commit and push
4. Open a Pull Request

Detailed guide: `CONTRIBUTING.md`

---

## License

Licensed under the [MIT License](./LICENSE).

<div align="center">
If SparkLaw helps you, please consider giving it a ⭐
</div>
