# SQL Generation

完成：

- prompts/sql_agent/sql_generation.md（Prompt）
- Schema Context 拼入 Prompt（动态构建）
- LLM 调用 + SQL 生成逻辑
- 单元测试（Mock LLM，验证生成 SQL 语法正确）

不要：

- 连接数据库
- 执行 SQL
- 集成 Task Analyzer（后续 PR）
- Reflection（PR #13）
