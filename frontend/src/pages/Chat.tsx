import React from "react";

const Chat: React.FC = () => {
  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        padding: 24,
      }}
    >
      {/* Messages area */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          color: "#999",
        }}
      >
        <p style={{ fontSize: 16, marginBottom: 8 }}>欢迎使用 AI Data Analyst</p>
        <p>输入业务问题，我将为您分析数据</p>
      </div>

      {/* Input area */}
      <div style={{ borderTop: "1px solid #f0f0f0", padding: "16px 0" }}>
        <div
          style={{
            display: "flex",
            gap: 8,
            maxWidth: 800,
            margin: "0 auto",
            width: "100%",
          }}
        >
          <input
            type="text"
            placeholder="请输入你的业务问题..."
            style={{
              flex: 1,
              padding: "10px 16px",
              border: "1px solid #d9d9d9",
              borderRadius: 6,
              fontSize: 14,
              outline: "none",
            }}
            onFocus={(e) => (e.target.style.borderColor = "#1677ff")}
            onBlur={(e) => (e.target.style.borderColor = "#d9d9d9")}
          />
          <button
            style={{
              padding: "10px 24px",
              background: "#1677ff",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              fontSize: 14,
              cursor: "pointer",
            }}
          >
            发送
          </button>
        </div>
      </div>
    </div>
  );
};

export default Chat;
