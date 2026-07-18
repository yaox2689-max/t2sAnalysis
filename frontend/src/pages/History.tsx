import React, { useState, useEffect } from "react";
import { List, Typography, Button, Empty, Spin, Space } from "antd";
import {
  MessageOutlined,
  PlusOutlined,
  RightOutlined,
} from "@ant-design/icons";
import { listSessions, createSession, SessionInfo } from "../services/api";

const { Text, Title } = Typography;

interface HistoryProps {
  onSelectSession: (id: string) => void;
  refreshKey: number;
}

const History: React.FC<HistoryProps> = ({ onSelectSession, refreshKey }) => {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const loadSessions = async () => {
    setLoading(true);
    try {
      const res = await listSessions();
      setSessions(res.sessions);
    } catch (err) {
      console.error("Failed to load sessions:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, [refreshKey]);

  const handleNew = async () => {
    const res = await createSession();
    onSelectSession(res.session_id);
  };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: 24 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <Title level={4} style={{ margin: 0 }}>
          历史记录
        </Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleNew}>
          新建对话
        </Button>
      </div>

      {loading ? (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Spin />
        </div>
      ) : sessions.length === 0 ? (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Empty description="暂无历史记录" />
        </div>
      ) : (
        <List
          dataSource={sessions}
          renderItem={(item) => (
            <List.Item
              onClick={() => onSelectSession(item.id)}
              style={{ cursor: "pointer", padding: "12px 16px" }}
              actions={[<RightOutlined key="go" />]}
            >
              <List.Item.Meta
                avatar={<MessageOutlined style={{ fontSize: 18, color: "#1677ff" }} />}
                title={<Text strong>{item.title}</Text>}
                description={
                  <Space size="small">
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {new Date(item.updated_at).toLocaleString("zh-CN")}
                    </Text>
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      )}
    </div>
  );
};

export default History;
