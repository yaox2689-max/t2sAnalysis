import React from "react";
import { Layout, Menu } from "antd";
import {
  MessageOutlined,
  BarChartOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import Chat from "./pages/Chat";

const { Sider, Content } = Layout;

const App: React.FC = () => {
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
          defaultSelectedKeys={["chat"]}
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
          <Chat />
        </Content>
      </Layout>
    </Layout>
  );
};

export default App;
