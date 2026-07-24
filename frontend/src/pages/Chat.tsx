import React, { useState, useRef, useEffect, useCallback } from "react";
import { Input, Button, Spin, Collapse, Table, Typography, message } from "antd";
import {
  SendOutlined,
  LoadingOutlined,
  DatabaseOutlined,
  BarChartOutlined,
  BulbOutlined,
  RocketOutlined,
  SearchOutlined,
  LineChartOutlined,
  PaperClipOutlined,
  CloseCircleOutlined,
} from "@ant-design/icons";
import * as echarts from "echarts/core";
import { BarChart, LineChart, PieChart, ScatterChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  TitleComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  BarChart,
  LineChart,
  PieChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  TitleComponent,
  CanvasRenderer,
]);
import {
  sendChat,
  createSession,
  getSessionMessages,
  uploadDataset,
  deleteDataset,
  ChatResponse,
  MessageInfo,
  DatasetPreview,
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
    const instance = echarts.init(chartRef.current);
    instanceRef.current = instance;

    const ro = new ResizeObserver(() => instance.resize());
    ro.observe(chartRef.current);

    return () => {
      ro.disconnect();
      instance.dispose();
      instanceRef.current = null;
    };
  }, []);

  useEffect(() => {
    instanceRef.current?.setOption(option, true);
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
          耗时 {((msg.elapsed_ms ?? 0) / 1000).toFixed(1)}s
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
            key={s.text}
            role="button"
            tabIndex={0}
            className={`suggestion-card animate-fade-up stagger-${i + 2}`}
            onClick={() => onSend(s.text)}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onSend(s.text); }}
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
  const [datasets, setDatasets] = useState<DatasetPreview[]>([]);
  const [uploading, setUploading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const loadingRef = useRef(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const inputRef = useRef(input);
  inputRef.current = input;
  const sessionIdRef = useRef(sessionId);
  sessionIdRef.current = sessionId;

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, scrollToBottom]);

  useEffect(() => {
    const controller = new AbortController();
    const init = async () => {
      setInitLoading(true);
      try {
        let sid = sessionId;
        if (!sid) {
          const res = await createSession();
          if (controller.signal.aborted) return;
          sid = res.session_id;
          onSessionChange(sid);
        } else {
          const res = await getSessionMessages(sid);
          if (controller.signal.aborted) return;
          setMessages(res.messages);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          console.error("Init error:", err);
        }
      } finally {
        if (!controller.signal.aborted) {
          setInitLoading(false);
        }
      }
    };
    init();
    return () => controller.abort();
  }, [sessionId, onSessionChange]);

  const sendAbortRef = useRef<AbortController | null>(null);

  const handleSend = useCallback(
    async (text?: string) => {
      const question = (text ?? inputRef.current).trim();
      const sid = sessionIdRef.current;
      if (!question || loadingRef.current || !sid) return;

      setInput("");
      loadingRef.current = true;
      setLoading(true);

      const controller = new AbortController();
      sendAbortRef.current = controller;

      try {
        const res = await sendChat({ question, session_id: sid });
        if (controller.signal.aborted) return;
        if (res.error) {
          message.error(res.error);
        }
        const updated = await getSessionMessages(sid);
        if (controller.signal.aborted) return;
        setMessages(updated.messages);
      } catch (err: unknown) {
        if (!controller.signal.aborted) {
          const msg = err instanceof Error ? err.message : "请求失败，请稍后重试";
          message.error(msg);
        }
      } finally {
        if (!controller.signal.aborted) {
          loadingRef.current = false;
          setLoading(false);
        }
      }
    },
    []
  );

  // Cleanup send request on unmount
  useEffect(() => {
    return () => sendAbortRef.current?.abort();
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  // ── Upload handlers ───────────────────────────────────

  const handleFileUpload = useCallback(
    async (file: File) => {
      const sid = sessionIdRef.current;
      if (!sid || uploading) return;

      setUploading(true);
      try {
        const res = await uploadDataset(file, sid);
        setDatasets((prev) => [...prev, ...res.datasets]);
        message.success(`已导入 ${res.count} 个数据集`);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "上传失败";
        message.error(msg);
      } finally {
        setUploading(false);
      }
    },
    [uploading]
  );

  const handleRemoveDataset = useCallback(async (tableName: string) => {
    try {
      await deleteDataset(tableName);
      setDatasets((prev) => prev.filter((d) => d.table_name !== tableName));
    } catch {
      message.error("删除失败");
    }
  }, []);

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileUpload(file);
      e.target.value = "";
    }
  };

  // ── Drag-drop ─────────────────────────────────────────

  const [dragging, setDragging] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      handleFileUpload(file);
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

      <div
        className="glass-input-area"
        style={{ padding: "16px 32px 20px" }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Dataset tags */}
        {datasets.length > 0 && (
          <div
            style={{
              maxWidth: 880,
              margin: "0 auto 8px",
              display: "flex",
              flexWrap: "wrap",
              gap: 6,
            }}
          >
            {datasets.map((ds) => (
              <span
                key={ds.table_name}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                  padding: "2px 8px",
                  background: "rgba(13, 148, 136, 0.08)",
                  border: "1px solid rgba(13, 148, 136, 0.2)",
                  borderRadius: 6,
                  fontSize: 12,
                  color: "#0d9488",
                }}
              >
                <DatabaseOutlined style={{ fontSize: 11 }} />
                {ds.name}
                <span style={{ color: "#94a3b8" }}>({ds.row_count} rows)</span>
                <CloseCircleOutlined
                  style={{ fontSize: 12, cursor: "pointer", color: "#94a3b8" }}
                  onClick={() => handleRemoveDataset(ds.table_name)}
                />
              </span>
            ))}
          </div>
        )}

        {/* Drag overlay */}
        {dragging && (
          <div
            style={{
              maxWidth: 880,
              margin: "0 auto 8px",
              padding: 20,
              border: "2px dashed #0d9488",
              borderRadius: 10,
              textAlign: "center",
              color: "#0d9488",
              fontSize: 14,
              background: "rgba(13, 148, 136, 0.04)",
            }}
          >
            拖放 Excel/CSV 文件到此处上传
          </div>
        )}

        <div
          style={{
            display: "flex",
            gap: 10,
            maxWidth: 880,
            margin: "0 auto",
            alignItems: "flex-end",
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls,.csv"
            style={{ display: "none" }}
            onChange={handleFileInputChange}
          />
          <Button
            icon={<PaperClipOutlined />}
            onClick={() => fileInputRef.current?.click()}
            disabled={loading || uploading}
            title="上传 Excel/CSV 文件"
            style={{ borderRadius: 10 }}
          />
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
