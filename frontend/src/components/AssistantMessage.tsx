import React from "react";
import { Collapse, Table, Typography } from "antd";
import {
  DatabaseOutlined,
  BarChartOutlined,
  BulbOutlined,
  LineChartOutlined,
  AuditOutlined,
} from "@ant-design/icons";
import EChart from "./EChart";
import type { MessageInfo } from "../services/api";

const { Text, Paragraph } = Typography;

/** Renders a full assistant message card (SQL, table, chart, insight, evidence). */
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
            background:
              "linear-gradient(135deg, rgba(13,148,136,0.05), rgba(2,132,199,0.03))",
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

      {msg.evidence && msg.evidence.conclusion && (
        <div
          style={{
            background:
              "linear-gradient(135deg, rgba(245,158,11,0.05), rgba(217,119,6,0.03))",
            borderLeft: "3px solid #f59e0b",
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
            <AuditOutlined style={{ color: "#f59e0b", fontSize: 14 }} />
            <Text
              strong
              style={{
                fontSize: 13,
                color: "#d97706",
                letterSpacing: 0.3,
              }}
            >
              证据分析
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
            {msg.evidence.conclusion}
          </Paragraph>
          {msg.evidence.suggestions?.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <Text strong style={{ fontSize: 12, color: "#92400e" }}>
                建议：
              </Text>
              <ul style={{ margin: "4px 0 0 16px", padding: 0 }}>
                {msg.evidence.suggestions.map((s, i) => (
                  <li
                    key={i}
                    style={{ fontSize: 13, color: "#78350f", lineHeight: 1.6 }}
                  >
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {msg.evidence.limitations?.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <Text style={{ fontSize: 12, color: "#94a3b8" }}>
                局限性: {msg.evidence.limitations.join("; ")}
              </Text>
            </div>
          )}
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

export default AssistantMessage;
