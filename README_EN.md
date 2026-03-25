<div align="center">
  <img src="showcase/branding/sparklaw-logo.png" alt="SparkLaw Logo" width="120" />

# SparkLaw

### An Open-Source AI Legal Agent

<p>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-0ea5e9.svg" alt="MIT License" /></a>
  <a href="https://github.com/QingShengmMa/SparkLaw/pulls"><img src="https://img.shields.io/badge/PRs-Welcome-22c55e.svg" alt="PRs Welcome" /></a>
  <a href="https://github.com/QingShengmMa/SparkLaw/stargazers"><img src="https://img.shields.io/github/stars/QingShengmMa/SparkLaw?style=social" alt="GitHub Stars" /></a>
  <a href="https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white"><img src="https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="https://img.shields.io/badge/Next.js-Frontend-000000?logo=nextdotjs"><img src="https://img.shields.io/badge/Next.js-Frontend-000000?logo=nextdotjs" alt="Next.js" /></a>
</p>

English · [中文](./README.md)
</div>

<p align="center">
  <img src="showcase/gifs/mock-court.gif" alt="SparkLaw Hero - Mock Court" width="100%" />
</p>

---

## Introduction

SparkLaw is an open-source AI system for Chinese legal scenarios, focused on three practical workflows: legal chat, structured legal tools, and mock-court simulation.  
It combines LLMs, RAG, and streaming interaction to unify legal retrieval, case analysis, and adversarial reasoning in one project.  
The goal is not hype—it is a runnable, extensible, and developer-friendly legal AI foundation.

---

## ✨ Feature Matrix

<table>
  <tr>
    <td width="50%" valign="top">
      <img src="showcase/screenshots/legal-chat.png" alt="Legal Chat" width="100%" />
      <b>Legal Chat</b><br>
      Supports multi-turn context, streaming responses, and session memory for practical legal Q&A.
    </td>
    <td width="50%" valign="top">
      <img src="showcase/screenshots/contract-review.png" alt="Contract Review" width="100%" />
      <b>Contract Review</b><br>
      Detects risk clauses with structured outputs: severity, analysis, and actionable revision suggestions.
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <img src="showcase/screenshots/legal-calculator.png" alt="Legal Calculator" width="100%" />
      <b>Legal Calculator</b><br>
      Parameterized calculators for litigation fees, compensation, and interest with traceable outputs.
    </td>
    <td width="50%" valign="top">
      <img src="showcase/screenshots/document-drafting.png" alt="Document Drafting" width="100%" />
      <b>Document Drafting</b><br>
      Template-based legal drafting with AI continuation, rewriting, and refinement out-of-the-box.
    </td>
  </tr>
</table>

---

## 🧱 Tech Stack

- ⚛️ **Frontend**: Next.js 16, TypeScript, Tailwind CSS  
- ⚡ **Backend**: FastAPI, Pydantic, SSE  
- 🦜🔗 **AI / LLM Orchestration**: LangChain, LangGraph, ReAct  
- 🗄️ **Infrastructure**: ChromaDB, Redis, Celery

---

## 🚀 Quick Start

### 1) Clone the repository

```bash
git clone https://github.com/QingShengmMa/SparkLaw.git
cd SparkLaw
```

### 2) Configure environment variables

```bash
# backend
cp .env.example .env

# frontend
cd frontend
cp .env.local.example .env.local
cd ..
```

### 3) Start backend (Python / FastAPI)

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
# source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4) Start frontend (Node / Next.js)

```bash
cd frontend
npm install
npm run dev
```

Open: `http://localhost:3000`

### 5) (Optional) Start async worker

```bash
celery -A app.workers.celery_app worker --loglevel=info
```

### 6) Minimal project structure

```text
SparkLaw/
├─ app/                    # FastAPI backend
├─ frontend/               # Next.js frontend
├─ showcase/               # README assets
├─ requirements.txt
└─ README_EN.md
```

---

## 🤝 Contributing

Issues and PRs are welcome. Please include change summary, test notes, and screenshots for UI updates.  
See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for contribution details.

## 📄 License

Released under the [MIT License](./LICENSE).

---

<div align="center">
  <b>If SparkLaw is useful to you, please consider giving it a ⭐ Star.</b>
</div>
