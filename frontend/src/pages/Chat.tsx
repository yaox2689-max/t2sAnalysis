import React, { useState, useRef, useCallback } from "react";
import { useParams, useOutletContext } from "react-router-dom";
import { Input, Button, Spin, Typography } from "antd";
import {
  SendOutlined,
  LoadingOutlined,
  RocketOutlined,
  PaperClipOutlined,
  DatabaseOutlined,
  CloseCircleOutlined,
} from "@ant-design/icons";
import AssistantMessage from "../components/AssistantMessage";
import TypingIndicator from "../components/TypingIndicator";
import WelcomeScreen from "../components/WelcomeScreen";
import { useChat } from "../hooks/useChat";
import { useFileUpload } from "../hooks/useFileUpload";

const { TextArea } = Input;
const { Text } = Typography;

// ── Chat component ─────────────────────────────────────

interface OutletContext {
  handleSessionChange: (id: string) => void;
  handleNewSession: () => void;
}

const Chat: React.FC = () => {
  const { sessionId: urlSessionId } = useParams<{ sessionId: string }>();
  const { handleSessionChange, handleNewSession } =
    useOutletContext<OutletContext>();
  const sessionId = urlSessionId || null;

  const [input, setInput] = useState("");
  const inputRef = useRef(input);
  inputRef.current = input;

  const sessionIdRef = useRef(sessionId);
  sessionIdRef.current = sessionId;

  const {
    messages,
    loading,
    progressLabel,
    initLoading,
    messagesEndRef,
    handleSend: rawSend,
  } = useChat(sessionId, handleSessionChange);

  const {
    datasets,
    uploading,
    dragging,
    fileInputRef,
    handleRemoveDataset,
    handleFileInputChange,
    handleDragOver,
    handleDragLeave,
    handleDrop,
  } = useFileUpload(sessionIdRef);

  const handleSend = useCallback(
    (text?: string) => rawSend(text, inputRef),
    [rawSend],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

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
          onClick={handleNewSession}
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
      {/* Messages area */}
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
            <TypingIndicator progressLabel={progressLabel} />
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
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
