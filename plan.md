# AI Data Analyst Agent — 项目方案

> 定位：不只做 Text2SQL，而是完整的智能数据分析 Agent。
> 用户提出业务问题 → Agent 理解需求 → 检索相关 Schema → 生成并安全执行 SQL → 可视化 → 给出带证据的业务洞察。

---

## 1. 项目概述

### 核心能力

| 能力 | 说明 |
|------|------|
| 自然语言 → SQL | 用户用中文描述需求，Agent 自动生成正确的 SQL |
| 智能 Schema 检索 | 根据问题自动匹配相关表和字段，而非全量 Schema |
| 多层 SQL 反思 | Parser → Validator → Executor → Error Analyzer 结构化修正 |
| 多工具编排 | SQL 执行、图表生成、数据洞察，统一由 Agent 按需调用 |
| 带证据的分析 | Evidence Analyzer 给出结论时引用具体数据行做支撑 |
| 纵深安全防护 | AST 分析 + 只读用户 + 运行时护栏，三层保障 |
| 全链路日志 | 每层可追踪，支持 Trace ID 串联 |
| 评测体系 | Golden SQL + 自动化 Benchmark |

### 项目定位差异

| 传统 Text2SQL | 本项目 AI Data Analyst |
|--------------|----------------------|
| 用户说一句，转一句 SQL | 用户提出业务问题，Agent 自主分析 |
| 只输出 SQL 和结果 | 输出 SQL → 可视化 → 带证据的洞察 |
| 无/弱错误处理 | 结构化反思循环，精准定位错误类型 |
| Schema 全部塞进 Prompt | Schema Retriever 按需检索，动态构建上下文 |
| 无评测 | Golden SQL 基准评测 + Execution Accuracy |

---

## 2. 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | FastAPI | 异步高性能，原生 SSE 支持 |
| Agent 引擎 | LangGraph | 有状态工作流 + Tool 调用编排 |
| LLM | 通义千问 / GPT-4o | 根据场景切换 |
| ORM & 数据 | SQLAlchemy + aiomysql | 异步 SQL 执行 |
| Schema 索引 | FAISS + 内存 | 表级/字段级向量索引，双路召回 |
| 会话缓存 | Redis | Session 存储 + Cache |
| 前端 | React + Ant Design + ECharts | 专业后台交互 |
| SQL 分析 | sqlglot | AST 静态分析，阻断写入操作 |
| 评测 | pytest + 自定义 Benchmark | Golden SQL 自动化评测 |

> 向量索引选型说明：Schema 数据量很小（几十张表），FAISS + 内存即可满足需求，无需 Redis Stack。Redis 仅承担 Session 和 Cache 职责。

---

## 3. 架构设计

### Agent 架构（核心变化：只有 1 个真正的 Agent + LangGraph 编排）

```
User
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│                 LangGraph Workflow                       │
│                                                          │
│   Node 1: Task Analyzer（意图分析 + 参数提取）             │
│   Node 2: Schema Retrieval（检索相关表结构）               │
│   Node 3: SQL Generation（生成 SQL）                      │
│   Node 4: Safety Validation（AST 安全校验）                │
│   Node 5: SQL Execution（执行 SQL）                       │
│   Node 6: Reflection（结构化错误修正, max 3次）            │
│   Node 7: Result Processing（按需调用 Tool）              │
│     ├── Chart Tool（数据 → Python → ECharts Option）      │
│     ├── Insight Tool（结果 → LLM → 总结）                 │
│     └── Evidence Analyzer（结论 → 引用数据 → 证据链）      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 架构原则

**Workflow（LangGraph）只负责节点编排（Orchestration），不承载业务逻辑。** 

每个 Node 仅负责：
- 从 AgentState 读取输入
- 调用对应模块
- 写回 AgentState

**禁止**：
- 编写 Prompt
- 编写 SQL
- 查询数据库
- 执行业务逻辑
- 直接访问 Repository
- 实现 Reflection 策略

所有业务能力必须保留在已有模块中，Workflow 只是胶水层（Glue Layer）。

```
Repository 负责数据来源        → SchemaRepository.get_columns()
Tool       负责执行动作          → SQLValidator.validate()
Service    负责 LLM 调用         → TaskAnalyzer.analyze()
Agent      负责有状态 Workflow   → LangGraph StateGraph
```

分层职责不可跨越：Repository 不做 Embedding，Tool 不查数据库。所有模块通过 `AgentState` 这个统一 Context 通信。

**为什么只有一个 Agent？**

| 常见错误做法 | 我们的做法 | 原因 |
|------------|-----------|------|
| 拆出 Chart Agent、Insight Agent 等子 Agent | 统一为 SQL Agent + Tool | Chart 判断 (line/bar/pie) 不需要 LLM，Python 逻辑即可。Insight 是 Summarizer 不是 Agent。Tool 调用比多 Agent 协作更轻量、更可靠 |
| Supervisor 做路由 | 不需要 | 只有 1 个 Agent，Supervisor 反而增加复杂度。当后续扩展到 10+ Agent 时再引入 |

### 完整数据流

```
User: "分析一下最近30天各品类销售额趋势"
  │
  ▼
┌─ LangGraph Workflow ────────────────────────────────────────┐
│                                                              │
│  START                                                       │
│    │                                                         │
│    ▼                                                         │
│  analyze_task_node         [TaskAnalyzer]                    │
│    │                        → task_plan                      │
│    ▼                                                         │
│  retrieve_schema_node      [SchemaRetriever]                 │
│    │                        → schema_context                 │
│    ▼                                                         │
│  generate_sql_node         [SQLGenerator]                    │
│    │                        → generated_sql, current_sql     │
│    ▼                                                         │
│  validate_sql_node         [SQLValidator]                    │
│    │                        → validation_result              │
│    │                                                         │
│    ├── passed ─────────────────────────────► execute_sql_node│
│    │              [SafeExecutor]            → query_result   │
│    │                                         │               │
│    │             成功 ──────────────────────► END            │
│    │             失败 ──► reflect_node       │               │
│    │                                                         │
│    └── failed ────────────────────────────► reflect_node     │
│                    [ReflectionLoop]                           │
│                      → reflection_result                     │
│                      → next_action (retry_generate /         │
│                            retry_retrieve / stop)            │
│                         │                                    │
│          ┌── retry_generate ──► retry++ ──► generate_sql_node│
│          │                                      (retry<3)    │
│          ├── retry_retrieve ──► retry++ ──► retrieve_...     │
│          │                                      (retry<3)    │
│          └── stop ──────────────────────────► END            │
│                                                              │
│  ─── END ────────────────────────────────────────────────────│
└──────────────────────────────────────────────────────────────┘
  │
  ▼
User 收到: 查询结果
```

---

## 4. 核心模块详解

### 4.0 Task Analyzer（原名 Journey Planning）

用户问题进入后，第一件事不是生成 SQL，而是**分析任务类型**。它不涉及多步规划（planning），而是意图识别 + 参数提取。

```python
def analyze_task(question: str, chat_history: list) -> TaskPlan:
    """
    LLM 调用，输出结构化的任务分析结果。
    这不是 "Agent Planning"——没有分解子任务、没有编排步骤。
    而是回答：用户在问什么？需要查什么？要图吗？
    """
    # 输出示例:
    {
        "task_type": "trend_analysis",         # 趋势分析/对比分析/简单查询/...
        "time_range": {"start": "2024-01-01", "end": "2024-01-30"},
        "metrics": ["sales_amount"],
        "dimensions": ["product_category"],
        "requires_chart": True,
        "chart_type_hint": "line",             # 供 Chart Tool 参考
        "requires_insight": True,
        "requires_evidence": False
    }
```

> **命名说明**：不叫 Journey Planning 是因为这里没有真正的多步规划。Task Analyzer 更准确地描述了这个职责。

### 4.1 Schema Retriever（产品经理特别强调）

这是 Text2SQL 最关键也最容易被忽视的模块。不把全量 Schema 塞进 Prompt，而是按需检索。

**实现方案**：

```
问题: "最近30天各品类销售额趋势"
  │
  ├── 关键词匹配: "销售额" → orders, payments, products
  ├── FAISS 向量检索: 问题向量 → 表描述向量库 → Top-3
  └── FK 关系扩展: products ↔ category 等关联表
  │
  ▼
Schema Context (构建 Prompt 用):
  - Table: orders (order_id, purchase_date, status)
  - Table: payments (payment_value, payment_type)
  - Table: products (product_category, product_id)
  - 表间关系: orders.order_id = payments.order_id
  - 示例数据: orders.purchase_date → "2024-01-01"
```

**Schema Index 设计**：

```python
# FAISS 向量索引，纯内存，无需额外中间件
class SchemaIndex:
    table_embeddings: Dict[str, np.ndarray]  # 表名 → 向量
    column_embeddings: Dict[str, np.ndarray] # 字段名 → 向量
    relationships: List[FKRelation]           # 外键关系

    def retrieve(self, question: str, top_k=3) -> SchemaContext:
        # 1. 问题向量化
        q_vec = self.embed(question)
        # 2. 双路召回: 表级 + 字段级 向量相似度
        # 3. 关键词匹配补充
        # 4. 关联扩展: FK 关系
        # 5. 排序去重 → 构建 Schema Context
```

> **FAISS 选型说明**：Schema 数据量很小（几十张表），FAISS 内存索引即可。无需 Redis Stack 承担向量库职责。Redis 只做会话 Session 和结果缓存。

### 4.2 SQL Reflection Loop（结构化错误处理）

不是简单 "LLM 再来一次"，而是分类处理：

```
Error Analysis 流程:

SQL 执行报错: "Unknown column 'product_name'"
  │
  ▼
┌─ Error Classifier ──────────────────────┐
│  LLM 判断错误类型:                       │
│  → Schema Error (表/字段不存在)          │
│  → Syntax Error (语法错误)               │
│  → Ambiguous (歧义/缺少上下文)           │
│  → Join Error (关联条件错误)             │
│  → Other (其他) + 重试计划              │
└─────────────────────────────────────────┘
  │
  ▼ (按类型走不同修复路径)

Schema Error:               Syntax Error:
  重新 Schema Retrieval        LLM 直接修正 SQL
  → 补充表结构                 → 重写 SQL
  → 重新生成 SQL
                          Ambiguous:
                            补充上下文信息
                            → 重新生成 SQL

  Other:
    LLM 分析错误原因 + 重试生成

  max 3 次重试，超过则返回友好错误信息
```

### 4.3 Chart Tool（非 Agent，纯 Python 逻辑）

```
DataFrame
  │
  ├── 分析数据特征:
  │   ├── 时间序列? → Line Chart
  │   ├── 分类对比? → Bar Chart
  │   ├── 占比关系? → Pie Chart
  │   ├── 相关性? → Scatter Chart
  │   └── 分布? → Histogram
  │
  ├── 生成 ECharts Option (Python dict)
  │
  └── 返回前端渲染
```

**核心设计**：
- 不需要 LLM 决定图表类型，特征分析 + 规则引擎即可
- 输出标准 ECharts JSON，前后端解耦
- 支持组合图表（如 Line + Bar 双轴）

### 4.4 Insight Tool（轻量 LLM 调用，非 Agent）

```
DataFrame + 用户问题
  │
  ▼
LLM Summarize:
  "Q2 总销售额 ¥12,345,678，环比增长 15.3%，
   家电品类增长最快 28.6%，建议重点关注..."
```

这是一个 **LLM summarize 调用**，不是 Agent。没有多步推理、没有工具调用、没有循环。

### 4.5 Evidence Analyzer（原名 Explain Tool ✅）

这是区别于其他 Text2SQL 项目的核心设计。不只是"给答案"，而是**证明答案**。改名是因为它做的是证据链分析，不是解释 SQL。

```
用户: "为什么3月份销售额下降了？"
  │
  ▼
1. SQL Agent 执行分析查询
  │
  ▼
2. Evidence Analyzer 工作:
   ├── 对比分析: 3月 vs 2月 各品类数据
   ├── 定位差异点: 哪些品类下降最多
   ├── 交叉验证: 关联订单量、客单价、退款率等多维数据
   │
  ▼
3. 输出结构化结论:
   ┌─────────────────────────────────────┐
   │ 结论: 3月销售额下降主要因为家电品类  │
   │       销量环比下降 32%               │
   │                                     │
   │ 证据链:                              │
   │  ① 家电品类 2月销售额 ¥530万         │
   │     → 3月销售额 ¥360万, 下降 ¥170万  │
   │  ② 家电品类占总销售额 38%            │
   │     → 贡献了整体下降的 62%           │
   │  ③ 订单量下降 28%, 客单价基本持平    │
   │     → 主因是订单量下降而非降价        │
   │                                     │
   │ 建议: 检查家电品类3月流量来源变化     │
   └─────────────────────────────────────┘
```

### 4.6 SQL 沙箱安全

| 层级 | 方式 | 拦截/保护范围 |
|------|------|-------------|
| 语法层 | sqlglot AST 分析 | 阻断 INSERT/UPDATE/DELETE/DROP/ALTER 等 |
| 危险模式检测 | AST 静态分析 | 无 WHERE 全表扫描、CROSS JOIN、左模糊 LIKE |
| 数据库层 | MySQL 只读用户 | 数据库层面杜绝写入 |
| 运行时 | asyncio timeout + fetchmany | 超时 10s + 最多 500 行 |
| 结果 | 截断通知 | 告知用户数据已截断 |

---

## 5. Prompt 管理体系

```
backend/
    prompts/
        sql_agent/
            system.md              # SQL Agent 系统指令
            sql_generation.md      # SQL 生成 Prompt
            schema_retrieval.md    # Schema 检索指令
            task_analyzer.md       # 任务分析指令
        reflection/
            error_classifier.md    # 错误分类 Prompt
            sql_fix.md             # SQL 修正 Prompt
        tools/
            insight.md             # 数据洞察 Prompt
            evidence_analyzer.md   # 证据链分析 Prompt
```

**版本管理**：每个 Prompt 文件头包含版本号和变更记录：

```markdown
# SQL 生成 — v2.1
# 变更: 2025-01-15 — 增加对 GROUP BY 的约束说明
# 变更: 2025-01-10 — 初始版本

你的任务是根据提供的 Schema 信息和用户问题生成 SQL 查询。
...
```

---

## 6. 评测体系

```
backend/
    evaluation/
        golden_sql.json     # 标准测试集
        benchmark.py        # 评测脚本
        metrics.py          # 指标计算
```

### Golden SQL 格式

```json
[
    {
        "id": "001",
        "question": "最近30天销量最高的前10个商品",
        "golden_sql": "SELECT p.product_id, p.product_name, COUNT(o.order_id) as sales_count FROM orders o JOIN products p ...",
        "tables_used": ["orders", "products"],
        "category": "aggregation",
        "difficulty": "easy"
    },
    {
        "id": "002",
        "question": "对比上个月各品类的销售额变化",
        "golden_sql": "...",
        "tables_used": ["orders", "payments", "products"],
        "category": "time_comparison",
        "difficulty": "hard"
    }
]
```

### 评测指标

| 指标 | 说明 |
|------|------|
| Execution Accuracy | 执行结果是否与 Golden SQL 一致 |
| SQL Match | 生成 SQL 是否与 Golden SQL 语义等价 |
| Latency | 端到端响应时间 |
| Retry Count | 平均每次查询需要几次重试 |
| Schema Recall | Schema Retriever 是否召回所有需要的表 |

> 注意：具体数值（如 Schema Recall 准确率）需在跑完真实 Benchmark 后填写，README 中不写未经验证的数字。

---

## 7. 全链路 Logging + Observability

### Trace ID 串联

每次请求生成唯一的 Trace ID，串联所有环节：

```
Trace ID: tx_7f3a1b2c
  │
  ├── [Request]        POST /chat  params={memory_id: "abc", message: "..."}
  │
  ├── [Task Analyzer]  task_type=trend_analysis, LLM Call ID: llm_001 (2.1s, 312 tokens)
  │
  ├── [Schema Retrieval]  FAISS recall: orders(0.91), payments(0.87), products(0.62)
  │
  ├── [SQL Generation]  LLM Call ID: llm_002 (3.4s, 589 tokens)
  │
  ├── [Validator]      ast_check: passed
  │
  ├── [Executor]       30 rows in 1.2s, no truncation
  │
  ├── [Chart]          line chart generated
  │
  ├── [Insight]        LLM Call ID: llm_003 (1.8s, 234 tokens)
  │
  └── [Total]          8.5s, 3 LLM calls, 0 retries
```

### Observability 设计（面试加分项 ✅）

| 能力 | 工具 | 说明 |
|------|------|------|
| Trace 追踪 | OpenTelemetry | 跨 LLM 调用、SQL 执行的分布式追踪 |
| Prompt 调试 | LangSmith | 记录每次 LLM 调用的输入/输出、Token 消耗 |
| 性能监控 | Phoenix / Grafana | LLM 延迟、SQL 执行时间、端到端响应分析 |

当前实现：
- 结构化 JSON 日志 + Trace ID

未来可接入：
- LangSmith Trace: 可视化每次 Agent 决策路径
- Prompt Evaluation: 回归测试 Prompt 变更效果
- Cost Analysis: 按用户/会话统计 Token 消耗

---

## 8. 分阶段实现计划

### Phase 1：MVP 核心链路（Week 1-2）

- [ ] FastAPI 项目初始化 + 配置管理
- [ ] MySQL 电商数据集导入（Olist 数据集）
- [ ] Schema Index (FAISS) 构建 + Schema Retriever
- [ ] SQL Agent：生成 → 校验 → 执行 基础链路
- [ ] 三层 SQL 安全沙箱
- [ ] 基础 React 聊天界面

### Phase 2：Agent 能力完善（Week 3-4）

- [ ] 结构化 Reflection Loop（Error Classifier + 分类型修复）
- [ ] LangGraph Workflow 编排（StateGraph + 条件路由 + Retry）
- [ ] Chart Tool 特征分析 + ECharts 生成
- [ ] Insight Tool 数据洞察
- [ ] Prompt 管理 + 版本化

### Phase 3：Evidence + Eval（Week 5-6）

- [ ] Evidence Analyzer 带证据链分析
- [ ] Golden SQL 测试集构建
- [ ] Benchmark 自动化评测
- [ ] 全链路 Logging + Trace ID
- [ ] 多轮对话 + 上下文管理

### Phase 4：工程完善（Week 7）

- [ ] Docker Compose 一键部署
- [ ] README + 演示文档 + 流程图
- [ ] 单元测试 + 集成测试
- [ ] 性能优化

---

## 9. 项目目录结构

```
t2sAnalysis/
├── backend/
│   ├── app/
│   │   ├── api/               # FastAPI 路由
│   │   │   ├── chat.py        # 聊天 SSE 接口
│   │   │   └── schema.py      # Schema 查询接口
│   │   ├── agents/            # Agent 节点（按业务域分组）
│   │   │   ├── state.py       # AgentState 统一 Context
│   │   │   ├── sql/           # SQL 相关节点
│   │   │   │   ├── generator.py
│   │   │   │   ├── reflection.py
│   │   │   │   └── workflow.py
│   │   │   ├── chart/         # 图表节点
│   │   │   └── insight/       # 洞察节点
│   │   ├── graph/             # LangGraph 图编排
│   │   │   └── graph.py       # StateGraph 构建
│   │   ├── tools/             # 工具函数（非 Agent）
│   │   │   ├── chart.py       # Chart Tool
│   │   │   ├── insight.py     # Insight Tool
│   │   │   ├── evidence_analyzer.py  # Evidence Analyzer
│   │   │   ├── sql_executor.py    # SQL 执行器
│   │   │   └── sql_validator.py   # SQL 安全校验
│   │   ├── services/          # 业务逻辑
│   │   │   ├── chat_service.py
│   │   │   └── task_analyzer.py   # 任务分析（原 Journey Planning）
│   │   ├── repositories/      # 数据访问
│   │   │   ├── schema_repository.py
│   │   │   └── memory_repository.py
│   │   ├── schemas/           # Schema 管理
│   │   │   ├── schema_index.py    # FAISS 索引构建
│   │   │   └── schema_retriever.py # Schema 检索
│   │   ├── models/            # Pydantic 模型
│   │   │   ├── chat.py
│   │   │   ├── sql.py
│   │   │   └── agent.py
│   │   └── core/              # 基础设施
│   │       ├── config.py
│   │       ├── database.py
│   │       ├── redis.py
│   │       └── security.py
│   ├── prompts/               # Prompt 版本管理
│   │   ├── sql_agent/
│   │   ├── reflection/
│   │   └── tools/
│   ├── evaluation/            # 评测体系
│   │   ├── golden_sql.json
│   │   ├── benchmark.py
│   │   └── metrics.py
│   ├── scripts/               # 初始化脚本
│   │   └── init_db.py
│   ├── requirements.txt
│   └── main.py
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   └── Chat.tsx
│   │   ├── components/
│   │   │   ├── ChatBox.tsx
│   │   │   ├── ChartView.tsx
│   │   │   ├── DataTable.tsx
│   │   │   └── SqlReview.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   └── App.tsx
│   ├── package.json
│   └── tsconfig.json
│
├── docker-compose.yml
└── README.md
```

---

## 10. README 流程图（建议）

```
┌──────────────┐
│  User Question │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Task Analyzer│
│ (意图+参数)   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Schema Retrieval│
│ (FAISS + 关键词)│
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ SQL Generation│
│ (LLM + Schema) │
└──────┬───────┘
       │
       ▼
┌──────────────┐  失败   ┌──────────────────┐
│    Validator  ├────────► Error Classifier │
│ (sqlglot AST)│        │ (结构化分类修复)   │
└──────┬───────┘        └────────┬─────────┘
       │ 通过                    │ 重试 (max 3)
       ▼                        │
┌──────────────┐                │
│   Executor   │◄───────────────┘
│ (只读+超时)   │
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│   Result Processing   │
│ ┌──────┐ ┌────────┐  │
│ │Chart │ │Insight │  │
│ │Tool  │ │Tool    │  │
│ └──┬───┘ └───┬────┘  │
│    │         │        │
│    ▼         ▼        │
│ ┌───────────────┐     │
│ │   Evidence    │     │
│ │   Analyzer    │     │
│ └───────┬───────┘     │
└─────────┼─────────────┘
          │
          ▼
┌──────────────┐
│   Answer +    │
│ Chart + Data  │
└──────────────┘
```

---

## 11. 面试竞争力分析

| 维度 | 说明 |
|------|------|
| 架构设计 | 1 个 Agent + 多 Tool，不盲目拆 Agent。Graph 与 Agent 分离，职责清晰 |
| 工程能力 | Prompt 版本管理、结构化 Reflection、评测体系、全链路 Logging、Trace ID 串联 |
| AI 应用 | LangGraph StateGraph、FAISS Schema 检索、结构化错误分类 |
| 创新性 | Evidence Analyzer + Evidence Chain，定位 AI Data Analyst 而非 Text2SQL Demo |
| 面试竞争力 | 面试官有深度可聊的话题：Agent 设计取舍、安全策略、评测方式、可观测性 |

---

## 12. 面试常见问题预案

| 面试官可能会问 | 你的回答 |
|--------------|---------|
| 为什么不用 Supervisor？ | 当前只有 1 个 Agent，引入 Supervisor 徒增复杂度。设计原则：Agent 在必要时引入，而不是为了用而用 |
| Chart 为什么是 Tool 不是 Agent？ | 图表类型判断 (line/bar/pie) 可以用特征工程 + 规则解决，不需要 LLM。Tool 更快、更可控、不消耗 Token |
| Reflection Loop 为什么不直接 LLM 重试？ | 分类处理更工程化：Unknown Column 意味着 Schema 不一致，重试 SQL 没用，需要重新检索 Schema |
| Schema Retriever 召回率怎么样？ | 目前跑了 Benchmark 框架，具体数值还在评测中，支持 Execution Accuracy / Schema Recall / Latency 等指标 |
| 你这个和 Chat2DB 有什么区别？ | Chat2DB 偏工具，我们是 Agent 系统。最大的差异是 Evidence Analyzer + Evidence Chain |
| 用 FAISS 不用 Redis Stack 的原因？ | Schema 只有几十张表，FAISS 内存索引足够，不需要额外维护 Redis Stack。Redis 专注 Session 和 Cache |
