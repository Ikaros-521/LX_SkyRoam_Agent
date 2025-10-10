import React from 'react';
import { 
  Card, 
  Row, 
  Col, 
  Typography, 
  Space,
  Divider,
  List,
  Avatar,
  Tag
} from 'antd';
import { 
  RocketOutlined,
  GlobalOutlined,
  SafetyOutlined,
  HeartOutlined,
  TeamOutlined,
  BulbOutlined
} from '@ant-design/icons';

const { Title, Paragraph, Text } = Typography;

const AboutPage: React.FC = () => {
  const features = [
    {
      icon: <GlobalOutlined style={{ fontSize: '24px', color: '#1890ff' }} />,
      title: '智能搜索',
      description: '基于AI技术，自动收集和分析全球旅行数据'
    },
    {
      icon: <SafetyOutlined style={{ fontSize: '24px', color: '#52c41a' }} />,
      title: '数据可靠',
      description: '多源数据验证，确保信息的准确性和时效性'
    },
    {
      icon: <HeartOutlined style={{ fontSize: '24px', color: '#f5222d' }} />,
      title: '个性化',
      description: '根据您的偏好和需求，生成专属旅行方案'
    },
    {
      icon: <BulbOutlined style={{ fontSize: '24px', color: '#faad14' }} />,
      title: '智能优化',
      description: '自动优化行程安排，让您的旅行更加高效'
    }
  ];

  const team = [
    {
      name: '张明',
      role: '产品经理',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=zhangming',
      description: '负责产品规划和用户体验设计'
    },
    {
      name: '李华',
      role: '技术总监',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=lihua',
      description: '负责技术架构和AI算法开发'
    },
    {
      name: '王芳',
      role: 'UI设计师',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=wangfang',
      description: '负责界面设计和用户体验优化'
    },
    {
      name: '刘强',
      role: '后端开发',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=liuqiang',
      description: '负责后端服务和数据系统开发'
    }
  ];

  const technologies = [
    'React', 'TypeScript', 'FastAPI', 'Python', 'PostgreSQL', 
    'Redis', 'OpenAI GPT', 'Docker', 'Kubernetes', 'AWS'
  ];

  return (
    <div className="about-page" style={{ maxWidth: '1200px', margin: '0 auto' }}>
      {/* 公司介绍 */}
      <Card style={{ marginBottom: '24px' }}>
        <Row gutter={[32, 32]} align="middle">
          <Col xs={24} md={12}>
            <Space direction="vertical" size="large">
              <div>
                <Title level={1} style={{ margin: 0 }}>
                  <RocketOutlined style={{ marginRight: '12px', color: '#1890ff' }} />
                  LX SkyRoam Agent
                </Title>
                <Title level={3} type="secondary" style={{ margin: '8px 0' }}>
                  智能旅游攻略生成器
                </Title>
              </div>
              
              <Paragraph style={{ fontSize: '16px', lineHeight: '1.8' }}>
                LX SkyRoam Agent 是一款基于人工智能技术的智能旅行规划助手。
                我们致力于为每一位旅行者提供个性化、专业化的旅行方案规划服务，
                让每一次旅行都成为美好的回忆。
              </Paragraph>
              
              <Paragraph style={{ fontSize: '16px', lineHeight: '1.8' }}>
                通过整合全球旅行数据，运用先进的AI算法，我们能够为您生成
                最适合的旅行方案，包括航班、酒店、景点、餐饮等全方位的规划建议。
              </Paragraph>
            </Space>
          </Col>
          
          <Col xs={24} md={12}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ 
                width: '300px', 
                height: '300px', 
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto',
                boxShadow: '0 8px 32px rgba(102, 126, 234, 0.3)'
              }}>
                <RocketOutlined style={{ fontSize: '120px', color: 'white' }} />
              </div>
            </div>
          </Col>
        </Row>
      </Card>

      {/* 核心功能 */}
      <Card title="核心功能" style={{ marginBottom: '24px' }}>
        <Row gutter={[24, 24]}>
          {features.map((feature, index) => (
            <Col xs={24} sm={12} md={6} key={index}>
              <div style={{ textAlign: 'center', padding: '16px' }}>
                <div style={{ marginBottom: '16px' }}>
                  {feature.icon}
                </div>
                <Title level={4} style={{ marginBottom: '8px' }}>
                  {feature.title}
                </Title>
                <Paragraph style={{ color: '#666', margin: 0 }}>
                  {feature.description}
                </Paragraph>
              </div>
            </Col>
          ))}
        </Row>
      </Card>

      {/* 技术栈 */}
      <Card title="技术栈" style={{ marginBottom: '24px' }}>
        <div style={{ textAlign: 'center' }}>
          <Space wrap size="large">
            {technologies.map((tech, index) => (
              <Tag 
                key={index} 
                color="blue" 
                style={{ 
                  padding: '4px 12px', 
                  fontSize: '14px',
                  borderRadius: '16px'
                }}
              >
                {tech}
              </Tag>
            ))}
          </Space>
        </div>
      </Card>

      {/* 团队介绍 */}
      <Card title="我们的团队" style={{ marginBottom: '24px' }}>
        <Row gutter={[24, 24]}>
          {team.map((member, index) => (
            <Col xs={24} sm={12} md={6} key={index}>
              <Card 
                size="small" 
                style={{ textAlign: 'center' }}
                bodyStyle={{ padding: '20px' }}
              >
                <Avatar 
                  size={80} 
                  src={member.avatar}
                  style={{ marginBottom: '16px' }}
                />
                <Title level={4} style={{ marginBottom: '4px' }}>
                  {member.name}
                </Title>
                <Tag color="blue" style={{ marginBottom: '8px' }}>
                  {member.role}
                </Tag>
                <Paragraph style={{ color: '#666', margin: 0, fontSize: '14px' }}>
                  {member.description}
                </Paragraph>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>

      {/* 联系我们 */}
      <Card title="联系我们">
        <Row gutter={[32, 32]}>
          <Col xs={24} md={12}>
            <Title level={4}>联系方式</Title>
            <List>
              <List.Item>
                <List.Item.Meta
                  avatar={<TeamOutlined style={{ fontSize: '20px', color: '#1890ff' }} />}
                  title="邮箱"
                  description="contact@lxskyroam.com"
                />
              </List.Item>
              <List.Item>
                <List.Item.Meta
                  avatar={<GlobalOutlined style={{ fontSize: '20px', color: '#52c41a' }} />}
                  title="官网"
                  description="www.lxskyroam.com"
                />
              </List.Item>
              <List.Item>
                <List.Item.Meta
                  avatar={<HeartOutlined style={{ fontSize: '20px', color: '#f5222d' }} />}
                  title="客服热线"
                  description="400-123-4567"
                />
              </List.Item>
            </List>
          </Col>
          
          <Col xs={24} md={12}>
            <Title level={4}>服务时间</Title>
            <List>
              <List.Item>
                <Text strong>在线客服：</Text>
                <Text> 7×24小时</Text>
              </List.Item>
              <List.Item>
                <Text strong>电话客服：</Text>
                <Text> 周一至周日 9:00-21:00</Text>
              </List.Item>
              <List.Item>
                <Text strong>技术支持：</Text>
                <Text> 周一至周五 9:00-18:00</Text>
              </List.Item>
            </List>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default AboutPage;
