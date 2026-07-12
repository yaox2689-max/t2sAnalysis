# Schema Retriever

完成：

- SchemaRetriever 类
- 双路召回：FAISS 向量检索 + 关键词匹配
- FK 关系扩展：加入关联表
- 构建 SchemaContext（tables, columns, relationships, sample_data）
- 排序去重，限制 Token 数
- 单元测试（Mock）

不要：

- 修改 Schema Index
- 修改 Schema Repository
- LLM 调用
- Agent
