import React, { useState, useEffect } from "react";
import { Typography, Button, Empty, Spin, Modal, message } from "antd";
import {
  MessageOutlined,
  PlusOutlined,
  DeleteOutlined,
  ClockCircleOutlined,
  RightOutlined,
} from "@ant-design/icons";
import {
  listSessions,
  createSession,
  deleteSession,
  SessionInfo,
} from "../services/api";

const { Text, Title } = Typography;

function toBeijingTime(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleString("zh-CN", {
    timeZone: "Asia/Shanghai",
    hour12: false,
  });
}

interface HistoryProps {
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  refreshKey: number;
}

const History: React.FC<HistoryProps> = ({
  onSelectSession,
  onDeleteSession,
  refreshKey,
}) => {
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
    try {
      const res = await createSession();
      onSelectSession(res.session_id);
    } catch (err) {
      console.error("Failed to create session:", err);
      message.error("创建对话失败，请稍后重试");
    }
  };

  const handleDelete = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    Modal.confirm({
      title: "确认删除",
      content: "删除后将无法恢复该对话记录，是否继续？",
      okText: "删除",
      okType: "danger",
      cancelText: "取消",
      onOk: async () => {
        try {
          await deleteSession(sessionId);
          message.success("已删除");
          onDeleteSession(sessionId);
          loadSessions();
        } catch {
          message.error("删除失败");
        }
      },
    });
  };

  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        padding: "32px 40px",
        background: "#f8f9fc",
        overflowY: "auto",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 28,
        }}
      >
        <div>
          <Title
            level={3}
            style={{
              margin: 0,
              fontFamily: "var(--font-display)",
              fontWeight: 700,
              letterSpacing: -0.3,
            }}
          >
            历史记录
          </Title>
          <Text style={{ color: "#94a3b8", fontSize: 13 }}>
            浏览和管理您的对话历史
          </Text>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleNew}
          style={{
            background: "linear-gradient(135deg, #0d9488, #0284c7)",
            border: "none",
            borderRadius: 10,
            fontWeight: 600,
            height: 40,
            padding: "0 20px",
            boxShadow: "0 2px 8px rgba(13, 148, 136, 0.25)",
            color: "#fff",
          }}
        >
          新建对话
        </Button>
      </div>

      {loading ? (
        <div
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Spin size="large" />
        </div>
      ) : sessions.length === 0 ? (
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 16,
          }}
        >
          <MessageOutlined style={{ fontSize: 48, color: "#94a3b8", opacity: 0.4 }} />
          <Empty description="暂无历史记录" />
        </div>
      ) : (
        <div style={{ maxWidth: 800 }}>
          {sessions.map((item, idx) => (
            <div
              key={item.id}
              className="history-item animate-fade-up"
              onClick={() => onSelectSession(item.id)}
              style={{ animationDelay: `${idx * 0.05}s` }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 14,
                    flex: 1,
                    minWidth: 0,
                  }}
                >
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: 10,
                      background: "linear-gradient(135deg, rgba(13,148,136,0.1), rgba(2,132,199,0.06))",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    <MessageOutlined style={{ fontSize: 16, color: "#0d9488" }} />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Text
                      strong
                      style={{
                        display: "block",
                        fontSize: 14.5,
                        color: "#1a1a2e",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {item.title}
                    </Text>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                        marginTop: 4,
                      }}
                    >
                      <ClockCircleOutlined style={{ fontSize: 11, color: "#94a3b8" }} />
                      <Text style={{ fontSize: 12, color: "#94a3b8" }}>
                        {toBeijingTime(item.updated_at)}
                      </Text>
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <Button
                    type="text"
                    danger
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={(e) => handleDelete(e, item.id)}
                    style={{ opacity: 0.5, transition: "opacity 0.2s" }}
                  />
                  <RightOutlined style={{ fontSize: 12, color: "#94a3b8", marginLeft: 4 }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default History;
