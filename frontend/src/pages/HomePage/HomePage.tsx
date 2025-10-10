import React, { useState } from 'react';
import { 
  Card, 
  Button, 
  Input, 
  DatePicker, 
  Select, 
  Form, 
  Row, 
  Col, 
  Typography, 
  Space,
  Divider,
  Statistic,
  Carousel
} from 'antd';
import { 
  SearchOutlined, 
  GlobalOutlined, 
  CalendarOutlined,
  DollarOutlined,
  HeartOutlined,
  RocketOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';

const { Title, Paragraph, Text } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

interface TravelRequest {
  destination: string;
  dateRange: [dayjs.Dayjs, dayjs.Dayjs];
  duration: number;
  budget: number;
  preferences: string[];
  requirements: string;
}

const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values: TravelRequest) => {
    setLoading(true);
    try {
      // 这里应该调用API创建旅行计划
      console.log('提交的旅行请求:', values);
      
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // 跳转到计划页面，传递表单数据（将dayjs对象转换为字符串）
      const formDataToPass = {
        ...values,
        dateRange: [
          values.dateRange[0].format('YYYY-MM-DD'),
          values.dateRange[1].format('YYYY-MM-DD')
        ]
      };
      
      navigate('/plan', { 
        state: { 
          formData: formDataToPass 
        } 
      });
    } catch (error) {
      console.error('提交失败:', error);
    } finally {
      setLoading(false);
    }
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
            LX SkyRoam Agent
          </Title>
          <Title level={2} style={{ color: 'white', fontWeight: 'normal', marginBottom: '24px' }}>
            您的智能旅行规划助手
          </Title>
          <Paragraph style={{ fontSize: '18px', color: 'rgba(255,255,255,0.9)', marginBottom: '40px' }}>
            基于AI技术，为您提供个性化的旅行方案规划，让每一次旅行都成为美好回忆
          </Paragraph>
        </div>
      </div>

      {/* 搜索表单 */}
      <div className="search-section" style={{ 
        marginTop: '-60px', 
        position: 'relative', 
        zIndex: 10 
      }}>
        <div className="container" style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 20px' }}>
          <Card 
            style={{ 
              borderRadius: '16px', 
              boxShadow: '0 8px 32px rgba(0,0,0,0.1)',
              border: 'none'
            }}
          >
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSubmit}
              size="large"
            >
              <Row gutter={[24, 16]}>
                <Col xs={24} sm={12} md={6}>
                  <Form.Item
                    name="destination"
                    label="目的地"
                    rules={[{ required: true, message: '请输入目的地' }]}
                  >
                    <Input 
                      placeholder="请输入目的地" 
                      prefix={<GlobalOutlined />}
                    />
                  </Form.Item>
                </Col>
                
                <Col xs={24} sm={12} md={6}>
                  <Form.Item
                    name="dateRange"
                    label="出行时间"
                    rules={[{ required: true, message: '请选择出行时间' }]}
                  >
                    <RangePicker 
                      style={{ width: '100%' }}
                      placeholder={['出发日期', '返回日期']}
                    />
                  </Form.Item>
                </Col>
                
                <Col xs={24} sm={12} md={6}>
                  <Form.Item
                    name="budget"
                    label="预算范围"
                    rules={[{ required: true, message: '请选择预算范围' }]}
                  >
                    <Select placeholder="选择预算范围">
                      <Option value={1000}>1000元以下</Option>
                      <Option value={3000}>1000-3000元</Option>
                      <Option value={5000}>3000-5000元</Option>
                      <Option value={10000}>5000-10000元</Option>
                      <Option value={20000}>10000元以上</Option>
                    </Select>
                  </Form.Item>
                </Col>
                
                <Col xs={24} sm={12} md={6}>
                  <Form.Item label=" ">
                    <Button 
                      type="primary" 
                      htmlType="submit" 
                      loading={loading}
                      icon={<SearchOutlined />}
                      style={{ 
                        width: '100%', 
                        height: '40px',
                        borderRadius: '8px'
                      }}
                    >
                      {loading ? '生成中...' : '开始规划'}
                    </Button>
                  </Form.Item>
                </Col>
              </Row>
              
              <Row gutter={[24, 16]}>
                <Col xs={24} sm={12}>
                  <Form.Item name="preferences" label="旅行偏好">
                    <Select 
                      mode="multiple" 
                      placeholder="选择您的旅行偏好"
                      allowClear
                    >
                      <Option value="culture">文化历史</Option>
                      <Option value="nature">自然风光</Option>
                      <Option value="food">美食体验</Option>
                      <Option value="shopping">购物娱乐</Option>
                      <Option value="adventure">冒险刺激</Option>
                      <Option value="relaxation">休闲放松</Option>
                    </Select>
                  </Form.Item>
                </Col>
                
                <Col xs={24} sm={12}>
                  <Form.Item name="requirements" label="特殊要求">
                    <Input.TextArea 
                      placeholder="请输入特殊要求（如：带老人、带小孩、无障碍设施等）"
                      rows={2}
                    />
                  </Form.Item>
                </Col>
              </Row>
            </Form>
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
