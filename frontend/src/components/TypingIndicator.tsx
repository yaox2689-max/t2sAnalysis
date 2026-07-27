import React from "react";
import { Typography } from "antd";

const { Text } = Typography;

/** Animated typing dots shown while the AI is processing. */
const TypingIndicator: React.FC<{ progressLabel?: string }> = ({
  progressLabel,
}) => (
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
      {progressLabel || "AI 正在分析您的问题"}
    </Text>
  </div>
);

export default TypingIndicator;
