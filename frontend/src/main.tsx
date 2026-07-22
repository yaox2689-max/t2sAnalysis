import React from "react";
import ReactDOM from "react-dom/client";
import { ConfigProvider, Button, Result } from "antd";
import zhCN from "antd/locale/zh_CN";
import App from "./App";
import "./index.css";

// ── Error Boundary ──────────────────────────────────────
interface ErrorBoundaryState {
  hasError: boolean;
}

class ErrorBoundary extends React.Component<
  React.PropsWithChildren,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("Uncaught error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh" }}>
          <Result
            status="error"
            title="页面出错了"
            subTitle="发生了意外错误，请刷新页面重试"
            extra={
              <Button type="primary" onClick={() => window.location.reload()}>
                刷新页面
              </Button>
            }
          />
        </div>
      );
    }
    return this.props.children;
  }
}

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
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </ConfigProvider>
  </React.StrictMode>,
);
