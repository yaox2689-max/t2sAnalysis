# 数据集初始化

完成：

- schema.sql（8 张表：orders, products, customers, payments, reviews, order_items, sellers, product_category）
- init_db.py（建表 + 导入 + 校验）
- README.md（数据获取说明）
- 每张表行数校验

不要：

- 自动下载数据
- 创建只读用户
- 修改 backend/app/*
- 创建 API
- 涉及 Agent

---

## Definition of Done

- [ ] schema.sql 可独立执行
- [ ] init_db.py 可重复运行（幂等）
- [ ] 八张表创建成功
- [ ] 数据导入成功
- [ ] 每张表行数校验通过
- [ ] 不修改 backend/app/*
- [ ] 不创建 API
- [ ] 不涉及 Agent
