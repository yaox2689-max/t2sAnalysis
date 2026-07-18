import React, { useState, useRef, useEffect, useCallback } from "react";
import { Input, Button, Spin, Collapse, Table, Tag, Typography } from "antd";
import {
  SendOutlined,
  LoadingOutlined,
  DatabaseOutlined,
  BarChartOutlined,
  CommentOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import * as echarts from "echarts";
import {
  sendChat,
  createSession,
  getSessionMessages,
  ChatResponse,
  MessageInfo,
} from "../services/api";

const { TextArea } = Input;
const { Text, Paragraph } = Typography;

// ── ECharts component ──────────────────────────────────

const EChart: React.FC<{ option: Record<string, unknown> }> = ({ option }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;
    if (!instanceRef.current) {
      instanceRef.current = echarts.init(chartRef.current);
    }
    instanceRef.current.setOption(option, true);
    return () => {
      instanceRef.current?.dispose();
      instanceRef.current = null;
    };
  }, [option]);

  return <div ref={chartRef} style={{ width: "100%", height: 360 }} />;
};

// ── Message display ────────────────────────────────────

const AssistantMessage: React.FC<{ msg: MessageInfo }> = ({ msg }) => {
  return (
    <div
      style={{
        background: "#fafafa",
        border: "1px solid #f0f0f0",
        borderRadius: 8,
        padding: 16,
      }}
    >
      {msg.sql_text && (
        <Collapse
          ghost
          size="small"
          items={[
            {
              key: "sql",
              label: (
                <span>
                  <DatabaseOutlined style={{ marginRight: 6 }} />
                  查看 SQL
                </span>
              ),
              children: (
                <pre
                  style={{
                    background: "#1e1e1e",
                    color: "#d4d4d4",
                    padding: 12,
                    borderRadius: 6,
                    fontSize: 13,
                    overflowX: "auto",
                    margin: 0,
                  }}
                >
                  {msg.sql_text}
                </pre>
              ),
            },
          ]}
          style={{ marginBottom: 12 }}
        />
      )}

      {msg.columns && msg.columns.length > 0 && msg.rows_data && msg.rows_data.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <Text strong style={{ display: "block", marginBottom: 8 }}>
            <BarChartOutlined style={{ marginRight: 6 }} />
            查询结果 ({msg.rows_data.length} 行)
          </Text>
          <Table
            dataSource={msg.rows_data.map((r, i) => ({ ...r, _key: i }))}
            columns={msg.columns.map((col) => ({
              title: col,
              dataIndex: col,
              key: col,
              ellipsis: true,
            }))}
            rowKey="_key"
            size="small"
            pagination={msg.rows_data.length > 20 ? { pageSize: 20 } : false}
            scroll={{ x: "max-content" }}
            style={{ fontSize: 13 }}
          />
        </div>
      )}

      {msg.chart_type && msg.echarts_option && Object.keys(msg.echarts_option).length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <Text strong style={{ display: "block", marginBottom: 8 }}>
            <BarChartOutlined style={{ marginRight: 6 }} />
            图表 ({msg.chart_type})
          </Text>
          <EChart option={msg.echarts_option} />
        </div>
      )}

      {msg.insight && (
        <div
          style={{
            background: "#f6ffed",
            border: "1px solid #b7eb8f",
            borderRadius: 6,
            padding: "12px 16px",
          }}
        >
          <Text strong>
            <CommentOutlined style={{ marginRight: 6 }} />
            业务洞察
          </Text>
          <Paragraph style={{ margin: "8px 0 0", fontSize: 14 }}>
            {msg.insight}
          </Paragraph>
        </div>
      )}

      <div style={{ textAlign: "right", marginTop: 8 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          耗时: {msg.elapsed_ms}ms
        </Text>
      </div>
    </div>
  );
};

// ── Chat component ─────────────────────────────────────

interface ChatProps {
  sessionId: string | null;
  onNewSession: () => void;
  onSessionChange: (id: string) => void;
}

const Chat: React.FC<ChatProps> = ({ sessionId, onNewSession, onSessionChange }) => {
  const [messages, setMessages] = useState<MessageInfo[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [initLoading, setInitLoading] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize or load session
  useEffect(() => {
    const init = async () => {
      setInitLoading(true);
      let sid = sessionId;
      if (!sid) {
        // First time — create a new session
        const res = await createSession();
        sid = res.session_id;
        onSessionChange(sid);
      } else {
        // Load existing messages
        const res = await getSessionMessages(sid);
        setMessages(res.messages);
      }
      setInitLoading(false);
    };
    init();
  }, [sessionId]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || loading || !sessionId) return;

    setInput("");
    setLoading(true);

    try {
      const res = await sendChat({ question, session_id: sessionId });
      // Reload messages from the session
      const updated = await getSessionMessages(sessionId);
      setMessages(updated.messages);
      if (res.error) {
        console.error("Chat error:", res.error);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "请求失败";
      console.error("Send error:", msg);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (initLoading) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Spin tip="加载中..." />
      </div>
    );
  }

  if (!sessionId) {
    return (
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
        <Text type="secondary">暂无对话</Text>
        <Button type="primary" icon={<PlusOutlined />} onClick={onNewSession}>
          新建对话
        </Button>
      </div>
    );
  }

  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        height: "100vh",
      }}
    >
      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "24px 32px" }}>
        {messages.length === 0 && !loading && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              color: "#999",
            }}
          >
            <Text style={{ fontSize: 16, marginBottom: 8 }}>欢迎使用 AI Data Analyst</Text>
            <Text>输入业务问题，我将为您分析数据</Text>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} style={{ marginBottom: 20, maxWidth: 900 }}>
            {msg.role === "user" && (
              <div style={{ textAlign: "right", marginBottom: 8 }}>
                <Tag color="blue" style={{ fontSize: 14, padding: "4px 12px" }}>
                  {msg.content}
                </Tag>
              </div>
            )}
            {msg.role === "assistant" && <AssistantMessage msg={msg} />}
          </div>
        ))}

        {loading && (
          <div style={{ textAlign: "center", padding: 20 }}>
            <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} />
            <Text type="secondary" style={{ display: "block", marginTop: 8 }}>
              AI 正在分析...
            </Text>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div
        style={{
          borderTop: "1px solid #f0f0f0",
          padding: "16px 32px",
          background: "#fff",
        }}
      >
        <div style={{ display: "flex", gap: 8, maxWidth: 900, margin: "0 auto" }}>
          <TextArea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="请输入你的业务问题..."
            autoSize={{ minRows: 1, maxRows: 4 }}
            style={{ flex: 1, fontSize: 14, borderRadius: 6 }}
            disabled={loading}
          />
          <Button
            type="primary"
            icon={loading ? <LoadingOutlined /> : <SendOutlined />}
            onClick={handleSend}
            disabled={loading || !input.trim()}
            style={{ height: "auto", borderRadius: 6, padding: "4px 20px" }}
          >
            发送
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Chat;
