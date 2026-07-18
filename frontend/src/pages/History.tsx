import React from "react";
import { Typography, Empty } from "antd";

const { Title, Text } = Typography;

const History: React.FC = () => {
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: 24 }}>
      <Title level={4} style={{ marginBottom: 16 }}>历史记录</Title>
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Empty description="暂无历史记录" />
      </div>
    </div>
  );
};

export default History;
