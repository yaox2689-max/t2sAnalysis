# t2sAnalysis — AI 数据分析助手

**自然语言 → SQL → 可视化 → 洞察**

上传任意 Excel/CSV 文件或连接 MySQL 数据库，用自然语言提问，AI 自动生成 SQL 查询、ECharts 图表和业务洞察。

## 核心能力

| 能力 | 说明 |
|------|------|
| 自然语言查询 | LangGraph Agent 编排：意图分析 → SQL 生成 → 校验 → 执行 → 自修复 |
| 多数据源 | Excel/CSV 上传 + MySQL 直连，统一 Dataset 抽象 |
| 自动可视化 | 规则引擎选图（Line / Bar / Pie / Scatter / Histogram） |
| 业务洞察 | LLM 总结查询结果，输出可读结论 + 证据分析 |
| 多轮对话 | 自动加载最近 20 条消息作为上下文 |
| SSE 流式 | 实时推送 Agent 每个节点的执行进度 |
| 多用户隔离 | JWT 认证，用户级数据隔离 |
| 查询缓存 | Redis 缓存相同 SQL 结果，1 小时 TTL |
| 链路追踪 | LangSmith 集成（可选），完整 Agent 执行链路可视化 |

## Architecture

```
                         用户提问
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│              AI Reasoning Layer (LangGraph)          │
│                                                     │
│  任务理解 → Schema 检索 → SQL 生成 → 安全校验       │
│       → 执行 → 反思重试（最多 3 次）                 │
│                                                     │
│  Post-tools: 图表 → 洞察 → 证据分析                  │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│          Dataset Intelligence Layer                  │
│                                                     │
│  Dataset Registry — 统一数据目录                     │
│  Schema Profiler — 列级画像 + 语义类型               │
│  Prompt Builder — 按需构建数据上下文                 │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│          Unified Analytics Engine                    │
│                                                     │
│  ExecutorRouter — 自动路由到 DuckDB 或 MySQL         │
│  QueryCache — Redis 缓存（user_id + SQL hash）       │
│  SQL Safety — 写操作阻断 + 超时保护                  │
└────────────────────────┬────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
    DuckDB (嵌入式)              MySQL 直连（外部）
    Excel/CSV 数据               生产数据库
```

## Quick Start

### 前置条件

- Python 3.10+
- Node.js 18+
- MySQL 8.0
- Redis 7（可选，用于查询缓存）
- LLM API Key（[DeepSeek](https://platform.deepseek.com) / OpenAI）

### 方式 1：Docker 一键部署（推荐）

```bash
# 1. 克隆
git clone https://github.com/yaox2689-max/t2sAnalysis.git
cd t2sAnalysis

# 2. 配置
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY（必填）

# 3. 启动（MySQL + Redis + 后端 + 前端）
docker compose up -d

# 4. 打开浏览器
# http://localhost
```

### 方式 2：本地开发

```bash
# 1. 克隆
git clone https://github.com/yaox2689-max/t2sAnalysis.git
cd t2sAnalysis

# 2. 后端依赖（二选一）
cd backend
pip install -r requirements.txt     # pip 方式
# 或
uv sync                             # uv 方式

# 3. 配置
cp ../.env.example .env
# 编辑 .env，至少填入：
#   DB_PASSWORD=你的MySQL密码
#   LLM_API_KEY=你的API Key

# 4. 前端依赖
cd ../frontend
npm install

# 5. 启动（两个终端）
# 终端 1:
cd backend
uvicorn main:app --reload

# 终端 2:
cd frontend
npm run dev

# 6. 打开浏览器
# http://localhost:5173
```

启动后自动完成：
- DuckDB 初始化
- MySQL 业务表创建（users / sessions / messages / datasets / mysql_connections）
- DatasetRegistry 加载 Catalog
- Redis 连接（如可用）

## 使用流程

1. **注册/登录** — 首次使用注册账号
2. **上传数据** — 拖拽或点击上传 Excel/CSV
3. **提问** — 自然语言提问，如"各品牌月度销售额趋势"
4. **查看结果** — SQL + 数据表 + ECharts 图表 + 业务洞察 + 证据分析
5. **（可选）连接 MySQL** — 侧边栏"数据库连接"，输入连接信息，自动发现表

## Configuration

核心环境变量（`.env`）：

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `LLM_API_KEY` | **是** | — | DeepSeek / OpenAI API Key |
| `LLM_MODEL` | — | `deepseek-v4-flash` | 模型名称 |
| `LLM_BASE_URL` | — | `https://api.deepseek.com` | API 端点 |
| `DB_HOST` | — | `localhost` | MySQL 地址 |
| `DB_PASSWORD` | **是** | — | MySQL 密码 |
| `JWT_SECRET_KEY` | **是** | — | JWT 签名密钥（生产环境请更换） |
| `REDIS_HOST` | — | `localhost` | Redis 地址（可选，用于缓存） |
| `LANGSMITH_API_KEY` | — | — | LangSmith API Key（留空不接入） |
| `SQL_TIMEOUT` | — | `10` | SQL 执行超时（秒） |

完整变量见 [`.env.example`](.env.example)。

## API Endpoints

### Auth

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册 → 返回 JWT |
| POST | `/api/auth/login` | 登录 → 返回 JWT |
| GET | `/api/auth/me` | 当前用户信息 |

### Chat

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat` | 发送问题（非流式） |
| POST | `/api/chat/stream` | 发送问题（SSE 流式） |

### Sessions

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/sessions` | 创建会话 |
| GET | `/api/sessions` | 列出会话 |
| GET | `/api/sessions/{id}` | 获取会话消息 |
| DELETE | `/api/sessions/{id}` | 删除会话 |

### Datasets

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/datasets/upload` | 上传 Excel/CSV |
| GET | `/api/datasets?session_id=` | 列出数据集 |
| DELETE | `/api/datasets/{table}` | 删除数据集 |

### Connections

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/connections/test` | 测试 MySQL 连接 |
| POST | `/api/connections` | 保存连接 + 注册表 |
| GET | `/api/connections` | 列出连接 |
| DELETE | `/api/connections/{id}` | 删除连接 |

### System

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── agents/               Agent Pipeline
│   │   │   ├── sql_generator.py  LLM → SQL
│   │   │   ├── reflection.py     错误分类 + 修复策略
│   │   │   └── state.py          AgentState
│   │   ├── api/                  API 路由
│   │   │   ├── auth.py           注册/登录
│   │   │   ├── chat.py           对话 + SSE 流式
│   │   │   ├── connections.py    MySQL 连接管理
│   │   │   └── datasets.py       文件上传
│   │   ├── core/                 基础设施
│   │   │   ├── auth.py           JWT 依赖注入
│   │   │   ├── cache.py          Redis 查询缓存
│   │   │   ├── config.py         Pydantic Settings
│   │   │   ├── database.py       MySQL
│   │   │   ├── deps.py           AppContext 依赖组装
│   │   │   ├── duckdb.py         DuckDB 引擎
│   │   │   ├── redis.py          Redis 客户端
│   │   │   └── tracing.py        Trace ID
│   │   ├── graph/                LangGraph StateGraph
│   │   │   ├── graph.py          图编排
│   │   │   ├── nodes.py          6 个节点
│   │   │   └── routers.py        条件路由
│   │   ├── models/               Pydantic 契约
│   │   ├── services/             业务逻辑
│   │   │   ├── auth_service.py   认证服务
│   │   │   ├── credential_encryption.py  密码加密
│   │   │   ├── dataset_manager.py   Dataset 导入
│   │   │   ├── dataset_registry.py  Dataset Registry
│   │   │   ├── prompt_builder.py    Context Builder
│   │   │   └── task_analyzer.py     意图分析
│   │   ├── tools/                工具
│   │   │   ├── chart.py          自动可视化
│   │   │   ├── duckdb_executor.py  DuckDB 执行器
│   │   │   ├── evidence_analyzer.py 证据分析
│   │   │   ├── executor_router.py  执行器路由
│   │   │   ├── external_db_executor.py  MySQL 执行器
│   │   │   ├── insight.py        业务洞察
│   │   │   ├── sql_safety.py     SQL 写拦截
│   │   │   └── sql_validator.py  SQL 校验
│   │   └── bootstrap.py          系统初始化
│   ├── prompts/                  Prompt 模板
│   ├── evaluation/               Benchmark 评测
│   ├── tests/                    测试（133+）
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── main.py                   FastAPI 入口
├── frontend/
│   ├── src/
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx    认证上下文
│   │   ├── pages/
│   │   │   ├── Chat.tsx          对话（SSE 流式 + 图表 + 洞察）
│   │   │   ├── ConnectDatabase.tsx  MySQL 连接管理
│   │   │   ├── History.tsx       历史会话
│   │   │   ├── Login.tsx         登录/注册
│   │   │   └── Settings.tsx      系统设置
│   │   └── services/api.ts       API 客户端（含 SSE）
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── docker-compose.yml
├── .env.example                  环境变量模板
└── README.md
```

## Tech Stack

| 层 | 技术 |
|---|------|
| Backend | FastAPI + Python 3.10+ |
| Agent | LangGraph |
| LLM | DeepSeek / OpenAI（兼容 API） |
| Analytics | **DuckDB**（嵌入式）+ MySQL 直连 |
| Metadata | MySQL 8.0 |
| Cache | Redis 7（SQL 结果缓存） |
| Auth | JWT + bcrypt |
| Tracing | LangSmith（可选） |
| Frontend | React 18 + TypeScript + Ant Design 5 + ECharts 5 |
| SQL | sqlglot（校验 + AST 解析） |

## Evaluation

```bash
cd backend
python -m evaluation.benchmark
```

Benchmark 已接入真实 LangGraph Agent，运行前需确保 DuckDB 中有测试数据。

## FAQ

**Q: 支持哪些 LLM？**
A: 兼容 OpenAI API 格式的模型均可。默认 DeepSeek，修改 `.env` 中的 `LLM_BASE_URL` 和 `LLM_MODEL` 即可切换。

**Q: 支持哪些文件格式？**
A: `.xlsx`、`.xls`、`.csv`。Excel 默认导入所有 Sheet。

**Q: 如何启用 LangSmith？**
A: 在 `.env` 中填入 `LANGSMITH_API_KEY=你的key`，重启服务即可。留空则不接入。

**Q: Redis 必须安装吗？**
A: 不必须。Redis 用于 SQL 查询缓存，不可用时自动降级（跳过缓存直接执行）。

**Q: MySQL 直连安全吗？**
A: 所有外部数据库连接均为只读，写操作（INSERT/UPDATE/DELETE/DROP）被 sqlglot AST 拦截。连接密码使用 Fernet 对称加密存储。

## License

MIT
