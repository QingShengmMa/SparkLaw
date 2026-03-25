<div align="center">
  <img src="showcase/branding/sparklaw-logo.png" alt="SparkLaw Logo" width="120" />

# SparkLaw

**开源 AI 法律智能体（Legal Agent）**

让法律服务触手可及：**普法问答 · 法律工具 · 模拟法庭**

[English](./README_EN.md) · 中文

<p>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-0ea5e9.svg" alt="MIT License" /></a>
  <a href="https://github.com/QingShengmMa/SparkLaw/pulls"><img src="https://img.shields.io/badge/PRs-Welcome-22c55e.svg" alt="PRs Welcome" /></a>
  <a href="https://github.com/QingShengmMa/SparkLaw/stargazers"><img src="https://img.shields.io/github/stars/QingShengmMa/SparkLaw?style=social" alt="GitHub Stars" /></a>
  <a href="https://github.com/QingShengmMa/SparkLaw/issues"><img src="https://img.shields.io/github/issues/QingShengmMa/SparkLaw" alt="Issues" /></a>
</p>
</div>

---

## 界面展示

### 1) 首页（Landing）

<p align="center">
  <img src="showcase/screenshots/landing.png" alt="SparkLaw Landing" width="92%" />
</p>

### 2) 普法问答

<p align="center">
  <img src="showcase/screenshots/legal-chat.png" alt="SparkLaw Legal Chat" width="92%" />
</p>

### 3) 合同审查

<p align="center">
  <img src="showcase/screenshots/contract-review.png" alt="SparkLaw Contract Review" width="92%" />
</p>

### 4) 法律计算器

<p align="center">
  <img src="showcase/screenshots/legal-calculator.png" alt="SparkLaw Legal Calculator" width="92%" />
</p>

### 5) 文书起草

<p align="center">
  <img src="showcase/screenshots/document-drafting.png" alt="SparkLaw Document Drafting" width="92%" />
</p>

### 模拟法庭（GIF）

<p align="center">
  <img src="showcase/gifs/mock-court.gif" alt="SparkLaw Mock Court GIF" width="92%" />
</p>

---

## 核心功能

- **普法问答**：面向中文法律场景的多轮对话与法律检索辅助。
- **法律工具**：合同审查、文书起草、诉讼费与赔偿金等结构化工具。
- **模拟法庭**：原告/被告/法官多角色推演与庭审复盘。

---

## 快速开始

### 1) 环境要求
- Python 3.10+
- Node.js 18+
- npm 9+
- Redis（可选，用于异步任务）

### 2) 克隆项目

```bash
git clone https://github.com/QingShengmMa/SparkLaw.git
cd SparkLaw
```

### 3) 启动后端（FastAPI）

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

### 4) 启动前端（Next.js）

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

访问：`http://localhost:3000`

### 5) 可选：启动异步 Worker

```bash
celery -A app.workers.celery_app worker --loglevel=info
```

---

## 环境变量（最小示例）

后端 `.env`：

```bash
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
REDIS_URL=redis://localhost:6379/0
```

前端 `frontend/.env.local`：

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 技术栈

| 层 | 技术 |
|---|---|
| Frontend | Next.js 16, TypeScript, Tailwind CSS |
| Backend | FastAPI, Pydantic, SSE |
| Agent / Orchestration | LangChain, LangGraph |
| Retrieval | ChromaDB, RAG, Reranker |
| Async | Celery, Redis |

---

## 项目结构（简版）

```text
SparkLaw/
├─ app/                          # FastAPI 后端
│  ├─ api/v1/routes/             # 路由
│  ├─ services/                  # 业务服务（审查/法庭/问答）
│  ├─ tools/calculators/         # 法律计算器策略
│  └─ orchestration/workflows/   # LangGraph 工作流
├─ frontend/                     # Next.js 前端
│  └─ src/app/                   # 页面路由
├─ showcase/                     # README 展示素材
├─ README.md
└─ README_EN.md
```

---

## 贡献指南

欢迎 Issue 与 PR！

1. Fork 本仓库
2. 新建分支：`feat/xxx` 或 `fix/xxx`
3. 提交并推送
4. 发起 Pull Request

详细说明：`CONTRIBUTING.md`

---

## License

本项目采用 [MIT License](./LICENSE)。

<div align="center">
如果这个项目对你有帮助，欢迎点一个 ⭐
</div>
