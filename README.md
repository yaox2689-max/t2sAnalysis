# Dataset Intelligence Platform

**Natural Language → Dataset → SQL → Insight**

AI doesn't query databases directly.
It reasons over Dataset Registry, where schema, semantics and metadata are already understood.

## Why Dataset Intelligence?

**一个抽象 — Dataset**
所有数据源进入系统后统一成为 Dataset。Excel、CSV、数据库、API — AI 不需要学习不同数据源格式。

**一个认知层 — Dataset Registry**
Registry 不只是目录。它包含 Schema、语义类型、统计信息和示例数据，构成 AI 理解数据的完整上下文。

**一个执行引擎 — DuckDB**
所有分析查询统一执行，AI 无需区分数据来源。

## Architecture

```
                          用户提问
                             │
                             ▼
 ┌─────────────────────────────────────────────────────┐
 │              AI Reasoning Layer                      │
 │                                                     │
 │   任务理解 → SQL 规划 → 安全校验 → 自动修复          │
 │                                                     │
 └────────────────────────▲────────────────────────────┘
                          │
                          │  AI 的认知边界
                          │
 ┌─────────────────────────────────────────────────────┐
 │          Dataset Intelligence Layer                  │
 │                                                     │
 │   Dataset Registry — 统一数据目录                    │
 │   Semantic Schema — 列级画像 + 语义类型              │
 │   Data Profile — 统计信息 + 示例值                   │
 │   Context Retrieval — 按需构建数据上下文             │
 │                                                     │
 │   ←—— AI 的语义数据视图 ——→                          │
 │                                                     │
 └────────────────────────▲────────────────────────────┘
                          │
 ┌─────────────────────────────────────────────────────┐
 │          Unified Analytics Engine                    │
 │                                                     │
 │                   DuckDB                             │
 │                                                     │
 │   执行 Dataset 查询，返回结果                        │
 │                                                     │
 └────────────────────────▲────────────────────────────┘
                          │
 ┌─────────────────────────────────────────────────────┐
 │               Dataset Sources                       │
 │                                                     │
 │   Excel  |  CSV  |  Database  |  API  |  Future     │
 │                                                     │
 └─────────────────────────────────────────────────────┘

                          元数据
                             │
                             ▼
                      ┌─────────────┐
                      │    MySQL    │
                      │ 会话 / 消息  │
                      │ 数据集目录   │
                      └─────────────┘
```

## Dataset Lifecycle

```
   Upload ──→ Import ──→ Profile ──→ Register ──→ Understand ──→ Query ──→ Insight
                                                                         │
                                                                         ▼
                                                              Dataset = Living Data Asset
```

| 阶段 | 说明 |
|------|------|
| **Upload** | 用户上传 Excel / CSV |
| **Import** | 列名清洗、类型推断、写入 DuckDB |
| **Profile** | 列级统计 + 语义类型（dimension / measure / time） |
| **Register** | 注册到 Dataset Registry，AI 可见 |
| **Understand** | AI 通过 Registry 获取 Schema + 画像 + 示例值 |
| **Query** | AI 生成 SQL，安全执行 |
| **Insight** | 自动可视化 + 业务洞察 |

## Core Capabilities

| 能力 | 说明 |
|------|------|
| Dataset 抽象 | Excel / CSV 统一为 Dataset，一个引擎处理所有数据 |
| 语义画像 | 自动推断列级语义类型（dimension / measure / time） |
| Dataset-aware Agent | LangGraph 编排：意图分析 → SQL 生成 → 校验 → 执行 → 自修复 |
| 安全执行 | 写操作阻断 + 超时保护 + 最多 3 次结构化重试 |
| 自动可视化 | 规则引擎自动选图（Line / Bar / Pie / Scatter / Histogram） |
| 业务洞察 | LLM 总结查询结果，输出可读的业务结论 |
| 全链路可观测 | Trace ID 串联 + JSON 结构化日志 |

## How It Works

### 数据接入

```
Excel / CSV 上传
       │
       ▼
 Dataset Manager — 导入 / 清洗 / 注册
       │
       ▼
 Schema Profiler — 列级统计 + 语义类型推断
       │
       ▼
 Dataset Registry — 注册到统一数据目录
       │
       ▼
 DuckDB + MySQL 元数据
```

### 查询分析

```
用户提问
       │
       ▼
 Task Analyzer — 意图理解 → TaskPlan
       │
       ▼
 Dataset Registry — 检索相关数据集（top-k）
       │
       ▼
 Context Builder — Schema + 画像 + 示例值 → Dataset Context
       │
       ▼
 SQL Generator — LLM 基于 Dataset Context 生成 SQL
       │
       ▼
 安全校验 — 语法检查 + 写操作阻断
       │
       ├── 通过 → DuckDB 执行（超时保护）
       │              │
       │              ├── 成功 → 可视化 + 洞察 → 返回用户
       │              └── 失败 ─┐
       │                       │
       └── 失败 ───────────────┤
                               ▼
                        自动修复（错误分类 + 重试，最多 3 次）
```

## Quick Start（5 分钟）

### 前置条件

- Docker & Docker Compose
- LLM API Key（[DeepSeek](https://platform.deepseek.com) / OpenAI）

### 步骤

```bash
# 1. 克隆
git clone https://github.com/yaox2689-max/t2sAnalysis.git
cd t2sAnalysis

# 2. 配置（唯一必须的步骤）
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY

# 3. 启动后端 + 数据库（自动建表）
docker compose up -d

# 4. 启动前端（另开终端）
cd frontend
npm install
npm run dev

# 5. 打开浏览器
open http://localhost:5173
```

启动后自动完成：
1. DuckDB 初始化（`analysis.duckdb`）
2. MySQL 业务表创建（sessions / messages / datasets）
3. DatasetRegistry 加载 Catalog
4. Context Builder 就绪

### 验证

```bash
curl http://localhost:8000/health
# → {"status": "ok"}
```

## Local Development

```bash
# 方式 1: pip
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# 方式 2: uv
cd backend
uv pip install -e .
uv run uvicorn main:app --reload

# 前端（另开终端）
cd frontend
npm install
npm run dev
```

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── agents/              AI Pipeline
│   │   │   ├── sql_generator.py LLM → SQL
│   │   │   ├── reflection.py    错误分类 + 修复策略
│   │   │   └── state.py         AgentState 统一 Context
│   │   ├── api/                 API 路由
│   │   │   ├── chat.py          聊天 API
│   │   │   └── datasets.py      文件上传 API
│   │   ├── core/                基础设施
│   │   │   ├── config.py        Pydantic Settings
│   │   │   ├── database.py      MySQL（业务元数据）
│   │   │   ├── duckdb.py        DuckDB（分析引擎）
│   │   │   ├── logging.py       JSON 结构化日志
│   │   │   ├── tracing.py       Trace ID 串联
│   │   │   └── prompt_loader.py Prompt 文件管理
│   │   ├── graph/               LangGraph StateGraph
│   │   │   ├── graph.py         图编排
│   │   │   ├── nodes.py         节点实现
│   │   │   └── routers.py       条件路由
│   │   ├── models/              Pydantic 契约
│   │   ├── services/            业务逻辑
│   │   │   ├── dataset_manager.py   Dataset 导入 / 删除
│   │   │   ├── dataset_registry.py  Dataset Registry
│   │   │   ├── prompt_builder.py    Context Builder
│   │   │   └── task_analyzer.py     意图分析
│   │   ├── tools/               工具函数
│   │   │   ├── chart.py         自动可视化 → ECharts
│   │   │   ├── column_cleaner.py 列名清洗
│   │   │   ├── duckdb_executor.py DuckDB 执行器
│   │   │   ├── insight.py       业务洞察
│   │   │   ├── schema_profiler.py 语义画像
│   │   │   └── sql_validator.py  SQL 安全校验
│   │   └── bootstrap.py         系统启动初始化
│   ├── prompts/                 Prompt 模板
│   ├── scripts/
│   │   ├── schema.sql           Olist DDL
│   │   └── schema_datasets.sql  datasets 表 DDL
│   ├── tests/                   测试用例（160+）
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── main.py                  FastAPI 入口
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Chat.tsx         聊天页（拖拽上传 + 图表 + 洞察）
│   │   │   ├── History.tsx      历史会话
│   │   │   └── Settings.tsx     系统设置
│   │   └── services/api.ts      API 客户端
│   └── package.json
├── docker-compose.yml           开发环境
├── docker-compose.prod.yml      生产环境
└── .env.example                 环境变量模板
```

## Configuration

核心环境变量（`.env`）：

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `LLM_API_KEY` | ✅ | — | DeepSeek / OpenAI API Key |
| `LLM_MODEL` | — | `deepseek-chat` | 模型名称 |
| `LLM_BASE_URL` | — | `https://api.deepseek.com` | API 端点 |
| `DB_HOST` | — | `localhost` | MySQL 地址 |
| `DB_PORT` | — | `3307` | MySQL 端口 |
| `REDIS_HOST` | — | `localhost` | Redis 地址 |
| `SQL_TIMEOUT` | — | `10` | SQL 执行超时（秒） |

完整变量见 [`.env.example`](.env.example)。

## API Endpoints

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | 发送问题，返回 SQL + 图表 + 洞察 |
| POST | `/api/sessions` | 创建会话 |
| GET | `/api/sessions` | 列出会话 |
| GET | `/api/sessions/{id}` | 获取会话消息 |
| DELETE | `/api/sessions/{id}` | 删除会话 |
| POST | `/api/datasets/upload` | 上传 Excel/CSV 文件 |
| GET | `/api/datasets?session_id=` | 列出数据集 |
| DELETE | `/api/datasets/{table}` | 删除数据集 |
| GET | `/health` | 健康检查 |

## Tech Stack

| 层 | 技术 |
|---|------|
| Backend | FastAPI + Python 3.9+ |
| Agent | LangGraph |
| LLM | DeepSeek / OpenAI |
| Analytics | **DuckDB**（唯一分析引擎） |
| Business DB | MySQL 8.0（元数据） |
| Cache | Redis 7（Session / Cache） |
| Frontend | React + Ant Design + ECharts |
| SQL Analysis | sqlglot |
| File Parsing | pandas（Excel）/ DuckDB（CSV） |
| Logging | JSON + Trace ID |

## Evaluation

```bash
cd backend
python -m evaluation.benchmark
```

> **注意**: 当前 Benchmark 使用 Mock Agent，尚未接入真实 LangGraph Pipeline。
> 评测框架（metrics + golden dataset）已就绪，待接入真实 Agent 后即可运行端到端评测。

| 指标 | 说明 |
|------|------|
| Task Accuracy | TaskPlan 与预期匹配度 |
| SQL Executable | SQL 是否可执行 |
| SQL Valid | 是否通过 AST 校验 |
| Result Consistency | 结果列是否符合预期 |

## FAQ

**Q: 支持哪些 LLM？**
A: 兼容 OpenAI API 格式的模型均可。默认 DeepSeek，修改 `LLM_BASE_URL` 和 `LLM_MODEL` 即可切换。

**Q: 支持哪些文件格式？**
A: `.xlsx`、`.xls`、`.csv`。Excel 默认导入所有 Sheet，每个 Sheet 生成独立 Dataset。

**Q: 上传的数据安全吗？**
A: 文件名 UUID 重命名存储，SQL 经 sqlglot 校验，写操作被阻断，执行有超时保护。

**Q: 如何添加新的数据源（如 Parquet、API）？**
A: 在 DatasetManager 中新增导入方法，注册到 DatasetRegistry 即可。AI Pipeline 无需修改。

**Q: 需要 GPU 吗？**
A: 不需要。DuckDB 是嵌入式数据库，LLM 调用远程 API。

## License

MIT
