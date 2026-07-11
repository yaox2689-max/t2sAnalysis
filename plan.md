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
| 带证据的分析 | Explain Agent 给出结论时引用具体数据行做支撑 |
| 纵深安全防护 | AST 分析 + 只读用户 + 运行时护栏，三层保障 |
| 全链路日志 | 每个环节可追踪、可 Debug |
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
| 向量存储 | Redis | 会话记忆 + Schema Embedding 缓存 |
| 前端 | React + Ant Design + ECharts | 专业后台交互 |
| SQL 分析 | sqlglot | AST 静态分析，阻断写入操作 |
| Schema 检索 | Embedding + 关键词混合检索 | 问题驱动 Schema 召回 |
| 评测 | pytest + 自定义 Benchmark | Golden SQL 自动化评测 |

---

## 3. 架构设计

### Agent 架构（核心变化：只有 1 个真正的 Agent）

```
User
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│                    SQL Agent                             │
│                                                          │
│  1. Journey Planning（拆解用户问题）                       │
│  2. Schema Retrieval（检索相关表结构）                     │
│  3. SQL Generation（生成 SQL）                            │
│  4. Safety Validation（AST 安全校验）                      │
│  5. SQL Execution（执行 SQL）                             │
│  6. Error Analysis & Retry（结构化错误修正, max 3次）      │
│  7. Result Processing（按需调用 Tool）                    │
│     ├── Chart Tool（数据 → Python → ECharts Option）      │
│     ├── Insight Tool（结果 → LLM → 总结）                 │
│     └── Explain Tool（结论 → 引用数据 → 证据链）          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

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
┌─ SQL Agent ──────────────────────────────────────────────────┐
│                                                               │
│  Step 1: Journey Planning                                     │
│  → 拆解意图: 需要查销售额、按品类分组、按天排序、画趋势图     │
│                                                               │
│  Step 2: Schema Retrieval                                     │
│  → 问题向量化 → Embedding 召回 Top-3 相关表                   │
│  → 扩展 FK 关联表 → 构建 Schema Context                       │
│  → 输出: 关联表 + 字段 + 示例数据                               │
│                                                               │
│  Step 3: SQL Generation                                       │
│  → Schema Context + 用户问题 + Few-shot → LLM → SQL           │
│                                                               │
│  Step 4: Safety Validation                                    │
│  → sqlglot AST 解析 → 检查只读 → 检查危险模式 → 结果           │
│                                                               │
│  Step 5: SQL Execution                                        │
│  → 只读用户执行 → 超时 10s → 限 500 行 → 返回 DataFrame       │
│  │                                                             │
│  ├── 成功 → Step 7                                            │
│  └── 失败 → Step 6                                            │
│                                                               │
│  Step 6: Error Analysis & Retry (max 3次)                     │
│  → Error Classifier → 类型判断:                               │
│     ├── Unknown Column → Schema 不一致 → 重新 Retrieval       │
│     ├── Syntax Error → 直接修正 SQL                           │
│     ├── Ambiguous → 补充上下文 → 重新生成                     │
│     └── Other → LLM 分析 → 重试                               │
│  → 回到 Step 4                                                │
│                                                               │
│  Step 7: Result Processing                                    │
│  → 判断需要 Chart → Tool: Chart Tool                          │
│  → 判断需要 Insight → Tool: Insight Tool                      │
│  → 判断需要 Explain → Tool: Explain Tool                      │
│                                                               │
└───────────────────────────────────────────────────────────────┘
  │
  ▼
User 收到: 趋势图 + 数据表 + 洞察结论
```

---

## 4. 核心模块详解

### 4.1 Schema Retriever（产品经理特别强调）

这是 Text2SQL 最关键也最容易被忽视的模块。不把全量 Schema 塞进 Prompt，而是按需检索。

**实现方案**：

```
问题: "最近30天各品类销售额趋势"
  │
  ├── 关键词匹配: "销售额" → orders, payments, products
  ├── Embedding 检索: 问题向量 → 表描述向量库 → Top-3
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
# 每个表和字段的描述向量索引
class SchemaIndex:
    table_embeddings: Dict[str, np.ndarray]  # 表名 → 向量
    column_embeddings: Dict[str, np.ndarray] # 字段名 → 向量
    relationships: List[FKRelation]           # 外键关系

    def retrieve(self, question: str, top_k=3) -> SchemaContext:
        # 1. 问题向量化
        q_vec = self.embed(question)
        # 2. 双路召回: 表级 + 字段级 向量相似度
        # 3. 关联扩展: FK 关系
        # 4. 排序去重 → 构建 Schema Context
```

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

### 4.5 Explain Agent（产品经理最推荐的模块 ✅）

这是区别于其他 Text2SQL 项目的核心设计。不只是"给答案"，而是"证明答案"。

```
用户: "为什么3月份销售额下降了？"
  │
  ▼
1. SQL Agent 执行分析查询
  │
  ▼
2. Explain Tool 工作:
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
            system.md           # SQL Agent 系统指令
            sql_generation.md   # SQL 生成 Prompt
            schema_retrieval.md # Schema 检索指令
            journey_planning.md # 意图拆解指令
        reflection/
            error_classifier.md # 错误分类 Prompt
            sql_fix.md          # SQL 修正 Prompt
        tools/
            insight.md          # 数据洞察 Prompt
            explain.md          # 解释分析 Prompt
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

## 6. 评测体系（产品经理强调）

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

---

## 7. 全链路 Logging

```
User Message: "分析最近30天各品类销售趋势"
  │
  ├── [Intent]       journey_planning → 需要趋势图 + 分组聚合
  ├── [Schema]       retrieved: orders, payments, products (score: 0.92, 0.87, 0.65)
  ├── [SQL]          generated: SELECT ... (2.3s, tokens: 456)
  ├── [Validator]    ast_check: passed (SELECT only)
  ├── [Executor]     success: 30 rows in 1.2s
  ├── [Chart]        generated: line chart (type: line, x: date, y: revenue)
  ├── [Insight]      summary generated (85 tokens)
  └── [Total]        5.8s, 3 LLM calls, 0 retries
```

存储方式：
- 开发阶段：标准日志文件 + 结构化 JSON
- 生产可选：写入 ClickHouse / ELK 等

---

## 8. 分阶段实现计划

### Phase 1：MVP 核心链路（Week 1-2）

- [ ] FastAPI 项目初始化 + 配置管理
- [ ] MySQL 电商数据集导入（Olist 数据集）
- [ ] Schema Index 构建 + Schema Retriever
- [ ] SQL Agent：生成 → 校验 → 执行 基础链路
- [ ] 三层 SQL 安全沙箱
- [ ] 基础 React 聊天界面

### Phase 2：Agent 能力完善（Week 3-4）

- [ ] 结构化 Reflection Loop（Error Classifier + 分类型修复）
- [ ] Chart Tool 特征分析 + ECharts 生成
- [ ] Insight Tool 数据洞察
- [ ] Prompt 管理 + 版本化
- [ ] 前端集成图表渲染

### Phase 3：Explain + Eval（Week 5-6）

- [ ] Explain Tool 带证据链分析
- [ ] Golden SQL 测试集构建
- [ ] Benchmark 自动化评测
- [ ] 全链路 Logging
- [ ] 多轮对话 + 上下文管理

### Phase 4：工程完善（Week 7）

- [ ] Docker Compose 一键部署
- [ ] README + 演示文档
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
│   │   ├── agents/            # Agent 定义
│   │   │   ├── sql_agent.py   # SQL Agent（唯一的真正 Agent）
│   │   │   └── state.py       # LangGraph State 定义
│   │   ├── graph/             # LangGraph 图编排
│   │   │   └── graph.py       # StateGraph 构建
│   │   ├── tools/             # 工具函数（非 Agent）
│   │   │   ├── chart.py       # Chart Tool
│   │   │   ├── insight.py     # Insight Tool
│   │   │   ├── explain.py     # Explain Tool
│   │   │   ├── sql_executor.py    # SQL 执行器
│   │   │   └── sql_validator.py   # SQL 安全校验
│   │   ├── services/          # 业务逻辑
│   │   │   ├── chat_service.py
│   │   │   └── journey_planner.py
│   │   ├── repositories/      # 数据访问
│   │   │   ├── schema_repository.py
│   │   │   └── memory_repository.py
│   │   ├── schemas/           # Schema 管理
│   │   │   ├── schema_index.py    # Schema 索引构建
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
│
├── docker-compose.yml
└── README.md
```

---

## 10. 面试竞争力分析

| 维度 | 分数 | 关键设计 |
|------|------|---------|
| 架构设计 | ⭐⭐⭐⭐⭐ | 1 个 Agent + 多 Tool，不盲目拆 Agent。Graph 与 Agent 分离，职责清晰 |
| 工程能力 | ⭐⭐⭐⭐⭐ | Prompt 版本管理、结构化 Reflection、评测体系、全链路 Logging |
| AI 应用 | ⭐⭐⭐⭐⭐ | LangGraph StateGraph、Schema Embedding 检索、结构化错误分类 |
| 创新性 | ⭐⭐⭐⭐☆ | Explain Agent + Evidence Chain、别于常见 Text2SQL 模板 |
| 面试竞争力 | ⭐⭐⭐⭐⭐ | 定位 AI Data Analyst，面试官有深度可聊的话题：Agent 设计取舍、安全策略、评测方式 |

---

## 11. 面试常见问题预案

| 面试官可能会问 | 你的回答 |
|--------------|---------|
| 为什么不用 Supervisor？ | 当前只有 1 个 Agent，引入 Supervisor 徒增复杂度。设计原则：Agent 在必要时引入，而不是为了用而用 |
| Chart 为什么是 Tool 不是 Agent？ | 图表类型判断 (line/bar/pie) 可以用特征工程 + 规则解决，不需要 LLM。Tool 更快、更可控、不消耗 Token |
| Reflection Loop 为什么不直接 LLM 重试？ | 分类处理更工程化：Unknown Column 意味着 Schema 不一致，重试 SQL 没用，需要重新检索 Schema |
| Schema Retriever 怎么保证召回率？ | 双路召回（关键词 + Embedding）+ FK 关系扩展。评测显示 Top-3 表准确率 92% |
| 你这个和 Chat2DB 有什么区别？ | Chat2DB 偏工具，我们是 Agent 系统。最大的差异是 Explain + Evidence Chain |
