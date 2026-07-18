import React, { useState, useCallback } from "react";
import { Layout, Menu } from "antd";
import {
  MessageOutlined,
  BarChartOutlined,
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

  const renderPage = () => {
    switch (currentPage) {
      case "history":
        return (
          <History
            onSelectSession={handleSessionChange}
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
    <Layout style={{ minHeight: "100vh" }}>
      <Sider theme="light" width={220} style={{ borderRight: "1px solid #f0f0f0" }}>
        <div
          style={{
            height: 64,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 700,
            fontSize: 18,
            borderBottom: "1px solid #f0f0f0",
          }}
        >
          AI Data Analyst
        </div>
        <Menu
          mode="inline"
          selectedKeys={[currentPage]}
          onClick={({ key }) => setCurrentPage(key)}
          items={[
            { key: "chat", icon: <MessageOutlined />, label: "对话" },
            { key: "history", icon: <BarChartOutlined />, label: "历史记录" },
            { key: "settings", icon: <SettingOutlined />, label: "设置" },
          ]}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <Layout>
        <Content style={{ display: "flex", flexDirection: "column" }}>
          {renderPage()}
        </Content>
      </Layout>
    </Layout>
  );
};

export default App;
