# PRD：Excel 文件上传分析功能

> 产品：AI Data Analyst
> 版本：v2.0 规划
> 日期：2026-07-24
> 状态：定稿
>
> **一句话定位：一套引擎，一个数据库，万物皆 Dataset。**

---

## 1. 核心理念

### 三层架构

```
┌──────────────────────────────────────────────────────────┐
│                    AI Data Analyst                        │
├──────────────────────┬───────────────────────────────────┤
│   Business Database  │        Analytics Engine           │
│      (MySQL)         │           (DuckDB)                │
├──────────────────────┼───────────────────────────────────┤
│ users                │ orders                            │
│ sessions             │ customers                         │
│ messages             │ products                          │
│ datasets             │ sales_june_3f6a                   │
│                      │ finance_q2_7b2e                   │
├──────────────────────┼───────────────────────────────────┤
│ AI 永远不查询         │ AI 只查询这里                     │
└──────────────────────┴───────────────────────────────────┘
```

### 核心原则

```
Everything is a Dataset.
AI 只看到 Catalog 中的相关表。
Prompt 统一组装，改一次全系统生效。
```

### AI 视角

```
AI 看到的世界（经 Catalog top_k 过滤后）：

Table: orders        — 50 rows, Demo, dimensions=[customer_id], measures=[order_id]
Table: sales_june    — 58,234 rows, Excel, dimensions=[产品名称, 品类], measures=[销售额]
Table: finance_q2    — 12,000 rows, Excel, dimensions=[部门], measures=[收入, 支出]

AI 不知道数据来自哪里，只管生成 SQL。
```

### 架构全景

```
                    用户上传 Excel/CSV
                           │
                           ▼
                     Ingestion Layer
                   (数据接入层，可扩展)
                           │
                           ▼
                  ┌─ DatasetManager ─┐
                  │   Import / Delete  │
                  └────────┬────────┘
                           │
                           ▼
                     DatasetRegistry
                    (Catalog，唯一入口)
                  get_catalog(top_k=10)
                           │
                    ┌──────┴──────┐
                    ▼             ▼
               Schema         Profile
             (列名+类型)    (统计+语义类型)
                    │             │
                    └──────┬──────┘
                           ▼
                     PromptBuilder
                  Catalog → PromptContext
                  → Markdown Template
                           │
                           ▼
                    SQL Generator      ← 零改动
                           │
                           ▼
                      Reflection       ← 零改动
                           │
                           ▼
                    SQL Validator      ← 零改动
                           │
                           ▼
                   DuckDB Execute      ← 极简
                           │
                           ▼
                  Chart + Insight      ← 零改动
```

---

## 2. 背景与目标

### 现状

- Olist 演示数据和业务数据混在同一个 MySQL
- 无法处理用户上传的 Excel/CSV
- SchemaRetriever 硬编码 MySQL 表结构

### 目标

1. **数据分离**：业务元数据（MySQL）与分析数据（DuckDB）完全独立
2. **万物皆 Dataset**：Demo、Excel、CSV 统一抽象，AI 不区分来源
3. **DatasetRegistry 作为唯一 Catalog**：SQL Generator 只从这里获取 Schema
4. **PromptBuilder 独立**：输出 PromptContext，统一组装 Prompt
5. **零改动链路**：SQL Generator → Reflection → Validator → Chart/Insight 全部不动

---

## 3. 核心概念

### 3.1 Dataset（数据集）

**Dataset ≠ File。** 统一抽象，万物皆 Dataset：

```python
class Dataset:
    id: str              # UUID，如 "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    name: str            # "6月销售报表" / "Olist Orders"
    source_type: str     # "excel" | "csv" | "demo" | "parquet" | "api"
    status: str          # "uploading" | "ready" | "deleted" | "archived"
    table_name: str      # DuckDB 中的真实表名，如 "sales_june_3f6a"
    session_id: str      # 关联的会话（Demo 数据为空）
    row_count: int
    column_count: int
    columns_meta: list   # 列名、类型、语义类型
    profile_meta: dict   # 数据画像
    original_file: str   # 原始文件路径（Demo 为空）
    created_at: datetime
```

**Dataset ID ≠ DuckDB 表名：**

```
Dataset ID:     a1b2c3d4-e5f6-7890-abcd-ef1234567890   (UUID，内部标识)
DuckDB 表名:    sales_june_3f6a                          (可读，用户/Debug 友好)
映射关系:       datasets 表维护 id → table_name
```

**SHOW TABLES 时看到的是有意义的表名，不是 UUID。**

**所有数据源统一：**

| 来源 | source_type | 导入方式 |
|------|-------------|----------|
| 内置 Olist | `demo` | Bootstrap 时 CSV → DuckDB |
| Excel | `excel` | pandas.read_excel → DuckDB |
| CSV | `csv` | DuckDB read_csv 直读 |
| 未来：Parquet | `parquet` | DuckDB read_parquet |
| 未来：API | `api` | HTTP → DataFrame → DuckDB |

### 3.2 Dataset 生命周期

```
Uploading ──→ Ready ──→ Deleted
                │
                └──→ Archived
```

| 状态 | 说明 | 触发 |
|------|------|------|
| `uploading` | 正在导入 DuckDB | 上传开始 |
| `ready` | 可查询 | 导入完成 + 画像生成完成 |
| `deleted` | 用户删除，DuckDB 表已 DROP | 用户操作 |
| `archived` | 超期自动归档，表仍保留 | 定时任务 |

**异常恢复：** 如果导入中断，`uploading` 状态的 Dataset 可以被清理任务识别并重试或删除。

### 3.3 Semantic Type（语义类型）

Profile 中每列增加 `semantic_type`：

```python
class ColumnProfile:
    name: str                # "销售额"
    data_type: str           # "DOUBLE"
    semantic_type: str       # "dimension" | "measure" | "time" | "identifier" | "text"
    null_ratio: float
    unique_count: int
    min_value: str | None
    max_value: str | None
    top_values: list[str]
```

**语义类型推断规则：**

| 语义类型 | 推断依据 | 示例 |
|----------|----------|------|
| `measure` | 数值列 + high unique ratio + 有小数 | 销售额、数量、价格 |
| `dimension` | 文本列 + low unique ratio OR 有枚举特征 | 品类、城市、状态 |
| `time` | DATE/TIMESTAMP 类型 | 销售日期、创建时间 |
| `identifier` | high unique ratio + 非数值 OR 含 `_id` 后缀 | 订单号、客户ID |
| `text` | 其他文本列 | 评论内容、描述 |

**收益：**
- ChartTool 直接用 `measure + dimension` 选图表，不用猜
- SQL Generator 知道哪些列可以 GROUP BY、哪些可以 SUM
- Prompt 中直接写 `销售额 (DOUBLE, measure)` 而不是只有 `销售额 (DOUBLE)`

### 3.4 DatasetRegistry（数据目录）

**替代 SchemaRetriever**，AI 的唯一数据入口：

```python
class DatasetRegistry:
    """AI 的数据目录（Catalog）。"""

    def get_catalog(
        self,
        session_id: str | None = None,
        question: str | None = None,
        top_k: int = 10,
    ) -> Catalog:
        """获取 Catalog（相关数据集）。
        
        - 返回：Demo 数据集 + 当前会话上传的数据集
        - top_k：最多返回多少张表（控制 Prompt 长度）
        - question：可选，用于按相关性排序
        """

    def get_table_schema(self, table_name: str) -> TableSchema:
        """获取单张表的 Schema + Profile。"""
```

**不要把所有 Dataset 都塞进 Prompt：**
- 100 个 Dataset 时 Prompt 会爆
- top_k=10 保证 Prompt 可控
- 未来可以用 question 做相关性排序

### 3.5 PromptBuilder（Prompt 组装器）

**输出 PromptContext，不是直接输出 Markdown：**

```python
@dataclass
class PromptContext:
    """Prompt 的结构化输入，由 PromptBuilder 组装。"""
    schema: str                    # 格式化的 Schema + Profile 文本
    examples: list[str]            # 可选：Few-shot 示例
    business_rules: list[str]      # 可选：业务规则约束
    metadata: dict                 # 可选：额外上下文

class PromptBuilder:
    """Catalog → PromptContext → Markdown。"""

    def build_context(self, catalog: Catalog) -> PromptContext:
        """Catalog → PromptContext（结构化）。"""

    def render(self, context: PromptContext, template: str) -> str:
        """PromptContext + Template → 最终 Prompt 文本。"""
```

**两步分离的好处：**
- `build_context` 只负责结构化数据
- `render` 负责 Markdown 模板
- 以后 Prompt 版本升级只改 `render`，不动 `build_context`
- 可以轻松 A/B 测试不同 Prompt 格式

**PromptContext 示例输出：**

```python
PromptContext(
    schema="""
### Table: orders (Demo)
行数: 50

Columns:
- order_id (VARCHAR, identifier) — 50 unique values
  Examples: ORD0001, ORD0002, ORD0003
- customer_id (VARCHAR, identifier) — 15 unique values
  Examples: C001, C002, C003
- order_status (VARCHAR, dimension) — 1 value: delivered
- order_purchase_timestamp (TIMESTAMP, time) — 2026-04-26 ~ 2026-06-12

### Table: sales_june (Excel: 6月销售报表.xlsx)
行数: 58,234

Columns:
- 产品名称 (VARCHAR, dimension) — 35 unique, 0% NULL
  Examples: MacBook, ThinkPad, iPhone 15
- 品类 (VARCHAR, dimension) — 8 unique, 0% NULL
- 销售额 (DOUBLE, measure) — range: 10.0~9800.0, avg: 620.5, 2% NULL
- 销售日期 (DATE, time) — 2024-06-01 ~ 2024-06-30
""",
    examples=[],
    business_rules=["金额单位为人民币元"],
)
```

### 3.6 Bootstrap（系统初始化）

**Demo 数据初始化不属于 DatasetManager，由独立的 Bootstrap 模块负责：**

```
Application 启动
        │
        ▼
    Bootstrap
        │
        ├── 1. DuckDB.connect("analysis.duckdb")
        │
        ├── 2. 检查 Demo 数据是否已导入
        │      └── 未导入 → CSV → DuckDB → 注册 Dataset
        │
        ├── 3. 初始化 DatasetRegistry
        │      └── 加载所有 Dataset 到内存索引
        │
        ├── 4. 初始化 PromptBuilder
        │
        └── 5. 完成，Application ready
```

**职责分离：**
- Bootstrap：系统启动、初始化、Demo 数据导入
- DatasetManager：Import / Delete / Update（运行时操作）

---

## 4. 功能需求

### 4.1 文件上传（P0）

| 需求项 | 描述 |
|--------|------|
| 格式 | `.xlsx`, `.xls`, `.csv` |
| 大小限制 | 单文件最大 10MB |
| Sheet 处理 | 默认导入所有 Sheet，每个 Sheet 生成独立 Dataset |
| 编码检测 | CSV 自动检测（UTF-8, GBK, GB2312） |
| 预览 | 前 5 行 + 列名 + 类型 + 语义类型 + 数据画像 |
| 上传方式 | 拖拽 + 点击 |

### 4.2 数据解析与导入（P0）

| 需求项 | 描述 |
|--------|------|
| CSV | DuckDB `read_csv()` 直读，不依赖 pandas |
| Excel | `pandas.read_excel()` → DuckDB |
| 类型推断 | DuckDB 自动 + Semantic Type 推断 |
| 列名清洗 | 中文/空名/重复/特殊字符（见 7.1） |
| 行数限制 | 最大 100,000 行 |

### 4.3 数据画像（P0）

| 需求项 | 描述 |
|--------|------|
| 列级 | 类型、语义类型、唯一值数、NULL 比例、min、max、top5 |
| 表级 | 行数、列数、日期范围 |
| 存储 | `datasets.profile_meta` JSON |
| Prompt | 由 PromptBuilder 自动注入 |

### 4.4 自然语言查询（P0）

| 需求项 | 描述 |
|--------|------|
| 引擎 | 统一 DuckDB |
| Prompt | PromptBuilder 组装 PromptContext → 模板渲染 |
| 结果 | 表格 + 图表 + 洞察（复用现有） |

### 4.5 数据集管理（P1）

| 需求项 | 描述 |
|--------|------|
| 列表 | 当前会话的数据集 |
| 删除 | → status=deleted + DROP TABLE |
| 归档 | → status=archived（不删除表，但不再出现在 Catalog） |

---

## 5. 技术方案

### 5.1 数据存储

```
backend/data/
├── uploads/
│   └── {uuid}.xlsx                # 原始文件（备份）
├── seed/
│   ├── orders.csv
│   ├── customers.csv
│   ├── products.csv
│   ├── payments.csv
│   ├── order_items.csv
│   ├── sellers.csv
│   ├── product_category.csv
│   └── reviews.csv
└── analysis.duckdb                # 唯一分析数据库
```

### 5.2 业务数据库 Schema（MySQL）

```sql
CREATE TABLE datasets (
    id              VARCHAR(36) PRIMARY KEY,        -- UUID
    name            VARCHAR(255) NOT NULL,          -- "6月销售报表"
    source_type     VARCHAR(32) NOT NULL,           -- "excel" | "csv" | "demo"
    status          VARCHAR(32) DEFAULT 'uploading',-- "uploading" | "ready" | "deleted" | "archived"
    table_name      VARCHAR(128) NOT NULL UNIQUE,   -- DuckDB 表名，如 "sales_june_3f6a"
    session_id      VARCHAR(64),                    -- Demo 数据为空
    row_count       INT,
    column_count    INT,
    columns_meta    JSON,
    profile_meta    JSON,
    original_file   VARCHAR(500),
    file_size_bytes BIGINT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_datasets_session (session_id),
    INDEX idx_datasets_status (status),
    INDEX idx_datasets_source (source_type)
);
```

### 5.3 DuckDB 表名生成规则

```python
def generate_table_name(file_name: str, sheet_name: str | None = None) -> str:
    """生成可读的 DuckDB 表名。"""
    # 取文件名（去扩展名）
    base = Path(file_name).stem
    # 清洗为合法标识符
    cleaned = clean_column_name(base)
    # 加 UUID 后缀（4位）
    suffix = uuid.uuid4().hex[:4]
    # 如有 Sheet 名，加入
    if sheet_name:
        sheet_cleaned = clean_column_name(sheet_name)
        return f"{cleaned}_{sheet_cleaned}_{suffix}"
    return f"{cleaned}_{suffix}"
```

示例：
- `6月销售报表.xlsx` → `sales_june_3f6a`
- `财务数据.xlsx` Sheet "收入" → `finance_income_7b2e`
- `customers.csv` → `customers_a1b2`

### 5.4 Bootstrap 流程

```python
class Bootstrap:
    """系统启动初始化。"""

    async def run(self):
        # 1. 连接 DuckDB
        self._duckdb_conn = duckdb.connect("backend/data/analysis.duckdb")

        # 2. 导入 Demo 数据（如果未导入）
        await self._init_demo_data()

        # 3. 初始化 DatasetRegistry
        self._registry = DatasetRegistry(self._duckdb_conn, mysql_db)
        await self._registry.load_all()

        # 4. 初始化 PromptBuilder
        self._prompt_builder = PromptBuilder()

        # 5. 初始化 DatasetManager
        self._dataset_manager = DatasetManager(
            self._duckdb_conn, self._registry, mysql_db
        )

    async def _init_demo_data(self):
        """检查并导入 Demo 数据。"""
        catalog = self._registry.get_catalog()
        if any(d.source_type == "demo" for d in catalog.tables):
            return  # 已导入

        for csv_file in SEED_DIR.glob("*.csv"):
            dataset_id = str(uuid.uuid4())
            table_name = f"{csv_file.stem}_{dataset_id[:4]}"
            self._duckdb_conn.execute(
                f'CREATE TABLE "{table_name}" AS SELECT * FROM read_csv(\'{csv_file}\')'
            )
            # 生成画像 + 注册 Dataset...
```

### 5.5 Executor 极简化

```python
class DuckDBExecutor:
    """DuckDB SQL 执行器。"""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    async def execute(self, sql: str) -> QueryResult:
        """执行 SQL 并返回 QueryResult。"""
        result = self._conn.execute(sql).fetchdf()
        columns = list(result.columns)
        rows = result.to_dict("records")
        return QueryResult(columns=columns, rows=rows, row_count=len(rows))
```

### 5.6 列名清洗规则

| 原始列名 | 处理后 | 方式 |
|----------|--------|------|
| 销售额 | `销售额` | 中文用反引号包裹 |
| Sales Amount | `sales_amount` | 小写 + 下划线 |
| (空) | `col_1` | 自动生成 |
| 重复列名 | `col_name_2` | 加后缀 |
| 2024年 | `year_2024` | 数字开头加前缀 |
| Revenue($) | `revenue` | 去除特殊字符 |

### 5.7 安全设计

| 风险 | 对策 |
|------|------|
| SQL 注入 | sqlglot 验证 |
| 写操作 | sqlglot 阻断 |
| 文件恶意内容 | 大小 + 行数限制 |
| 文件名注入 | UUID 存储 |
| 路径遍历 | 固定目录 |

---

## 6. 模块清单

### 新增模块

| 模块 | 职责 | 位置 |
|------|------|------|
| **Bootstrap** | 系统启动、Demo 导入、组件初始化 | `backend/app/bootstrap.py` |
| **DatasetManager** | Import / Delete / Update（运行时） | `backend/app/services/dataset_manager.py` |
| **DatasetRegistry** | Catalog 管理（替代 SchemaRetriever） | `backend/app/services/dataset_registry.py` |
| **PromptBuilder** | Catalog → PromptContext → Markdown | `backend/app/services/prompt_builder.py` |
| **SchemaProfiler** | 数据画像 + 语义类型推断 | `backend/app/tools/schema_profiler.py` |
| **DuckDBEngine** | DuckDB 连接管理 | `backend/app/core/duckdb.py` |
| **DuckDBExecutor** | SQL 执行 | `backend/app/tools/duckdb_executor.py` |
| **上传 API** | 文件接收、导入、预览 | `backend/app/api/datasets.py` |

### 改动模块（极小）

| 模块 | 改动 |
|------|------|
| SQLGenerator | prompt 从 PromptBuilder 获取（1 行） |
| LangGraph | execute 节点换 DuckDBExecutor（1 行） |

### 删除模块

| 模块 | 原因 |
|------|------|
| ~~SchemaRetriever~~ | 被 DatasetRegistry 替代 |
| ~~SchemaIndex (FAISS)~~ | Catalog 直接查询 |
| ~~SafeExecutor (MySQL)~~ | 分析不走 MySQL |
| ~~FileParser~~ | CSV 直读 + Excel 只需 pandas.read_excel |

### 零改动模块

SQLValidator · ReflectionLoop · ChartTool · InsightTool · sessions/messages API

---

## 7. 依赖变更

```diff
# requirements.txt
+ duckdb>=0.10
+ openpyxl>=3.1
+ xlrd>=2.0
+ chardet>=5.0
+ pandas>=2.0            # 仅 Excel read_excel()

- faiss-cpu              # 不再需要向量搜索
```

---

## 8. 里程碑

| 阶段 | 内容 | 周期 |
|------|------|------|
| **M1: 基础设施** | DuckDBEngine、Bootstrap、Demo CSV 导出+导入、DuckDBExecutor | 3 天 |
| **M2: Dataset 体系** | DatasetManager、DatasetRegistry、SchemaProfiler（含 semantic_type）、datasets 表 | 3 天 |
| **M3: PromptBuilder** | PromptContext、模板渲染、替换 SQLGenerator 拼接 | 2 天 |
| **M4: 文件上传** | Excel/CSV 导入、上传 API、数据画像 | 1 周 |
| **M5: 前端集成** | 附件按钮、拖拽上传、文件卡片、数据集管理页 | 1 周 |

**总计约 3 周**

---

## 9. 风险与对策

| 风险 | 对策 |
|------|------|
| LLM SQL 列名错误 | Profile 注入精确列名 + 示例值 + semantic_type + Reflection |
| Excel 格式异常 | 只支持标准表格，异常明确提示 |
| analysis.duckdb 损坏 | Demo 可从 CSV 重建，用户数据保留源文件 |
| 列名清洗后不认识 | Profile 保留原始列名 + 清洗后列名 |
| Dataset 过多 | Catalog top_k 过滤 |

---

## 10. 成功指标

| 指标 | 目标 |
|------|------|
| 文件上传成功率 | > 95% |
| SQL 准确率 | > 85%（Profile + semantic_type 注入后） |
| 代码复用率 | > 80% |
| 新数据源接入 | < 1 天 |
| 架构扩展性 | 新增 Parquet/API 不改 AI Pipeline |
