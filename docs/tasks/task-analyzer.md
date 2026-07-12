# Task Analyzer

完成：

- prompts/sql_agent/task_analyzer.md（Prompt）
- TaskAnalyzer.analyze(question, history) → TaskPlan
- TaskPlan Pydantic 模型（task_type, time_range, metrics, dimensions, requires_chart, requires_insight)
- 单元测试（Mock LLM）

不要：

- 生成 SQL
- 连接数据库
- Agent
- Executor
- Validator
