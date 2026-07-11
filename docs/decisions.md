# 关键决策记录

> 记录重要技术决策，避免重复讨论。

## ADR-001: 一个 Agent + 多 Tool

| 字段 | 内容 |
|------|------|
| 决策 | SQL Agent 是唯一 Agent，Chart/Insight/Evidence 作为 Tool |
| 理由 | Chart 选图无需 LLM，Insight 是 Summarizer 而非 Agent |
| 后续 | 当 Tool > 10 个时考虑引入 Tool 选择逻辑 |

## ADR-002: LangGraph

| 字段 | 内容 |
|------|------|
| 决策 | 使用 LangGraph 编排 Agent 工作流 |
| 理由 | 原生支持有状态图、Tool 调用、条件路由 |
| 后续 | 锁定 langgraph >= 0.2.0 |

## ADR-003: FAISS + 内存

| 字段 | 内容 |
|------|------|
| 决策 | Schema 索引用 FAISS 本地文件 + 内存加载 |
| 理由 | 数据量小，无需 Redis Stack |
| 后续 | 多实例部署时考虑独立向量数据库 |

## ADR-004: sqlglot

| 字段 | 内容 |
|------|------|
| 决策 | 使用 sqlglot 做 SQL AST 分析和安全校验 |
| 理由 | 纯 Python、多方言支持、AST 操作灵活 |

## ADR-005: 异步 SQLAlchemy + aiomysql

| 字段 | 内容 |
|------|------|
| 决策 | 异步 SQLAlchemy 2.0 + aiomysql |
| 理由 | 与 FastAPI 异步架构一致 |

## ADR-006: 分支策略

| 字段 | 内容 |
|------|------|
| 决策 | 每个 Feature Branch 从 main 拉出，合并回 main，不嵌套 |
| 理由 | 历史清晰，独立 Review，单独回滚 |

## ADR-007: Pydantic Settings

| 字段 | 内容 |
|------|------|
| 决策 | Pydantic Settings v2 管理配置，支持 .env |
| 理由 | 类型安全、自动验证、IDE 补全 |

## ADR-008: Ruff + Black

| 字段 | 内容 |
|------|------|
| 决策 | Ruff lint + Black 格式化 |
| 理由 | Ruff 速度极快（Rust），Black 保证一致性 |
