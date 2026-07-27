import React, { useState, useEffect } from "react";
import {
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  List,
  Modal,
  Popconfirm,
  Tag,
  Typography,
  message,
} from "antd";
import {
  PlusOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";
import {
  testConnection,
  saveConnection,
  listConnections,
  deleteConnection,
  ConnectionInfo,
} from "../services/api";

const { Text, Title } = Typography;

const ConnectDatabase: React.FC = () => {
  const [connections, setConnections] = useState<ConnectionInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const fetchConnections = async () => {
    try {
      setLoading(true);
      const data = await listConnections();
      setConnections(data.connections || []);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConnections();
  }, []);

  const handleTest = async () => {
    try {
      const values = await form.validateFields();
      setTesting(true);
      const data = await testConnection(values);
      if (data.success) {
        message.success(`连接成功，发现 ${data.count} 张表`);
      } else {
        message.error(data.error || "连接失败");
      }
    } catch {
      message.error("请填写完整连接信息");
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const data = await saveConnection(values);
      message.success(`已连接 ${data.display_name}，注册 ${data.count} 张表`);
      setModalOpen(false);
      form.resetFields();
      fetchConnections();
    } catch (err: unknown) {
      message.error(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteConnection(id);
      message.success("连接已删除");
      fetchConnections();
    } catch {
      message.error("删除失败");
    }
  };

  return (
    <div style={{ padding: 32, maxWidth: 800, margin: "0 auto" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 24,
        }}
      >
        <Title level={4} style={{ margin: 0 }}>
          数据库连接
        </Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setModalOpen(true)}
        >
          新建连接
        </Button>
      </div>

      <Text type="secondary" style={{ display: "block", marginBottom: 24 }}>
        连接外部 MySQL 数据库，系统将自动发现表结构用于 AI 分析。所有连接仅支持只读查询。
      </Text>

      <List
        loading={loading}
        dataSource={connections}
        locale={{ emptyText: "暂无数据库连接" }}
        renderItem={(item) => (
          <Card style={{ marginBottom: 12 }} size="small">
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <DatabaseOutlined style={{ marginRight: 8, color: "#0d9488" }} />
                <Text strong>{item.display_name}</Text>
                <Text type="secondary" style={{ marginLeft: 12 }}>
                  {item.host}:{item.port}/{item.database}
                </Text>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Tag icon={<CheckCircleOutlined />} color="success">
                  {item.table_count} 张表
                </Tag>
                <Popconfirm
                  title="确定删除此连接？"
                  description="关联的表将从数据目录中移除"
                  onConfirm={() => handleDelete(item.id)}
                >
                  <Button
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    size="small"
                  />
                </Popconfirm>
              </div>
            </div>
          </Card>
        )}
      />

      <Modal
        title="新建 MySQL 连接"
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false);
          form.resetFields();
        }}
        footer={[
          <Button key="test" onClick={handleTest} loading={testing}>
            测试连接
          </Button>,
          <Button
            key="save"
            type="primary"
            onClick={handleSave}
            loading={saving}
          >
            保存
          </Button>,
        ]}
        width={480}
      >
        <Form form={form} layout="vertical" initialValues={{ port: 3306 }}>
          <Form.Item
            name="display_name"
            label="连接名称"
            rules={[{ required: true, message: "请输入名称" }]}
          >
            <Input placeholder="例如：生产数据库" />
          </Form.Item>
          <div style={{ display: "flex", gap: 12 }}>
            <Form.Item
              name="host"
              label="Host"
              rules={[{ required: true }]}
              style={{ flex: 1 }}
            >
              <Input placeholder="localhost" />
            </Form.Item>
            <Form.Item name="port" label="Port" style={{ width: 100 }}>
              <InputNumber style={{ width: "100%" }} />
            </Form.Item>
          </div>
          <Form.Item
            name="database"
            label="Database"
            rules={[{ required: true }]}
          >
            <Input placeholder="数据库名" />
          </Form.Item>
          <div style={{ display: "flex", gap: 12 }}>
            <Form.Item
              name="username"
              label="Username"
              rules={[{ required: true }]}
              style={{ flex: 1 }}
            >
              <Input placeholder="用户名" />
            </Form.Item>
            <Form.Item
              name="password"
              label="Password"
              rules={[{ required: true }]}
              style={{ flex: 1 }}
            >
              <Input.Password placeholder="密码" />
            </Form.Item>
          </div>
        </Form>
      </Modal>
    </div>
  );
};

export default ConnectDatabase;
