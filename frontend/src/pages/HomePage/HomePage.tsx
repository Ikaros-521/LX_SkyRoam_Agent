import React from 'react';
import { 
  Card, 
  Button, 
  Row, 
  Col, 
  Typography, 
  Space,
  Divider,
  Statistic,
  Carousel
} from 'antd';
import { 
  GlobalOutlined, 
  CalendarOutlined,
  DollarOutlined,
  HeartOutlined,
  RocketOutlined,
  ArrowRightOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title, Paragraph, Text } = Typography;

const HomePage: React.FC = () => {
  const navigate = useNavigate();

  const handleStartPlanning = () => {
    navigate('/plan');
  };

  const features = [
    {
      icon: <GlobalOutlined style={{ fontSize: '32px', color: '#1890ff' }} />,
      title: '智能搜索',
      description: '基于AI的智能数据收集和分析'
    },
    {
      icon: <CalendarOutlined style={{ fontSize: '32px', color: '#52c41a' }} />,
      title: '个性化规划',
      description: '根据您的偏好生成专属旅行方案'
    },
    {
      icon: <DollarOutlined style={{ fontSize: '32px', color: '#faad14' }} />,
      title: '预算优化',
      description: '智能预算分配，让每一分钱都花得值'
    },
    {
      icon: <HeartOutlined style={{ fontSize: '32px', color: '#f5222d' }} />,
      title: '贴心服务',
      description: '24小时智能客服，随时为您解答'
    }
  ];

  const testimonials = [
    {
      content: "这个AI助手帮我规划了一次完美的日本之旅，从机票到酒店，从景点到美食，一切都安排得井井有条！",
      author: "张小姐",
      location: "北京"
    },
    {
      content: "作为一个旅行新手，这个工具让我轻松规划了欧洲15天的行程，省时省力还省钱！",
      author: "李先生", 
      location: "上海"
    },
    {
      content: "AI生成的方案比我自己规划的还要详细，连交通路线都考虑到了，太贴心了！",
      author: "王女士",
      location: "广州"
    }
  ];

  return (
    <div className="homepage">
      {/* 英雄区域 */}
      <div className="hero-section" style={{ 
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: '80px 0',
        textAlign: 'center',
        color: 'white'
      }}>
        <div className="container" style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 20px' }}>
          <Title level={1} style={{ color: 'white', marginBottom: '16px' }}>
            <RocketOutlined style={{ marginRight: '16px' }} />
            洛曦 云游Agent
          </Title>
          <Title level={2} style={{ color: 'white', fontWeight: 'normal', marginBottom: '24px' }}>
            您的智能旅行规划助手
          </Title>
          <Paragraph style={{ fontSize: '18px', color: 'rgba(255,255,255,0.9)', marginBottom: '40px' }}>
            基于AI技术，为您提供个性化的旅行方案规划，让每一次旅行都成为美好回忆
          </Paragraph>
        </div>
      </div>

      {/* 开始规划按钮 */}
      <div className="action-section" style={{ 
        marginTop: '-60px', 
        position: 'relative', 
        zIndex: 10 
      }}>
        <div className="container" style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 20px' }}>
          <Card 
            style={{ 
              borderRadius: '16px', 
              boxShadow: '0 8px 32px rgba(0,0,0,0.1)',
              border: 'none',
              textAlign: 'center',
              padding: '40px 20px'
            }}
          >
            <Title level={3} style={{ marginBottom: '16px' }}>
              开始您的智能旅行规划
            </Title>
            <Paragraph style={{ fontSize: '16px', color: '#666', marginBottom: '32px' }}>
              只需几步，AI将为您生成完美的旅行方案
            </Paragraph>
            <Button 
              type="primary" 
              size="large"
              icon={<ArrowRightOutlined />}
              onClick={handleStartPlanning}
              style={{ 
                height: '48px',
                paddingLeft: '32px',
                paddingRight: '32px',
                borderRadius: '24px',
                fontSize: '16px',
                fontWeight: 'bold'
              }}
            >
              开始规划旅行
            </Button>
          </Card>
        </div>
      </div>

      {/* 功能特色 */}
      <div className="features-section" style={{ padding: '80px 0', backgroundColor: '#f8f9fa' }}>
        <div className="container" style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 20px' }}>
          <div style={{ textAlign: 'center', marginBottom: '60px' }}>
            <Title level={2}>为什么选择我们？</Title>
            <Paragraph style={{ fontSize: '16px', color: '#666' }}>
              基于先进的AI技术，为您提供最专业的旅行规划服务
            </Paragraph>
          </div>
          
          <Row gutter={[32, 32]}>
            {features.map((feature, index) => (
              <Col xs={24} sm={12} md={6} key={index}>
                <Card 
                  className="travel-card"
                  style={{ textAlign: 'center', height: '100%' }}
                  bodyStyle={{ padding: '32px 24px' }}
                >
                  <div style={{ marginBottom: '16px' }}>
                    {feature.icon}
                  </div>
                  <Title level={4} style={{ marginBottom: '12px' }}>
                    {feature.title}
                  </Title>
                  <Paragraph style={{ color: '#666', margin: 0 }}>
                    {feature.description}
                  </Paragraph>
                </Card>
              </Col>
            ))}
          </Row>
        </div>
      </div>

      {/* 统计数据 */}
      <div className="stats-section" style={{ padding: '60px 0', backgroundColor: 'white' }}>
        <div className="container" style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 20px' }}>
          <Row gutter={[32, 32]}>
            <Col xs={12} sm={6}>
              <Statistic 
                title="服务用户" 
                value={12580} 
                suffix="+" 
                valueStyle={{ color: '#1890ff' }}
              />
            </Col>
            <Col xs={12} sm={6}>
              <Statistic 
                title="生成方案" 
                value={45620} 
                suffix="+" 
                valueStyle={{ color: '#52c41a' }}
              />
            </Col>
            <Col xs={12} sm={6}>
              <Statistic 
                title="覆盖城市" 
                value={280} 
                suffix="+" 
                valueStyle={{ color: '#faad14' }}
              />
            </Col>
            <Col xs={12} sm={6}>
              <Statistic 
                title="用户满意度" 
                value={98.5} 
                suffix="%" 
                valueStyle={{ color: '#f5222d' }}
              />
            </Col>
          </Row>
        </div>
      </div>

      {/* 用户评价 */}
      <div className="testimonials-section" style={{ padding: '80px 0', backgroundColor: '#f8f9fa' }}>
        <div className="container" style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 20px' }}>
          <div style={{ textAlign: 'center', marginBottom: '60px' }}>
            <Title level={2}>用户评价</Title>
            <Paragraph style={{ fontSize: '16px', color: '#666' }}>
              听听用户们怎么说
            </Paragraph>
          </div>
          
          <Carousel autoplay dots>
            {testimonials.map((testimonial, index) => (
              <div key={index}>
                <Card 
                  style={{ 
                    margin: '0 20px', 
                    textAlign: 'center',
                    border: 'none',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                  }}
                >
                  <Paragraph style={{ fontSize: '16px', fontStyle: 'italic', marginBottom: '24px' }}>
                    "{testimonial.content}"
                  </Paragraph>
                  <Divider />
                  <Space direction="vertical" size="small">
                    <Text strong>{testimonial.author}</Text>
                    <Text type="secondary">{testimonial.location}</Text>
                  </Space>
                </Card>
              </div>
            ))}
          </Carousel>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
