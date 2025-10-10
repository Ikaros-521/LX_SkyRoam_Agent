import React from 'react';
import { Card, Typography, Space, Button } from 'antd';
import { CheckCircleOutlined, RocketOutlined } from '@ant-design/icons';

const { Title, Paragraph } = Typography;

const TestPage: React.FC = () => {
  return (
    <div style={{ 
      minHeight: '100vh', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    }}>
      <Card 
        style={{ 
          maxWidth: '600px', 
          textAlign: 'center',
          borderRadius: '16px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.1)'
        }}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <CheckCircleOutlined 
            style={{ 
              fontSize: '64px', 
              color: '#52c41a' 
            }} 
          />
          
          <Title level={2} style={{ color: '#52c41a', margin: 0 }}>
            <RocketOutlined style={{ marginRight: '12px' }} />
            LX SkyRoam Agent
          </Title>
          
          <Title level={3} style={{ color: '#1890ff', margin: 0 }}>
            前端应用启动成功！
          </Title>
          
          <Paragraph style={{ fontSize: '16px', color: '#666' }}>
            恭喜！您的智能旅游攻略生成器前端应用已经成功启动。
            现在您可以开始使用所有功能了。
          </Paragraph>
          
          <Space size="large">
            <Button 
              type="primary" 
              size="large"
              onClick={() => window.location.href = '/'}
            >
              返回首页
            </Button>
            <Button 
              size="large"
              onClick={() => window.location.href = '/plan'}
            >
              创建计划
            </Button>
          </Space>
          
          <div style={{ 
            marginTop: '24px', 
            padding: '16px', 
            background: '#f6ffed', 
            borderRadius: '8px',
            border: '1px solid #b7eb8f'
          }}>
            <Paragraph style={{ margin: 0, color: '#52c41a' }}>
              <strong>应用状态:</strong> 运行正常 ✅<br/>
              <strong>端口:</strong> 3000<br/>
              <strong>环境:</strong> 开发模式
            </Paragraph>
          </div>
        </Space>
      </Card>
    </div>
  );
};

export default TestPage;
