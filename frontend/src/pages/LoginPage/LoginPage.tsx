import React, { useState } from 'react';
import { Card, Form, Input, Button, Typography, message } from 'antd';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';
import { setToken } from '../../utils/auth';
import { useNavigate } from 'react-router-dom';

const { Title, Paragraph } = Typography;

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const res = await fetch(buildApiUrl('/auth/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || '登录失败');
      }
      setToken(data.access_token);
      message.success('登录成功');
      navigate('/');
    } catch (err: any) {
      message.error(err.message || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 420, margin: '40px auto' }}>
      <Card>
        <Title level={3}>登录</Title>
        <Paragraph>使用用户名和密码登录系统</Paragraph>
        <Form layout="vertical" onFinish={onFinish}>
          <Form.Item label="用户名" name="username" rules={[{ required: true, message: '请输入用户名' }]}> 
            <Input placeholder="请输入用户名" />
          </Form.Item>
          <Form.Item label="密码" name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password placeholder="请输入密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登录
            </Button>
          </Form.Item>
          <Button type="link" onClick={() => navigate('/register')}>没有账号？去注册</Button>
        </Form>
      </Card>
    </div>
  );
};

export default LoginPage;