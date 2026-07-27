import React, { useCallback, useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  Outlet,
  useNavigate,
  useLocation,
} from "react-router-dom";
import { Layout, Menu, Button } from "antd";
import {
  MessageOutlined,
  HistoryOutlined,
  SettingOutlined,
  LogoutOutlined,
  DatabaseOutlined,
} from "@ant-design/icons";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import Login from "./pages/Login";
import Chat from "./pages/Chat";
import History from "./pages/History";
import SettingsPage from "./pages/Settings";
import ConnectDatabase from "./pages/ConnectDatabase";

const { Sider, Content } = Layout;

const AppLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [refreshKey, setRefreshKey] = useState(0);

  const handleSessionChange = useCallback(
    (id: string) => {
      navigate(`/chat/${id}`);
      setRefreshKey((k) => k + 1);
    },
    [navigate]
  );

  const handleNewSession = useCallback(() => {
    navigate("/chat");
    setRefreshKey((k) => k + 1);
  }, [navigate]);

  const handleDeleteSession = useCallback((_deletedId: string) => {
    setRefreshKey((k) => k + 1);
  }, []);

  const selectedKey = location.pathname.startsWith("/history")
    ? "history"
    : location.pathname.startsWith("/connections")
    ? "connections"
    : location.pathname.startsWith("/settings")
    ? "settings"
    : "chat";

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
          selectedKeys={[selectedKey]}
          onClick={({ key }) => navigate(`/${key}`)}
          style={{
            background: "transparent",
            borderRight: "none",
            padding: "12px 0",
            flex: 1,
          }}
          items={[
            { key: "chat", icon: <MessageOutlined />, label: "对话分析" },
            { key: "history", icon: <HistoryOutlined />, label: "历史记录" },
            { key: "connections", icon: <DatabaseOutlined />, label: "数据库连接" },
            { key: "settings", icon: <SettingOutlined />, label: "系统设置" },
          ]}
        />

        {/* Footer: user info + logout */}
        <div
          style={{
            padding: "12px 24px",
            borderTop: "1px solid #e5e8ef",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: "#52c41a",
                  boxShadow: "0 0 6px rgba(82, 196, 26, 0.4)",
                }}
              />
              <span style={{ fontSize: 12, color: "#64748b" }}>
                {user?.display_name || user?.username}
              </span>
            </div>
            <Button
              type="text"
              size="small"
              icon={<LogoutOutlined />}
              onClick={logout}
              style={{ color: "#94a3b8" }}
            />
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
          <Outlet
            context={{ refreshKey, onSelectSession: handleSessionChange, onDeleteSession: handleDeleteSession, handleSessionChange, handleNewSession }}
          />
        </Content>
      </Layout>
    </Layout>
  );
};

const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

const AppContent: React.FC = () => {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Login />;
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<AppLayout />}>
          <Route index element={<Navigate to="/chat" replace />} />
          <Route path="chat" element={<Chat />} />
          <Route path="chat/:sessionId" element={<Chat />} />
          <Route path="history" element={<History />} />
          <Route path="connections" element={<ConnectDatabase />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
