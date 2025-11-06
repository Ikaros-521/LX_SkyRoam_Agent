import React, { useState } from 'react';
import { Layout as AntLayout, Menu, Button, Drawer, Typography, Avatar, Dropdown, Modal, Form, Input, message } from 'antd';
import { 
  HomeOutlined, 
  CalendarOutlined, 
  HistoryOutlined, 
  InfoCircleOutlined,
  MenuOutlined,
  RocketOutlined,
  UserOutlined,
  EnvironmentOutlined
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import './Layout.css';
// 新增导入
import { getToken, clearToken } from '../../utils/auth';
import { authFetch } from '../../utils/auth';
import { buildApiUrl } from '../../config/api';

const { Header, Content, Footer } = AntLayout;
const { Title } = Typography;

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuVisible, setMobileMenuVisible] = useState(false);
  const token = getToken();
  const [user, setUser] = useState<any>(null);
  const [profileVisible, setProfileVisible] = useState(false);
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [profileForm] = Form.useForm();
  const [pwdForm] = Form.useForm();
  const [saving, setSaving] = useState(false);

  // 拉取当前用户信息
  React.useEffect(() => {
    const fetchMe = async () => {
      if (!token) return;
      try {
        const res = await authFetch(buildApiUrl('/users/me'));
        if (res.ok) {
          const data = await res.json();
          setUser(data);
          profileForm.setFieldsValue({ email: data.email || '', full_name: data.full_name || '' });
        }
      } catch (e) {
        // 忽略错误
      }
    };
    fetchMe();
  }, [token]);

  // 嵌入式菜单：将“创建计划”移出菜单作为CTA按钮
  const baseMenuItems = [
    { key: '/', label: '首页', icon: <HomeOutlined /> },
    { key: '/destinations', label: '目的地', icon: <EnvironmentOutlined /> },
    { key: '/plans', label: '计划库', icon: <HistoryOutlined /> },
    { key: '/about', label: '关于我们', icon: <InfoCircleOutlined /> },
  ];
  const menuItems = baseMenuItems;

  const handleMenuClick = (key: string) => {
    // 未登录时，拦截“创建计划”并跳转登录
    if (key === '/plan' && !token) {
      navigate('/login');
      setMobileMenuVisible(false);
      return;
    }
    navigate(key);
    setMobileMenuVisible(false);
  };

  const handleLogout = () => {
    clearToken();
    navigate('/login');
  };

  const handleSaveProfile = async () => {
    try {
      setSaving(true);
      const values = await profileForm.validateFields();
      const res = await authFetch(buildApiUrl('/users/me'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || '更新失败');
      }
      setUser(data);
      message.success('资料已更新');
      setProfileVisible(false);
    } catch (e: any) {
      message.error(e.message || '更新失败');
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async () => {
    try {
      setSaving(true);
      const values = await pwdForm.validateFields();
      const res = await authFetch(buildApiUrl('/users/change-password'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || '修改密码失败');
      }
      message.success('密码已更新');
      setPasswordVisible(false);
      pwdForm.resetFields();
    } catch (e: any) {
      message.error(e.message || '修改密码失败');
    } finally {
      setSaving(false);
    }
  };

  const userMenu = (
    <Menu
      items={[
        ...(user?.role === 'admin' ? [
          { key: 'admin_users', label: '用户管理', icon: <UserOutlined />, onClick: () => navigate('/admin/users') },
          { key: 'admin_history', label: '历史记录管理', icon: <HistoryOutlined />, onClick: () => navigate('/admin/history') },
          { type: 'divider' as const },
        ] : []),
        { key: 'profile', label: '个人资料', onClick: () => setProfileVisible(true) },
        { key: 'password', label: '修改密码', onClick: () => setPasswordVisible(true) },
        { type: 'divider' as const },
        { key: 'logout', label: '退出登录', onClick: handleLogout },
      ]}
    />
  );

  const mobileMenu = (
    <Menu
      mode="vertical"
      selectedKeys={[location.pathname]}
      items={menuItems}
      onClick={({ key }) => handleMenuClick(key)}
      style={{ border: 'none' }}
    />
  );

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Header 
        style={{ 
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          padding: 0,
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
        }}
      >
        <div className="header-inner">
          <div className="header-brand" style={{ display: 'flex', alignItems: 'center' }}>
             <RocketOutlined 
               style={{ fontSize: '24px', color: 'white', marginRight: 12 }} 
             />
             <Title level={3} style={{ color: 'white', margin: 0, fontWeight: 'bold' }}>
               洛曦 云旅Agent
             </Title>
           </div>

           <Menu
             mode="horizontal"
             selectedKeys={[location.pathname]}
             items={menuItems}
             onClick={({ key }) => handleMenuClick(key)}
             style={{ background: 'transparent', border: 'none', color: 'white' }}
             theme="dark"
           />

          <div className="header-actions">
            <Button type="primary" onClick={() => handleMenuClick('/plan')}>
              创建计划
            </Button>
            {token ? (
              <Dropdown overlay={userMenu} placement="bottomRight">
                <div style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                  <Avatar icon={<UserOutlined />} src={undefined} />
                  <Typography.Text style={{ color: 'white', marginLeft: 8 }}>
                    {user?.username || '用户'}
                  </Typography.Text>
                </div>
              </Dropdown>
            ) : (
              <Avatar
                icon={<UserOutlined />}
                style={{ cursor: 'pointer', backgroundColor: 'rgba(255,255,255,0.2)' }}
                onClick={() => navigate('/login')}
              />
            )}

            <Button
              type="text"
              icon={<MenuOutlined />}
              onClick={() => setMobileMenuVisible(true)}
              className="mobile-menu-button"
            />
          </div>
        </div>
      </Header>

      {/* 资料编辑弹窗 */}
      <Modal
        title="编辑个人资料"
        open={profileVisible}
        onCancel={() => setProfileVisible(false)}
        onOk={handleSaveProfile}
        confirmLoading={saving}
      >
        <Form form={profileForm} layout="vertical">
          <Form.Item label="邮箱" name="email">
            <Input placeholder="可选" />
          </Form.Item>
          <Form.Item label="姓名" name="full_name">
            <Input placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 修改密码弹窗 */}
      <Modal
        title="修改密码"
        open={passwordVisible}
        onCancel={() => setPasswordVisible(false)}
        onOk={handleChangePassword}
        confirmLoading={saving}
      >
        <Form form={pwdForm} layout="vertical">
          <Form.Item label="旧密码" name="old_password" rules={[{ required: true, message: '请输入旧密码' }]}>
            <Input.Password placeholder="请输入旧密码" />
          </Form.Item>
          <Form.Item label="新密码" name="new_password" rules={[{ required: true, message: '请输入新密码' }, { min: 6, message: '至少6位' }]}>
            <Input.Password placeholder="至少6位" />
          </Form.Item>
        </Form>
      </Modal>

      <Content style={{ padding: '24px', minHeight: 'calc(100vh - 64px - 70px)' }}>
        {children}
      </Content>

      <Footer 
        style={{ textAlign: 'center', background: '#f0f2f5', borderTop: '1px solid #d9d9d9' }}
      >
        <div style={{ color: '#666' }}>
          <p style={{ margin: '8px 0' }}>© 2025 洛曦 云旅Agent. 智能旅游攻略生成器</p>
          <p style={{ margin: '8px 0', fontSize: '12px' }}>基于AI技术，为您提供个性化的旅行方案规划</p>
        </div>
      </Footer>

      {/* 移动端抽屉菜单 */}
      <Drawer title="菜单" placement="right" onClose={() => setMobileMenuVisible(false)} open={mobileMenuVisible} bodyStyle={{ padding: 0 }}>
        {mobileMenu}
      </Drawer>

    </AntLayout>
  );
};

export default Layout;
