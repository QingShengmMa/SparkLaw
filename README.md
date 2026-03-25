<div align="center">
  <img src="showcase/branding/sparklaw-logo.png" alt="SparkLaw Logo" width="120" />

# SparkLaw

### 开源 AI 法律智能体

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

## 简介

SparkLaw 是一个面向中文法律场景的开源 AI 系统，聚焦“法律问答、结构化法律工具、模拟法庭推演”三条核心链路。  
它通过大模型 + RAG + 流式交互，将法律知识检索、案件分析和对抗式论证整合为一个可落地的开发者项目。  
目标不是堆砌概念，而是提供可运行、可扩展、可二次开发的开源法律 AI 基础设施。

---

## ✨ 核心特性矩阵

<table>
  <tr>
    <td width="50%" valign="top">
      <img src="showcase/screenshots/legal-chat.png" alt="Legal Chat" width="100%" />
      <b>普法问答</b><br>
      支持多轮上下文、流式响应与会话记忆，适合法律咨询、条文解释与场景化问答。
    </td>
    <td width="50%" valign="top">
      <img src="showcase/screenshots/contract-review.png" alt="Contract Review" width="100%" />
      <b>合同审查</b><br>
      基于结构化流程识别风险条款，输出风险等级、问题分析与可执行修改建议。
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <img src="showcase/screenshots/legal-calculator.png" alt="Legal Calculator" width="100%" />
      <b>法律计算器</b><br>
      覆盖诉讼费、补偿金、利息等常用计算场景，参数化输入、结果可追溯。
    </td>
    <td width="50%" valign="top">
      <img src="showcase/screenshots/document-drafting.png" alt="Document Drafting" width="100%" />
      <b>文书起草</b><br>
      基于模板与指令生成文书草稿，支持 AI 续写、改写与法律表达优化。
    </td>
  </tr>
</table>

---

## 🧱 技术架构

- ⚛️ **Frontend**: Next.js 16, TypeScript, Tailwind CSS  
- ⚡ **Backend**: FastAPI, Pydantic, SSE  
- 🦜 **AI / LLM Orchestration**: LangChain, LangGraph, ReAct  
- 🗄️ **Infrastructure**: ChromaDB, Redis, Celery

---

## 🚀 快速开始

### 1) 克隆项目

```bash
git clone https://github.com/QingShengmMa/SparkLaw.git
cd SparkLaw
```

### 2) 配置环境变量

```bash
# backend
cp .env.example .env

# frontend
cd frontend
cp .env.local.example .env.local
cd ..
```

### 3) 启动后端（Python / FastAPI）

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
# source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4) 启动前端（Node / Next.js）

```bash
cd frontend
npm install
npm run dev
```

访问：`http://localhost:3000`

### 5) （可选）启动异步 Worker

```bash
celery -A app.workers.celery_app worker --loglevel=info
```

### 6) 项目结构（极简）

```text
SparkLaw/
├─ app/                    # FastAPI backend
├─ frontend/               # Next.js frontend
├─ showcase/               # README assets
├─ requirements.txt
└─ README.md
```

---

## 🤝 Contributing

欢迎 Issue 与 PR。建议在提交前附上：变更说明、测试方式、关键截图（如涉及 UI）。  
详细规则见 [`CONTRIBUTING.md`](./CONTRIBUTING.md)。

## 📄 License

本项目基于 [MIT License](./LICENSE) 开源。

---

<div align="center">
  <b>如果 SparkLaw 对你有帮助，欢迎点一个 ⭐ Star。</b>
</div>
