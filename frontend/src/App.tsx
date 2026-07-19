import React, { useState, useCallback } from "react";
import { Layout, Menu } from "antd";
import {
  MessageOutlined,
  HistoryOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import Chat from "./pages/Chat";
import History from "./pages/History";
import SettingsPage from "./pages/Settings";

const { Sider, Content } = Layout;

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState("chat");
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(
    () => localStorage.getItem("session_id")
  );
  const [refreshKey, setRefreshKey] = useState(0);

  const handleSessionChange = useCallback((id: string) => {
    setCurrentSessionId(id);
    localStorage.setItem("session_id", id);
    setCurrentPage("chat");
    setRefreshKey((k) => k + 1);
  }, []);

  const handleNewSession = useCallback(() => {
    localStorage.removeItem("session_id");
    setCurrentSessionId(null);
    setRefreshKey((k) => k + 1);
  }, []);

  const handleDeleteSession = useCallback(
    (deletedId: string) => {
      if (deletedId === currentSessionId) {
        localStorage.removeItem("session_id");
        setCurrentSessionId(null);
      }
      setRefreshKey((k) => k + 1);
    },
    [currentSessionId]
  );

  const renderPage = () => {
    switch (currentPage) {
      case "history":
        return (
          <History
            onSelectSession={handleSessionChange}
            onDeleteSession={handleDeleteSession}
            refreshKey={refreshKey}
          />
        );
      case "settings":
        return <SettingsPage />;
      default:
        return (
          <Chat
            sessionId={currentSessionId}
            onNewSession={handleNewSession}
            onSessionChange={handleSessionChange}
          />
        );
    }
  };

  return (
    <Layout style={{ minHeight: "100vh", background: "#f8f9fc" }}>
      <Sider
        width={240}
        style={{
          background: "#ffffff",
          borderRight: "1px solid #e5e8ef",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Logo */}
        <div
          style={{
            height: 72,
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "0 24px",
            borderBottom: "1px solid #e5e8ef",
          }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: "linear-gradient(135deg, #0d9488, #0284c7)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 12a9 9 0 1 1-9-9" />
              <path d="M21 3v6h-6" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </div>
          <div>
            <div
              style={{
                fontFamily: "var(--font-display)",
                fontWeight: 700,
                fontSize: 15,
                color: "#1a1a2e",
                lineHeight: 1.2,
              }}
            >
              Data Analyst
            </div>
            <div
              style={{
                fontSize: 11,
                color: "#94a3b8",
                letterSpacing: 0.5,
                marginTop: 1,
              }}
            >
              AI 驱动的数据分析
            </div>
          </div>
        </div>

        {/* Navigation */}
        <Menu
          className="sidebar-menu"
          mode="inline"
          selectedKeys={[currentPage]}
          onClick={({ key }) => setCurrentPage(key)}
          style={{
            background: "transparent",
            borderRight: "none",
            padding: "12px 0",
            flex: 1,
          }}
          items={[
            { key: "chat", icon: <MessageOutlined />, label: "对话分析" },
            { key: "history", icon: <HistoryOutlined />, label: "历史记录" },
            { key: "settings", icon: <SettingOutlined />, label: "系统设置" },
          ]}
        />

        {/* Footer */}
        <div
          style={{
            padding: "16px 24px",
            borderTop: "1px solid #e5e8ef",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: "#52c41a",
                boxShadow: "0 0 6px rgba(82, 196, 26, 0.4)",
              }}
            />
            <span
              style={{
                fontSize: 12,
                color: "#94a3b8",
              }}
            >
              系统运行中
            </span>
          </div>
        </div>
      </Sider>

      <Layout style={{ background: "#f8f9fc" }}>
        <Content
          style={{
            display: "flex",
            flexDirection: "column",
            height: "100vh",
            overflow: "hidden",
          }}
        >
          {renderPage()}
        </Content>
      </Layout>
    </Layout>
  );
};

export default App;
