import React from "react";
import ReactDOM from "react-dom/client";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: "#0d9488",
          colorBgBase: "#ffffff",
          colorBgContainer: "#ffffff",
          colorBgElevated: "#ffffff",
          colorBgLayout: "#f8f9fc",
          colorBorderSecondary: "#e5e8ef",
          colorText: "#1a1a2e",
          colorTextSecondary: "#64748b",
          colorTextTertiary: "#94a3b8",
          fontFamily:
            '"DM Sans", -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif',
          borderRadius: 10,
          fontSize: 14,
        },
        components: {
          Table: {
            colorBgContainer: "#ffffff",
            headerBg: "#f8f9fc",
            headerColor: "#64748b",
            rowHoverBg: "#f1f5f9",
            borderColor: "#e5e8ef",
          },
          Menu: {
            itemBg: "transparent",
            subMenuItemBg: "transparent",
            itemSelectedBg: "rgba(13, 148, 136, 0.08)",
            itemSelectedColor: "#0d9488",
            itemColor: "#64748b",
            itemHoverBg: "#f1f5f9",
            itemHoverColor: "#1a1a2e",
          },
          Modal: {
            contentBg: "#ffffff",
            headerBg: "#ffffff",
            titleColor: "#1a1a2e",
          },
          Input: {
            colorBgContainer: "#ffffff",
            colorBorder: "#e5e8ef",
            activeBorderColor: "#0d9488",
            hoverBorderColor: "#0d9488",
            colorTextPlaceholder: "#94a3b8",
          },
          Collapse: {
            contentBg: "transparent",
            headerBg: "transparent",
          },
          Spin: {
            colorPrimary: "#0d9488",
          },
          Tag: {
            defaultBg: "#f1f5f9",
            defaultColor: "#475569",
          },
        },
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>,
);
