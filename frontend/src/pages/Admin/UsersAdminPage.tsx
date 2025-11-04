import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Typography, Space, Spin, Button, message } from 'antd';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';
import { authFetch } from '../../utils/auth';

const { Title } = Typography;

interface UserItem {
  id: number;
  username: string;
  email?: string;
  full_name?: string;
  role: string;
  is_verified: boolean;
}

const UsersAdminPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState<UserItem[]>([]);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await authFetch(buildApiUrl(API_ENDPOINTS.USERS + '/'));
      const data = await res.json();
      setUsers(Array.isArray(data) ? data : []);
    } catch (e) {
      setUsers([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleEditUsername = async (user: UserItem) => {
    const newUsername = window.prompt('输入新用户名', user.username);
    if (!newUsername || newUsername === user.username) return;
    try {
      const res = await authFetch(buildApiUrl(API_ENDPOINTS.USER_DETAIL(user.id)), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: newUsername }),
      });
      if (res.ok) {
        message.success('用户名已更新');
        fetchUsers();
      } else {
        const err = await res.json();
        message.error(err?.detail || '更新失败');
      }
    } catch (e) {
      message.error('请求失败');
    }
  };

  const handleResetPassword = async (user: UserItem) => {
    const newPassword = window.prompt('输入新密码');
    if (!newPassword) return;
    try {
      const res = await authFetch(buildApiUrl(API_ENDPOINTS.USER_RESET_PASSWORD(user.id)), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_password: newPassword }),
      });
      if (res.ok) {
        message.success('密码已重置');
      } else {
        const err = await res.json();
        message.error(err?.detail || '重置失败');
      }
    } catch (e) {
      message.error('请求失败');
    }
  };

  const handleDeleteUser = async (user: UserItem) => {
    if (!window.confirm(`确认删除用户 ${user.username} ?`)) return;
    try {
      const res = await authFetch(buildApiUrl(API_ENDPOINTS.USER_DETAIL(user.id)), {
        method: 'DELETE',
      });
      if (res.ok) {
        message.success('用户已删除');
        fetchUsers();
      } else {
        const err = await res.json();
        message.error(err?.detail || '删除失败');
      }
    } catch (e) {
      message.error('请求失败');
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { title: '邮箱', dataIndex: 'email', key: 'email' },
    { title: '姓名', dataIndex: 'full_name', key: 'full_name' },
    { 
      title: '角色', 
      dataIndex: 'role', 
      key: 'role',
      render: (role: string) => (
        <Tag color={role === 'admin' ? 'red' : 'blue'}>{role}</Tag>
      )
    },
    { 
      title: '已验证', 
      dataIndex: 'is_verified', 
      key: 'is_verified',
      render: (v: boolean) => (
        <Tag color={v ? 'green' : 'orange'}>{v ? '是' : '否'}</Tag>
      )
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: UserItem) => (
        <Space>
          <Button type="link" onClick={() => handleEditUsername(record)}>编辑用户名</Button>
          <Button type="link" onClick={() => handleResetPassword(record)}>重置密码</Button>
          <Button type="link" danger onClick={() => handleDeleteUser(record)}>删除</Button>
        </Space>
      )
    }
  ];

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <Title level={2}>用户管理</Title>
        </div>
        <Card>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 32 }}>
              <Spin />
            </div>
          ) : (
            <Table
              rowKey="id"
              columns={columns as any}
              dataSource={users}
              pagination={{ pageSize: 10 }}
            />
          )}
        </Card>
      </Space>
    </div>
  );
};

export default UsersAdminPage;