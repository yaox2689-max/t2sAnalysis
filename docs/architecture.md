# Architecture

> 系统架构设计文档

## 目录结构

```
backend/
├── main.py
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py      # PR5
│   │   └── redis.py         # PR5
│   ├── repositories/
│   │   └── schema_repository.py   # PR6
│   ├── tools/
│   │   ├── sql_executor.py        # PR7
│   │   ├── sql_validator.py       # PR8
│   │   ├── chart.py               # PR14
│   │   ├── insight.py             # PR15
│   │   └── evidence_analyzer.py   # PR16
│   ├── schemas/
│   │   ├── schema_index.py        # PR11
│   │   └── schema_retriever.py    # PR12
│   ├── agents/
│   │   ├── sql_agent.py           # PR10
│   │   └── reflection.py          # PR13
│   └── services/
│       └── task_analyzer.py       # PR9
├── prompts/
│   ├── sql_agent/
│   ├── reflection/
│   └── tools/
└── requirements.txt
```

## Agent 架构

```
User
  │
  ▼
┌──────────────────────────────────────┐
│            SQL Agent                 │
│                                      │
│  1. Task Analyzer                    │
│  2. Schema Retrieval                 │
│  3. SQL Generation                   │
│  4. Safety Validation                │
│  5. SQL Execution                    │
│  6. Error Analysis & Retry           │
│  7. Result Processing                │
│     ├── Chart Tool                   │
│     ├── Insight Tool                 │
│     └── Evidence Analyzer            │
└──────────────────────────────────────┘
```

## 核心原则

1. 一个 Agent，多个 Tool（Chart/Insight/Evidence 不是 Agent）
2. 模块之间单向依赖，禁止反向/循环依赖
3. 安全纵深：AST 分析 + 只读用户 + 超时 + 行数限制
