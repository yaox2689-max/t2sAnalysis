import React from "react";
import { Typography, Descriptions, Tag } from "antd";

const { Title } = Typography;

const Settings: React.FC = () => {
  return (
    <div style={{ flex: 1, padding: 24 }}>
      <Title level={4} style={{ marginBottom: 16 }}>设置</Title>
      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label="LLM 模型">DeepSeek Chat</Descriptions.Item>
        <Descriptions.Item label="API 端点">
          <Tag>https://api.deepseek.com</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="SQL 超时">10 秒</Descriptions.Item>
        <Descriptions.Item label="最大返回行数">500 行</Descriptions.Item>
        <Descriptions.Item label="最大重试次数">3 次</Descriptions.Item>
        <Descriptions.Item label="数据库">MySQL 8.0 (Olist)</Descriptions.Item>
        <Descriptions.Item label="Schema 检索">FAISS + 关键词</Descriptions.Item>
      </Descriptions>
    </div>
  );
};

export default Settings;
