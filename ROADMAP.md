# AI Data Analyst — 开发路线图

> 6 个 Epic，18 个 Feature Branch，18 个 PR。
> 每个 PR 可独立 Review、独立 Merge，main 始终保持可运行。

---

## 开发节奏

```
Week 1:  PR1 ~ PR4  基础设施（项目能启动、数据库能跑）
Week 2:  PR5 ~ PR8  SQL 核心（SQL 能执行且安全）
Week 3:  PR9 ~ PR13  Agent 主链路（Task Analyzer → SQL Generation → Reflection）
Week 4:  PR14 ~ PR16 结果处理（Chart/Insight/Evidence）
Week 5:  PR17 ~ PR18 工程化（评测、日志、部署、README）
```

---

## Epic 1 — 项目基础设施

### PR #1: Backend 初始化 ✅

| 字段 | 内容 |
|------|------|
| **Branch** | `feature/backend-init` |
| **目标** | FastAPI 启动的基础骨架 |
| **文件清单** | `backend/main.py`, `backend/app/__init__.py`, `backend/app/core/config.py`, `backend/requirements.txt`, `backend/.env.example` |
| **交付标准** | `uvicorn app.main:app` 可启动，访问 `/health` 返回 `{"status": "ok"}` |
| **完成日期** | 2026-07-11 |
| **PR** | #1 |

**详细任务**：
- [✔] `backend/` 目录结构搭建
- [✔] `core/config.py`：Pydantic Settings，支持 `.env` 加载（数据库、Redis、LLM 等配置）
- [✔] `main.py`：FastAPI 应用，CORS 中间件，Health Check 路由
- [✔] `requirements.txt`：FastAPI, uvicorn, pydantic-settings, python-dotenv
- [✔] `.env.example`：所有配置项模板（不含真实密钥）

> ⚠️ 不碰数据库、不碰 Agent、不碰前端

---

### PR #2: Frontend 初始化 ✅

| 字段 | 内容 |
|------|------|
| **Branch** | `feature/frontend-init` |
| **目标** | React + Ant Design 项目启动，展示基础页面 |
| **文件清单** | `frontend/` 完整 React 项目 |
| **交付标准** | 打开页面显示 "AI Data Analyst"，有简单的聊天输入框 |
| **完成日期** | 2026-07-11 |
| **PR** | #2 |

**详细任务**：
- [✔] 使用 Vite 初始化 React + TypeScript 项目
- [✔] 安装 Ant Design、ECharts、axios
- [✔] `App.tsx`：基础布局（侧边栏 + 主内容区）
- [✔] `pages/Chat.tsx`：聊天页面（仅有 UI，无后端对接）
- [✔] `services/api.ts`：axios 实例，配置 base URL
- [✔] 代理配置（开发时转发 `/api` 到 FastAPI）

> ⚠️ 不实现聊天逻辑，不连接后端，不做复杂业务

---

### PR #3: Docker Compose ✅

| 字段 | 内容 |
|------|------|
| **Branch** | `feature/docker-compose` |
| **目标** | 一键启动 MySQL + Redis + Backend |
| **文件清单** | `docker-compose.yml`, `backend/Dockerfile` |
| **交付标准** | `docker compose up` 后三个服务均可正常启动 |
| **完成日期** | 2026-07-11 |
| **PR** | #3 |

**详细任务**：
- [✔] `docker-compose.yml`：MySQL 8.0、Redis 7、Backend
- [✔] `backend/Dockerfile`：多阶段构建
- [✔] `.dockerignore`
- [✔] 环境变量映射

> ⚠️ 不包含 Frontend（开发阶段本地启动即可）

---

### PR #4: 数据集初始化 ✅

| 字段 | 内容 |
|------|------|
| **Branch** | `feature/init-dataset` |
| **目标** | Olist 电商数据导入 MySQL |
| **文件清单** | `backend/scripts/init_db.py`, `backend/scripts/schema.sql` |
| **交付标准** | 执行 `python scripts/init_db.py` 后，数据库包含完整 Olist 8 张表及数据 |
| **完成日期** | 2026-07-11 |
| **PR** | #4 |

**详细任务**：
- [✔] `schema.sql`：8 张表建表语句（orders, products, customers, payments, reviews, order_items, sellers, product_category）
- [✔] `init_db.py`：幂等初始化脚本（DROP → CREATE → INSERT → 校验）
- [✔] 中文注释
- [✔] 创建只读用户 `analyst_ro`

> ⚠️ 不涉及 Agent、不涉及 API、纯粹的数据库初始化

---

## Epic 2 — 数据访问层

### PR #5: Database 核心 ✅

| 字段 | 内容 |
|------|------|
| **Branch** | `feature/database` |
| **目标** | 异步数据库连接管理 |
| **文件清单** | `backend/app/core/database.py`, `backend/app/core/redis.py` |
| **交付标准** | 单元测试可通过 `db.execute("SELECT 1")` |
| **完成日期** | 2026-07-11 |
| **PR** | #5 |

**详细任务**：
- [✔] `core/database.py`：`Database` 类，异步引擎 + Session 管理
- [✔] `core/redis.py`：`RedisClient` 类，基础 get/set/delete
- [✔] 连接池配置 + 健康检查
- [✔] 单元测试

> ⚠️ 不写业务逻辑、不写 Schema、不写 Agent

---

### PR #6: Schema Repository ✅

| 字段 | 内容 |
|------|------|
| **Branch** | `feature/schema-repository` |
| **目标** | 从 MySQL 读取表结构信息 |
| **文件清单** | `backend/app/repositories/schema_repository.py` |
| **交付标准** | `get_tables()` 返回所有表名和注释；`get_columns('orders')` 返回字段名、类型、注释 |
| **完成日期** | 2026-07-11 |
| **PR** | #6 |

**详细任务**：
- [✔] `get_tables()` — 查询 `information_schema.tables`
- [✔] `get_columns(table)` — 查询 `information_schema.columns`
- [✔] `get_foreign_keys()` — 查询 `information_schema.key_column_usage`
- [✔] `get_sample_rows(table, n=3)` — 获取示例数据
- [✔] 单元测试

---

### PR #7: SQL Executor

| 字段 | 内容 |
|------|------|
| **Branch** | `feature/sql-executor` |
| **目标** | 安全执行 SQL 并返回统一 QueryResult |
| **文件清单** | `backend/app/tools/sql_executor.py`, `backend/app/models/query.py` |
| **交付标准** | `executor.execute("SELECT * FROM orders LIMIT 5")` 返回 `QueryResult` |

**详细任务**：
- [✔] `models/query.py`：`QueryResult(columns, rows, truncated, elapsed_ms)` — Pydantic BaseModel
- [✔] `SafeExecutor` 类，接收已校验的 SQL
- [✔] 超时控制（asyncio.timeout，来自 config `SQL_TIMEOUT`）
- [✔] 行数限制（fetchmany(max_rows+1)，来自 config `SQL_MAX_ROWS`）
- [✔] 截断通知（fetch 到 max_rows+1 条时 truncated=True）
- [✔] 执行时间计量（elapsed_ms，float）
- [✔] 异常包装（DatabaseError / TimeoutError / ExecutionError）
- [✔] 单元测试

> ⚠️ 不做 SQL 校验（那是 Validator 的事），不做 Agent，不修改 Database

---

## Epic 3 — SQL Core

### PR #8: SQL Validator

| 字段 | 内容 |
|------|------|
| **Branch** | `feature/sql-validator` |
| **目标** | sqlglot AST 校验，阻断非 SELECT |
| **文件清单** | `backend/app/tools/sql_validator.py` |
| **交付标准** | `validate("SELECT * FROM orders")` → 通过；`validate("DROP TABLE orders")` → 拒绝 |

**详细任务**：
- [ ] 使用 sqlglot 解析 AST
- [ ] 阻断所有非 SELECT 语句（INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE）
- [ ] 递归检查子查询中是否有写入操作
- [ ] 危险模式检测：无 WHERE 全表扫描、CROSS JOIN、左模糊 LIKE、ORDER BY RAND()
- [ ] 返回结构化校验结果：`ValidationResult(passed, risk_level, warnings)`
- [ ] 单元测试

> ⚠️ 不负责执行 SQL，不负责生成 SQL

---

### PR #9: Task Analyzer

| 字段 | 内容 |
|------|------|
| **Branch** | `feature/task-analyzer` |
| **目标** | 分析用户问题，输出结构化任务计划 |
| **文件清单** | `backend/app/services/task_analyzer.py`, `backend/prompts/sql_agent/task_analyzer.md` |
| **交付标准** | 输入"最近30天各品类销售额趋势" → 输出 `{task_type, metrics, dimensions, requires_chart}` |

**详细任务**：
- [ ] 编写 Prompt：`prompts/sql_agent/task_analyzer.md`
- [ ] `TaskAnalyzer.analyze(question, history)` → 调用 LLM → 输出结构化 JSON
- [ ] Pydantic 模型：`TaskPlan(task_type, time_range, metrics, dimensions, requires_chart, requires_insight)`
- [ ] 单元测试（Mock LLM）

> ⚠️ 不生成 SQL，不连接数据库，纯粹的 LLM + 结构化输出

---

### PR #10: SQL Generation

| 字段 | 内容 |
|------|------|
| **Branch** | `feature/sql-generation` |
| **目标** | 根据 Schema Context + 用户问题，生成 SQL |
| **文件清单** | `backend/app/agents/sql_agent.py`（部分），`backend/prompts/sql_agent/sql_generation.md` |
| **交付标准** | LLM 能根据 Schema 信息生成可执行的 SELECT 语句 |

**详细任务**：
- [ ] 编写 Prompt：`prompts/sql_agent/sql_generation.md`
- [ ] SQL 生成的 LLM 调用逻辑
- [ ] 将 Schema Context 拼入 Prompt
- [ ] 单元测试（Mock LLM，验证生成的 SQL 语法正确）

> ⚠️ 不执行 SQL，不做反思循环，不涉及 Task Analyzer 集成

---

## Epic 4 — Schema Retrieval（亮点模块）

### PR #11: Schema Index

| 字段 | 内容 |
|------|------|
| **Branch** | `feature/schema-index` |
| **目标** | 构建 FAISS 向量索引 |
| **文件清单** | `backend/app/schemas/schema_index.py` |
| **交付标准** | 初始化后 FAISS 索引包含所有表和字段的向量 |

**详细任务**：
- [ ] `SchemaIndex` 类
- [ ] 从 Schema Repository 获取表/字段描述
- [ ] 使用 Embedding Model 生成向量
- [ ] 构建 FAISS 索引（表级 + 字段级）
- [ ] 索引持久化（存本地文件，启动时加载）
- [ ] 单元测试

> ⚠️ 不做检索逻辑，不做 LLM 调用

---

### PR #12: Schema Retriever

| 字段 | 内容 |
|------|------|
| **Branch** | `feature/schema-retriever` |
| **目标** | 根据问题检索相关表结构 |
| **文件清单** | `backend/app/schemas/schema_retriever.py` |
| **交付标准** | 输入"销售额趋势" → 返回 orders, payments, products 的 Schema |

**详细任务**：
- [ ] `SchemaRetriever` 类，注入 `SchemaIndex`
- [ ] 双路召回：FAISS 向量检索 + 关键词匹配
- [ ] FK 关系扩展：加入关联表
- [ ] 构建 `SchemaContext(tables, columns, relationships, sample_data)`
- [ ] 排序去重，限制 Token 数
- [ ] 单元测试

> ⚠️ 不修改 SQL 生成逻辑，不修改 Agent

---

### PR #13: Reflection Loop

| 字段 | 内容 |
|------|------|
| **Branch** | `feature/reflection-loop` |
| **目标** | SQL 执行失败时分类处理并重试 |
| **文件清单** | `backend/app/agents/reflection.py`, `backend/prompts/reflection/error_classifier.md`, `backend/prompts/reflection/sql_fix.md` |
| **交付标准** | 错误的 SQL → 分类 → 修正 → 重新校验 → 重新执行（最多 3 次） |

**详细任务**：
- [ ] `ErrorClassifier`：根据错误信息判断类型
- [ ] `SchemaErrorHandler`：重新检索 Schema → 重新生成
- [ ] `SyntaxErrorHandler`：LLM 直接修正 SQL
- [ ] `AmbiguousHandler`：补充上下文 → 重新生成
- [ ] 集成到 SQL Agent 的 Graph 中

> ⚠️ 不修改 Chat、Tool、Validator

---

## Epic 5 — 结果处理

### PR #14: Chart Tool

| 字段 | 内容 |
|------|------|
| **Branch** | `feature/chart-tool` |
| **目标** | 根据 DataFrame 自动选择图表并生成 ECharts Option |
| **文件清单** | `backend/app/tools/chart.py` |
| **交付标准** | 输入 DataFrame → 输出 `{chart_type, echarts_option}` |

**详细任务**：
- [ ] 特征分析：时间序列、分类对比、占比、相关性、分布
- [ ] 规则引擎决定图表类型
- [ ] 生成 ECharts Option（Python dict）
- [ ] 支持 Line、Bar、Pie、Scatter、Histogram
- [ ] 单元测试

> ⚠️ 不需要 LLM，纯 Python 逻辑

---

### PR #15: Insight Tool

| 字段 | 内容 |
|------|------|
| **Branch** | `feature/insight-tool` |
| **目标** | 对查询结果进行 LLM 总结 |
| **文件清单** | `backend/app/tools/insight.py`, `backend/prompts/tools/insight.md` |
| **交付标准** | 输入 DataFrame + 用户问题 → 输出 1-3 句业务洞察 |

**详细任务**：
- [ ] 编写 Prompt
- [ ] 格式化 DataFrame 为文字摘要
- [ ] LLM 调用的 Summarize 逻辑
- [ ] 单元测试

> ⚠️ 这是一个 LLM 调用，不是 Agent。没有循环、没有工具调用

---

### PR #16: Evidence Analyzer

| 字段 | 内容 |
|------|------|
| **Branch** | `feature/evidence-analyzer` |
| **目标** | 带证据链的数据分析，回答"为什么" |
| **文件清单** | `backend/app/tools/evidence_analyzer.py`, `backend/prompts/tools/evidence_analyzer.md` |
| **交付标准** | 输入"为什么销量下降"→ 输出结构化结论 + 证据链 |

**详细任务**：
- [ ] 编写 Prompt
- [ ] 对比分析逻辑（当前 vs 对比期）
- [ ] 多维交叉验证
- [ ] 结构化输出：`EvidenceReport(conclusion, evidence_chain, suggestions)`
- [ ] 单元测试

---

## Epic 6 — 工程化

### PR #17: Evaluation + Logging

| 字段 | 内容 |
|------|------|
| **Branch** | `feature/eval-logging` |
| **目标** | 评测体系 + 全链路日志 + Trace ID |
| **文件清单** | `backend/evaluation/`, `backend/app/core/logging.py` |
| **交付标准** | `pytest evaluation/benchmark.py` 可运行，日志包含 Trace ID |

**详细任务**：
- [ ] `evaluation/golden_sql.json`：20-30 条标准测试集
- [ ] `evaluation/benchmark.py`：Execution Accuracy、Latency、Retry Count
- [ ] `evaluation/metrics.py`：SQL Match 语义等价判断
- [ ] `core/logging.py`：JSON 结构化日志
- [ ] Trace ID 中间件（每个请求生成唯一 Trace ID）
- [ ] LLM Call ID 追踪

---

### PR #18: README + Docker Release

| 字段 | 内容 |
|------|------|
| **Branch** | `feature/release` |
| **目标** | 项目对外发布 |
| **文件清单** | `README.md`, `docker-compose.prod.yml` |
| **交付标准** | 新用户按 README 操作，5 分钟内可运行完整项目 |

**详细任务**：
- [ ] README：项目介绍 + 架构图 + 流程图 + 快速开始
- [ ] Docker 生产配置
- [ ] Demo GIF 录制
- [ ] 最终代码清理

---

## 给 Claude 的任务模板

每次启动新 PR 时，按此模板描述任务：

```
我们现在在 Branch: feature/{branch-name}
对应 PR: #{PR-number}
目标: {一句话}

要求:
1. 不修改其他模块
2. 不修改 README
3. 不修改 Prompt（除非是本 PR 的职责）
4. 保持 API 不变
5. 添加必要的单元测试
6. 代码符合 Ruff/Black 规范
```

---

## 分支策略

```
main
  └── feature/backend-init        ← PR #1
  └── feature/frontend-init       ← PR #2
  └── feature/docker-compose      ← PR #3
  └── feature/init-dataset        ← PR #4
  └── feature/database            ← PR #5
  └── feature/schema-repository   ← PR #6
  └── feature/sql-executor        ← PR #7
  └── feature/sql-validator       ← PR #8
  └── feature/task-analyzer       ← PR #9
  └── feature/sql-generation      ← PR #10
  └── feature/schema-index        ← PR #11
  └── feature/schema-retriever    ← PR #12
  └── feature/reflection-loop     ← PR #13
  └── feature/chart-tool          ← PR #14
  └── feature/insight-tool        ← PR #15
  └── feature/evidence-analyzer   ← PR #16
  └── feature/eval-logging        ← PR #17
  └── feature/release             ← PR #18
```

每个 Feature Branch 从 `main` 拉出，合并回 `main`。不嵌套。
