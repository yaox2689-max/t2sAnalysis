import React from "react";
import { PaperClipOutlined, SearchOutlined, BarChartOutlined } from "@ant-design/icons";

const SUGGESTIONS = [
  { icon: <PaperClipOutlined />, desc: "上传数据", text: "Excel / CSV 文件" },
  { icon: <SearchOutlined />, desc: "提出问题", text: "用自然语言描述分析需求" },
  { icon: <BarChartOutlined />, desc: "获取洞察", text: "自动生成图表和分析结论" },
];

/** Initial landing screen shown when a session has no messages yet. */
const WelcomeScreen: React.FC<{ onSend: (text: string) => void }> = ({
  onSend: _onSend,
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
        Dataset Intelligence Platform
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
        上传数据，用自然语言提问，获取洞察
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
            className={`suggestion-card animate-fade-up stagger-${i + 2}`}
            style={{ flex: 1, cursor: "default" }}
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

export default WelcomeScreen;
