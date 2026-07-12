# Schema Index

完成：

- EmbeddingProvider 接口（Protocol，依赖注入）
- TableMetadata / ColumnMetadata 数据模型
- SchemaIndex 类（build, save, load, search）
- FAISS 索引构建（表级 + 字段级）
- 索引持久化（.faiss + .json，可重复构建，顺序稳定）
- 单元测试（Mock Repository + Mock EmbeddingProvider）

不要：

- 实现具体 Embedding 模型（sentence-transformers / OpenAI / 其他）
- 检索逻辑（那是 Schema Retriever 的事）
- LLM 调用
- Agent
- 修改 Schema Repository
