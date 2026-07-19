import React from "react";
import { Typography, Tag } from "antd";
import {
  RobotOutlined,
  ApiOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  ReloadOutlined,
  CloudServerOutlined,
  SearchOutlined,
} from "@ant-design/icons";

const { Title, Text } = Typography;

interface SettingItemProps {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  accent?: string;
}

const SettingItem: React.FC<SettingItemProps> = ({
  icon,
  label,
  value,
  accent = "#0d9488",
}) => (
  <div
    className="animate-fade-up"
    style={{
      background: "#ffffff",
      border: "1px solid #e5e8ef",
      borderRadius: 14,
      padding: "20px 24px",
      display: "flex",
      alignItems: "center",
      gap: 16,
      boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
      transition: "box-shadow 0.3s ease, border-color 0.3s ease",
    }}
    onMouseEnter={(e) => {
      (e.currentTarget as HTMLElement).style.boxShadow = "0 4px 12px rgba(0,0,0,0.06)";
      (e.currentTarget as HTMLElement).style.borderColor = "rgba(13,148,136,0.25)";
    }}
    onMouseLeave={(e) => {
      (e.currentTarget as HTMLElement).style.boxShadow = "0 1px 2px rgba(0,0,0,0.04)";
      (e.currentTarget as HTMLElement).style.borderColor = "#e5e8ef";
    }}
  >
    <div
      style={{
        width: 44,
        height: 44,
        borderRadius: 12,
        background: `${accent}12`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 18,
        color: accent,
        flexShrink: 0,
      }}
    >
      {icon}
    </div>
    <div style={{ flex: 1 }}>
      <Text style={{ fontSize: 12, color: "#94a3b8", letterSpacing: 0.5 }}>
        {label}
      </Text>
      <div
        style={{
          fontSize: 15,
          color: "#1a1a2e",
          fontWeight: 500,
          marginTop: 4,
        }}
      >
        {value}
      </div>
    </div>
  </div>
);

const Settings: React.FC = () => {
  return (
    <div
      style={{
        flex: 1,
        padding: "32px 40px",
        background: "#f8f9fc",
        overflowY: "auto",
      }}
    >
      <div style={{ marginBottom: 32 }}>
        <Title
          level={3}
          style={{
            margin: 0,
            fontFamily: "var(--font-display)",
            fontWeight: 700,
            letterSpacing: -0.3,
          }}
        >
          系统设置
        </Title>
        <Text style={{ color: "#94a3b8", fontSize: 13 }}>
          当前系统配置信息
        </Text>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
          gap: 14,
          maxWidth: 900,
        }}
      >
        <SettingItem
          icon={<RobotOutlined />}
          label="LLM 模型"
          value="DeepSeek Chat"
          accent="#0d9488"
        />
        <SettingItem
          icon={<ApiOutlined />}
          label="API 端点"
          value={
            <Tag
              style={{
                background: "rgba(13, 148, 136, 0.08)",
                color: "#0d9488",
                border: "1px solid rgba(13, 148, 136, 0.2)",
                borderRadius: 6,
                fontFamily: "var(--font-mono)",
                fontSize: 12,
              }}
            >
              api.deepseek.com
            </Tag>
          }
          accent="#0d9488"
        />
        <SettingItem
          icon={<ClockCircleOutlined />}
          label="SQL 超时"
          value="10 秒"
          accent="#f59e0b"
        />
        <SettingItem
          icon={<DatabaseOutlined />}
          label="最大返回行数"
          value="500 行"
          accent="#f59e0b"
        />
        <SettingItem
          icon={<ReloadOutlined />}
          label="最大重试次数"
          value="3 次"
          accent="#8b5cf6"
        />
        <SettingItem
          icon={<CloudServerOutlined />}
          label="数据库"
          value="MySQL 8.0 (Olist)"
          accent="#3b82f6"
        />
        <SettingItem
          icon={<SearchOutlined />}
          label="Schema 检索"
          value="FAISS + 关键词"
          accent="#ec4899"
        />
      </div>
    </div>
  );
};

export default Settings;
