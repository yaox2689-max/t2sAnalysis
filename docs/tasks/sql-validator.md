# SQL Validator

完成：

- sqlglot AST 解析
- 阻断非 SELECT（INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE）
- 递归检查子查询
- 危险模式检测（无 WHERE 全表扫描、CROSS JOIN、左模糊 LIKE、ORDER BY RAND）
- ValidationResult(passed, risk_level, warnings)
- 单元测试

不要：

- 执行 SQL
- 生成 SQL
- Agent
