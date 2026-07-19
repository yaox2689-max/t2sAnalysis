import React, { useState, useRef, useEffect, useCallback } from "react";
import { Input, Button, Spin, Collapse, Table, Typography } from "antd";
import {
  SendOutlined,
  LoadingOutlined,
  DatabaseOutlined,
  BarChartOutlined,
  BulbOutlined,
  RocketOutlined,
  SearchOutlined,
  LineChartOutlined,
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

const SUGGESTIONS = [
  {
    icon: <BarChartOutlined />,
    text: "各品类的销售总额排名",
    desc: "品类分析",
  },
  {
    icon: <LineChartOutlined />,
    text: "最近6个月的月度销售趋势",
    desc: "趋势分析",
  },
  {
    icon: <SearchOutlined />,
    text: "订单量最多的前10个州",
    desc: "地区分析",
  },
];

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

  return (
    <div
      ref={chartRef}
      style={{
        width: "100%",
        height: 380,
        borderRadius: 10,
        overflow: "hidden",
      }}
    />
  );
};

// ── Typing Indicator ───────────────────────────────────

const TypingIndicator: React.FC = () => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      gap: 10,
      padding: "20px 24px",
      background: "#ffffff",
      border: "1px solid #e5e8ef",
      borderLeft: "3px solid #0d9488",
      borderRadius: "2px 14px 14px 2px",
      boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
    }}
  >
    <div style={{ display: "flex", gap: 5, alignItems: "center" }}>
      <span className="typing-dot" />
      <span className="typing-dot" />
      <span className="typing-dot" />
    </div>
    <Text style={{ color: "#64748b", fontSize: 13.5 }}>
      AI 正在分析您的问题
    </Text>
  </div>
);

// ── Message display ────────────────────────────────────

const AssistantMessage: React.FC<{ msg: MessageInfo }> = ({ msg }) => {
  return (
    <div className="assistant-card animate-fade-up">
      {msg.sql_text && (
        <Collapse
          ghost
          size="small"
          items={[
            {
              key: "sql",
              label: (
                <span
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    color: "#0d9488",
                    fontSize: 13,
                    fontWeight: 600,
                    letterSpacing: 0.3,
                  }}
                >
                  <DatabaseOutlined />
                  SQL 查询
                </span>
              ),
              children: <pre className="sql-block">{msg.sql_text}</pre>,
            },
          ]}
          style={{ marginBottom: 16 }}
        />
      )}

      {msg.columns &&
        msg.columns.length > 0 &&
        msg.rows_data &&
        msg.rows_data.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 10,
              }}
            >
              <BarChartOutlined style={{ color: "#f59e0b" }} />
              <Text
                strong
                style={{
                  fontSize: 13,
                  color: "#64748b",
                  letterSpacing: 0.3,
                }}
              >
                查询结果
              </Text>
              <span
                style={{
                  background: "rgba(245, 158, 11, 0.1)",
                  color: "#d97706",
                  fontSize: 11,
                  fontWeight: 600,
                  padding: "2px 8px",
                  borderRadius: 10,
                }}
              >
                {msg.rows_data.length} 行
              </span>
            </div>
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
              pagination={
                msg.rows_data.length > 20
                  ? { pageSize: 20, size: "small" }
                  : false
              }
              scroll={{ x: "max-content" }}
              style={{ borderRadius: 10, overflow: "hidden" }}
            />
          </div>
        )}

      {msg.chart_type &&
        msg.echarts_option &&
        Object.keys(msg.echarts_option).length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 10,
              }}
            >
              <LineChartOutlined style={{ color: "#0d9488" }} />
              <Text
                strong
                style={{
                  fontSize: 13,
                  color: "#64748b",
                  letterSpacing: 0.3,
                }}
              >
                数据可视化
              </Text>
              <span
                style={{
                  background: "rgba(13, 148, 136, 0.1)",
                  color: "#0d9488",
                  fontSize: 11,
                  fontWeight: 600,
                  padding: "2px 8px",
                  borderRadius: 10,
                }}
              >
                {msg.chart_type}
              </span>
            </div>
            <EChart option={msg.echarts_option} />
          </div>
        )}

      {msg.insight && (
        <div
          style={{
            background: "linear-gradient(135deg, rgba(13,148,136,0.05), rgba(2,132,199,0.03))",
            borderLeft: "3px solid #0d9488",
            borderRadius: "2px 10px 10px 2px",
            padding: "14px 20px",
            marginBottom: 12,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: 8,
            }}
          >
            <BulbOutlined style={{ color: "#0d9488", fontSize: 14 }} />
            <Text
              strong
              style={{
                fontSize: 13,
                color: "#0d9488",
                letterSpacing: 0.3,
              }}
            >
              业务洞察
            </Text>
          </div>
          <Paragraph
            style={{
              margin: 0,
              fontSize: 14,
              lineHeight: 1.7,
              color: "#1a1a2e",
            }}
          >
            {msg.insight}
          </Paragraph>
        </div>
      )}

      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          paddingTop: 8,
          borderTop: "1px solid #f0f2f5",
        }}
      >
        <Text style={{ fontSize: 11.5, color: "#94a3b8", letterSpacing: 0.3 }}>
          耗时 {(msg.elapsed_ms! / 1000).toFixed(1)}s
        </Text>
      </div>
    </div>
  );
};

// ── Welcome Screen ─────────────────────────────────────

const WelcomeScreen: React.FC<{ onSend: (text: string) => void }> = ({
  onSend,
}) => (
  <div
    className="welcome-bg"
    style={{
      flex: 1,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      padding: "48px 32px",
      position: "relative",
    }}
  >
    <div style={{ position: "relative", zIndex: 1, textAlign: "center" }}>
      <div
        className="animate-fade-up"
        style={{
          fontFamily: "var(--font-display)",
          fontSize: 32,
          fontWeight: 700,
          color: "#1a1a2e",
          marginBottom: 8,
          letterSpacing: -0.5,
        }}
      >
        AI Data Analyst
      </div>
      <div
        className="animate-fade-up stagger-1"
        style={{
          fontSize: 15,
          color: "#64748b",
          marginBottom: 48,
          lineHeight: 1.6,
        }}
      >
        用自然语言提问，获取数据洞察
      </div>

      <div
        style={{
          display: "flex",
          gap: 16,
          maxWidth: 720,
          width: "100%",
        }}
      >
        {SUGGESTIONS.map((s, i) => (
          <div
            key={i}
            className={`suggestion-card animate-fade-up stagger-${i + 2}`}
            onClick={() => onSend(s.text)}
            style={{ flex: 1 }}
          >
            <div
              style={{
                fontSize: 22,
                color: "#0d9488",
                marginBottom: 12,
              }}
            >
              {s.icon}
            </div>
            <div
              style={{
                fontSize: 11,
                color: "#94a3b8",
                marginBottom: 6,
                letterSpacing: 0.5,
              }}
            >
              {s.desc}
            </div>
            <div
              style={{
                fontSize: 14,
                color: "#1a1a2e",
                lineHeight: 1.5,
              }}
            >
              {s.text}
            </div>
          </div>
        ))}
      </div>
    </div>
  </div>
);

// ── Chat component ─────────────────────────────────────

interface ChatProps {
  sessionId: string | null;
  onNewSession: () => void;
  onSessionChange: (id: string) => void;
}

const Chat: React.FC<ChatProps> = ({
  sessionId,
  onNewSession,
  onSessionChange,
}) => {
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
  }, [messages, loading]);

  useEffect(() => {
    const init = async () => {
      setInitLoading(true);
      let sid = sessionId;
      if (!sid) {
        const res = await createSession();
        sid = res.session_id;
        onSessionChange(sid);
      } else {
        const res = await getSessionMessages(sid);
        setMessages(res.messages);
      }
      setInitLoading(false);
    };
    init();
  }, [sessionId]);

  const handleSend = useCallback(
    async (text?: string) => {
      const question = (text ?? input).trim();
      if (!question || loading || !sessionId) return;

      setInput("");
      setLoading(true);

      try {
        const res = await sendChat({ question, session_id: sessionId });
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
    },
    [input, loading, sessionId]
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (initLoading) {
    return (
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#f8f9fc",
        }}
      >
        <Spin size="large" />
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
          gap: 20,
          background: "#f8f9fc",
        }}
      >
        <RocketOutlined style={{ fontSize: 40, color: "#94a3b8" }} />
        <Text style={{ color: "#64748b" }}>暂无对话</Text>
        <Button
          type="primary"
          icon={<RocketOutlined />}
          onClick={onNewSession}
          style={{
            background: "linear-gradient(135deg, #0d9488, #0284c7)",
            border: "none",
            borderRadius: 10,
            fontWeight: 600,
            height: 40,
            padding: "0 24px",
          }}
        >
          开始新对话
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
        background: "#f8f9fc",
      }}
    >
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "24px 32px",
        }}
      >
        {messages.length === 0 && !loading && (
          <WelcomeScreen onSend={handleSend} />
        )}

        {messages.map((msg, idx) => (
          <div
            key={msg.id}
            className="animate-fade-up"
            style={{
              marginBottom: 20,
              maxWidth: 880,
              marginLeft: msg.role === "user" ? "auto" : undefined,
              animationDelay: `${Math.min(idx * 0.05, 0.3)}s`,
            }}
          >
            {msg.role === "user" && (
              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  marginBottom: 8,
                }}
              >
                <div className="user-bubble-wrap">
                  <div className="user-bubble">{msg.content}</div>
                </div>
              </div>
            )}
            {msg.role === "assistant" && <AssistantMessage msg={msg} />}
          </div>
        ))}

        {loading && (
          <div style={{ maxWidth: 880, marginBottom: 20 }}>
            <TypingIndicator />
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="glass-input-area" style={{ padding: "16px 32px 20px" }}>
        <div
          style={{
            display: "flex",
            gap: 10,
            maxWidth: 880,
            margin: "0 auto",
            alignItems: "flex-end",
          }}
        >
          <TextArea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入你的业务问题，例如「各品类的销售额排名」..."
            autoSize={{ minRows: 1, maxRows: 4 }}
            style={{ flex: 1, fontSize: 14.5 }}
            disabled={loading}
          />
          <Button
            className="send-btn"
            type="primary"
            icon={loading ? <LoadingOutlined /> : <SendOutlined />}
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
          >
            发送
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Chat;
