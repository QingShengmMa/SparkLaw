<div align="center">

# SparkLaw ⚖️

### 面向中文法律场景的开源 AI 智能体系统

<p>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-0ea5e9.svg" alt="MIT License" /></a>
  <a href="https://github.com/QingShengmMa/SparkLaw/pulls"><img src="https://img.shields.io/badge/PRs-Welcome-22c55e.svg" alt="PRs Welcome" /></a>
  <a href="https://github.com/QingShengmMa/SparkLaw/stargazers"><img src="https://img.shields.io/github/stars/QingShengmMa/SparkLaw?style=social" alt="GitHub Stars" /></a>
  <a href="https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white"><img src="https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="https://img.shields.io/badge/Next.js-Frontend-000000?logo=nextdotjs"><img src="https://img.shields.io/badge/Next.js-Frontend-000000?logo=nextdotjs" alt="Next.js" /></a>
  <a href="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python" /></a>
</p>

[English](./README_EN.md) · 中文

<p align="center">
  <img src="showcase/screenshots/landing.png" alt="SparkLaw Landing" width="100%" />
</p>

</div>

---

## 📌 项目简介

`SparkLaw` 是一个聚焦中文法律场景的开源 AI 项目，围绕三类高价值工作流构建：

- **法律问答（Legal Chat）**：多轮上下文、流式回复、会话记忆
- **合同审查（Contract Review）**：结构化风险识别 + 修改建议
- **模拟法庭（Mock Court）**：多角色对抗推理 + 流式庭审过程

项目目标是提供一套**可运行、可扩展、可二次开发**的法律 AI 工程骨架，而不仅是一个演示页面。
开发者友好：模块化后端 + 独立前端，支持本地/云端模型配置，便于二次开发。

---

## 🧱 技术栈

- Python 3.10+
- FastAPI
- Pydantic
- Uvicorn
- LangChain
- LangGraph
- ChromaDB
- sentence-transformers
- Celery
- Redis
- Next.js 16
- React 18
- TypeScript
- Tailwind CSS
- Zustand
- PyMuPDF
- python-docx
- Docker / docker-compose

---

## 🏗️ 项目架构（关键模块）

```text
SparkLaw/
├─ app/
│  ├─ main.py                          # FastAPI 入口，注册路由与中间件
│  ├─ api/v1/routes/
│  │  ├─ chat.py                       # 法律问答（普通 + SSE）
│  │  ├─ document.py                   # 文档上传、解析、检索
│  │  ├─ tools.py                      # 合同审查、模拟法庭、分析工作流
│  │  └─ legal_tools.py                # 文书起草/证据评估/合规体检/计算器网关
│  ├─ agents/                          # Agent 角色与对话编排
│  ├─ services/                        # 业务核心：审查器、法庭代理、RAG、LLM 工厂
│  ├─ knowledge/                       # 召回、重排、引用与向量存储
│  ├─ tools/calculators/               # 14 类法律计算器策略与工厂调度
│  ├─ core/                            # 配置、日志、记忆管理等基础能力
│  └─ workers/                         # Celery 应用定义
├─ frontend/src/
│  ├─ app/                             # Next.js 路由页面（chat/contract/court/tools...）
│  ├─ components/                      # 业务组件与共享组件
│  ├─ hooks/                           # 自定义 hooks（主题、设置等）
│  └─ store/                           # 前端状态管理
├─ tests/                              # 后端接口与服务测试
├─ eval/                               # 评测数据生成与评估脚本
└─ docker-compose.yml                  # 本地容器化编排
```

### 核心请求链路（简化）

1. 前端页面发起请求（REST / SSE）
2. `api/v1/routes` 进行参数接收与协议转换
3. `services` 触发对应工作流（问答、审查、法庭、工具）
4. `agents + knowledge + tools` 完成推理、检索与计算
5. 结果以结构化 JSON 或流式事件返回前端

---

## 🖼️ 功能预览

<table>
  <tr>
    <td width="50%" valign="top">
      <img src="showcase/screenshots/legal-chat.png" alt="Legal Chat" width="100%" />
      <b>法律问答</b>
    </td>
    <td width="50%" valign="top">
      <img src="showcase/screenshots/contract-review.png" alt="Contract Review" width="100%" />
      <b>合同审查</b>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <img src="showcase/screenshots/legal-calculator.png" alt="Legal Calculator" width="100%" />
      <b>法律计算器</b>
    </td>
    <td width="50%" valign="top">
      <img src="showcase/screenshots/document-drafting.png" alt="Document Drafting" width="100%" />
      <b>文书起草</b>
    </td>
  </tr>
</table>

---

## 🚀 快速开始

### 前置要求

- Python 3.10+
- Node.js 18+
- （可选）Redis 6+
- （可选）Ollama（本地模型模式）

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

### 3) 启动后端

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
# source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4) 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问：`http://localhost:3000`

---

## ⚙️ 关键环境变量说明

| 变量名 | 说明 | 示例 |
|---|---|---|
| `LLM_MODE` | 模型模式：`local` / `cloud` | `cloud` |
| `OPENAI_API_KEY` | 云端模型密钥 | `sk-***` |
| `OPENAI_BASE_URL` | OpenAI 兼容网关 | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | 云端模型名称 | `gpt-4o-mini` |
| `OLLAMA_BASE_URL` | 本地 Ollama 地址 | `http://localhost:11434` |
| `OLLAMA_MODEL` | 本地模型名称 | `qwen2.5:7b` |
| `REDIS_URL` | Redis 主连接 | `redis://localhost:6379/0` |
| `NEXT_PUBLIC_API_URL` | 前端后端地址 | `http://localhost:8000` |

完整配置请参考：`.env.example` 与 `frontend/.env.local.example`。

---

## 🤝 贡献指南

欢迎 Issue / PR！

提交前建议：

1. 确保本地测试通过
2. 描述变更动机与方案
3. 如涉及 UI，附关键截图
4. 保持接口向后兼容或清晰说明 breaking change

详细规则见 [`CONTRIBUTING.md`](./CONTRIBUTING.md)。

---

## ⚠️ 免责声明

SparkLaw 旨在提供法律信息处理与辅助分析能力，不构成律师执业意见，不应直接替代专业法律服务。请在关键法律决策前咨询持证律师。

---

## 📄 License

本项目基于 [MIT License](./LICENSE) 开源。

---

<div align="center">
  <b>如果 SparkLaw 对你有帮助，欢迎点一个 ⭐ Star！</b>
</div>
