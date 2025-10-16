import React, { useState } from 'react';
import { Layout as AntLayout, Menu, Button, Drawer, Typography } from 'antd';
import { 
  HomeOutlined, 
  CalendarOutlined, 
  HistoryOutlined, 
  InfoCircleOutlined,
  MenuOutlined,
  RocketOutlined
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import './Layout.css';

const { Header, Content, Footer } = AntLayout;
const { Title } = Typography;

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuVisible, setMobileMenuVisible] = useState(false);

  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: '首页',
    },
    {
      key: '/plan',
      icon: <CalendarOutlined />,
      label: '创建计划',
    },
    {
      key: '/history',
      icon: <HistoryOutlined />,
      label: '历史记录',
    },
    {
      key: '/about',
      icon: <InfoCircleOutlined />,
      label: '关于我们',
    },
  ];

  const handleMenuClick = (key: string) => {
    navigate(key);
    setMobileMenuVisible(false);
  };

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
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <RocketOutlined 
            style={{ 
              fontSize: '24px', 
              color: 'white', 
              marginRight: '12px' 
            }} 
          />
          <Title 
            level={3} 
            style={{ 
              color: 'white', 
              margin: 0,
              fontWeight: 'bold'
            }}
          >
            洛曦 云旅Agent
          </Title>
        </div>

        {/* 桌面端菜单 */}
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <Menu
            mode="horizontal"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={({ key }) => handleMenuClick(key)}
            style={{ 
              background: 'transparent',
              border: 'none',
              color: 'white'
            }}
            theme="dark"
          />
        </div>

        {/* 移动端菜单按钮 */}
        <Button
          type="text"
          icon={<MenuOutlined />}
          onClick={() => setMobileMenuVisible(true)}
          style={{ 
            color: 'white',
            display: 'none'
          }}
          className="mobile-menu-button"
        />
      </Header>

      <Content style={{ padding: '24px', minHeight: 'calc(100vh - 64px - 70px)' }}>
        {children}
      </Content>

      <Footer 
        style={{ 
          textAlign: 'center',
          background: '#f0f2f5',
          borderTop: '1px solid #d9d9d9'
        }}
      >
        <div style={{ color: '#666' }}>
          <p style={{ margin: '8px 0' }}>
            © 2024 洛曦 云旅Agent. 智能旅游攻略生成器
          </p>
          <p style={{ margin: '8px 0', fontSize: '12px' }}>
            基于AI技术，为您提供个性化的旅行方案规划
          </p>
        </div>
      </Footer>

      {/* 移动端抽屉菜单 */}
      <Drawer
        title="菜单"
        placement="right"
        onClose={() => setMobileMenuVisible(false)}
        open={mobileMenuVisible}
        bodyStyle={{ padding: 0 }}
      >
        {mobileMenu}
      </Drawer>

    </AntLayout>
  );
};

export default Layout;
