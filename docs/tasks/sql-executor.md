# SQL Executor

完成：

- models/query.py：QueryResult（Pydantic BaseModel）
- SafeExecutor 类
- asyncio.timeout 超时控制（config.SQL_TIMEOUT）
- fetchmany(max_rows+1) 行数限制（config.SQL_MAX_ROWS）
- 截断通知 truncated
- 执行时间 elapsed_ms
- 异常包装（DatabaseError, TimeoutError, ExecutionError）
- 单元测试

不要：

- SQL 校验（那是 SQL Validator 的事）
- Agent
- 图表
- 洞察
- 修改 Database.execute()
