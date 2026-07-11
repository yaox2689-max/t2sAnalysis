# Database Core

完成：

- database.py（异步引擎 + Session 管理 + 连接池）
- redis.py（RedisClient：get / set / delete / exists）
- 健康检查
- 单元测试

不要：

- 业务逻辑（不涉及 session 序列化、schema cache、conversation memory）
- Schema
- Agent
- API

---

## Definition of Done

- [ ] Database / Redis 模块可独立初始化运行
- [ ] database.py 的 SQLAlchemy 引擎可正常 init
- [ ] 单元测试通过
- [ ] Ruff/Black 通过
- [ ] 没有 TODO

## 测试环境

```bash
# 启动依赖服务
docker compose up mysql redis -d

# 运行测试
pytest backend/tests/ -v
```
