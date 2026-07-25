import React, { useState } from "react";
import { Tabs, Form, Input, Button, Typography, message } from "antd";
import { UserOutlined, LockOutlined } from "@ant-design/icons";
import { useAuth } from "../contexts/AuthContext";

const { Text } = Typography;

const Login: React.FC = () => {
  const { login, register } = useAuth();
  const [loading, setLoading] = useState(false);

  const handleLogin = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      await login(values.username, values.password);
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : "登录失败");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (values: {
    username: string;
    password: string;
    display_name: string;
  }) => {
    setLoading(true);
    try {
      await register(values.username, values.password, values.display_name);
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : "注册失败");
    } finally {
      setLoading(false);
    }
  };

  const items = [
    {
      key: "login",
      label: "登录",
      children: (
        <Form onFinish={handleLogin} layout="vertical" size="large">
          <Form.Item name="username" rules={[{ required: true, message: "请输入用户名" }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: "请输入密码" }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登录
            </Button>
          </Form.Item>
        </Form>
      ),
    },
    {
      key: "register",
      label: "注册",
      children: (
        <Form onFinish={handleRegister} layout="vertical" size="large">
          <Form.Item name="username" rules={[{ required: true, message: "请输入用户名" }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" />
          </Form.Item>
          <Form.Item name="display_name">
            <Input prefix={<UserOutlined />} placeholder="显示名称（可选）" />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[
              { required: true, message: "请输入密码" },
              { min: 6, message: "密码至少6位" },
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              注册
            </Button>
          </Form.Item>
        </Form>
      ),
    },
  ];

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #f8f9fc 0%, #e8f4f8 100%)",
      }}
    >
      <div
        style={{
          width: 400,
          background: "#fff",
          borderRadius: 16,
          padding: "40px 32px 24px",
          boxShadow: "0 8px 32px rgba(0,0,0,0.08)",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: 12,
              background: "linear-gradient(135deg, #0d9488, #0284c7)",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: 16,
            }}
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2.2"
            >
              <path d="M21 12a9 9 0 1 1-9-9" />
              <path d="M21 3v6h-6" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </div>
          <Text strong style={{ fontSize: 20, color: "#1a1a2e" }}>
            Data Analyst
          </Text>
          <div style={{ fontSize: 13, color: "#94a3b8", marginTop: 4 }}>
            AI 驱动的数据分析平台
          </div>
        </div>
        <Tabs items={items} centered />
      </div>
    </div>
  );
};

export default Login;
