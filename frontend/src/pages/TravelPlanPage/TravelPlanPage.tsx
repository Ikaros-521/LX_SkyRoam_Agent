import React, { useState, useEffect } from 'react';
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
  Steps,
  Alert,
  Spin,
  Progress
} from 'antd';
import { 
  SearchOutlined, 
  GlobalOutlined, 
  CalendarOutlined,
  DollarOutlined,
  CheckCircleOutlined,
  LoadingOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';

const { Title, Paragraph, Text } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;
const { Step } = Steps;

interface TravelRequest {
  destination: string;
  dateRange: [dayjs.Dayjs, dayjs.Dayjs];
  budget: number;
  preferences: string[];
  requirements: string;
}

const TravelPlanPage: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [planId, setPlanId] = useState<number | null>(null);
  const [generationStatus, setGenerationStatus] = useState<string>('idle');
  const [progress, setProgress] = useState(0);

  const steps = [
    {
      title: '填写需求',
      description: '输入您的旅行需求',
      icon: <GlobalOutlined />
    },
    {
      title: 'AI分析',
      description: '智能分析您的需求',
      icon: <LoadingOutlined />
    },
    {
      title: '生成方案',
      description: '为您生成旅行方案',
      icon: <SearchOutlined />
    },
    {
      title: '完成',
      description: '方案生成完成',
      icon: <CheckCircleOutlined />
    }
  ];

  const handleSubmit = async (values: TravelRequest) => {
    setLoading(true);
    setCurrentStep(1);
    
    try {
      // 创建旅行计划
      const response = await fetch('/api/v1/travel-plans/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...values,
          user_id: 1, // 临时用户ID
          duration_days: values.dateRange[1].diff(values.dateRange[0], 'day') + 1
        }),
      });

      if (!response.ok) {
        throw new Error('创建计划失败');
      }

      const plan = await response.json();
      setPlanId(plan.id);
      
      // 开始生成方案
      await generatePlans(plan.id, values);
      
    } catch (error) {
      console.error('提交失败:', error);
      setCurrentStep(0);
    } finally {
      setLoading(false);
    }
  };

  const generatePlans = async (planId: number, preferences: TravelRequest) => {
    setCurrentStep(2);
    setGenerationStatus('generating');
    
    try {
      // 启动方案生成
      const response = await fetch(`/api/v1/travel-plans/${planId}/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          preferences: {
            budget_priority: preferences.budget < 3000 ? 'low' : 'medium',
            activity_preference: preferences.preferences[0] || 'culture'
          },
          requirements: preferences.requirements,
          num_plans: 3
        }),
      });

      if (!response.ok) {
        throw new Error('启动方案生成失败');
      }

      // 轮询生成状态
      await pollGenerationStatus(planId);
      
    } catch (error) {
      console.error('生成方案失败:', error);
      setGenerationStatus('failed');
    }
  };

  const pollGenerationStatus = async (planId: number) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/v1/travel-plans/${planId}/status`);
        const status = await response.json();
        
        setProgress(Math.min(progress + 10, 90));
        
        if (status.status === 'completed') {
          clearInterval(pollInterval);
          setCurrentStep(3);
          setGenerationStatus('completed');
          setProgress(100);
          
          // 跳转到方案详情页
          setTimeout(() => {
            navigate(`/plan/${planId}`);
          }, 2000);
        } else if (status.status === 'failed') {
          clearInterval(pollInterval);
          setGenerationStatus('failed');
        }
      } catch (error) {
        console.error('查询状态失败:', error);
      }
    }, 2000);

    // 30秒后超时
    setTimeout(() => {
      clearInterval(pollInterval);
      if (generationStatus === 'generating') {
        setGenerationStatus('timeout');
      }
    }, 30000);
  };

  const getStatusAlert = () => {
    switch (generationStatus) {
      case 'generating':
        return (
          <Alert
            message="正在生成您的专属旅行方案"
            description="AI正在为您分析目的地信息，收集航班、酒店、景点等数据，请稍候..."
            type="info"
            showIcon
            style={{ marginBottom: 24 }}
          />
        );
      case 'completed':
        return (
          <Alert
            message="方案生成完成！"
            description="您的专属旅行方案已生成，即将跳转到详情页面..."
            type="success"
            showIcon
            style={{ marginBottom: 24 }}
          />
        );
      case 'failed':
        return (
          <Alert
            message="方案生成失败"
            description="很抱歉，方案生成过程中出现了问题，请重试。"
            type="error"
            showIcon
            style={{ marginBottom: 24 }}
          />
        );
      case 'timeout':
        return (
          <Alert
            message="生成超时"
            description="方案生成时间较长，请稍后查看结果或重新生成。"
            type="warning"
            showIcon
            style={{ marginBottom: 24 }}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="travel-plan-page" style={{ maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: '40px' }}>
        <Title level={2}>创建您的专属旅行计划</Title>
        <Paragraph style={{ fontSize: '16px', color: '#666' }}>
          请填写您的旅行需求，AI将为您生成个性化的旅行方案
        </Paragraph>
      </div>

      {/* 步骤指示器 */}
      <Card style={{ marginBottom: '24px' }}>
        <Steps current={currentStep} items={steps} />
      </Card>

      {/* 状态提示 */}
      {getStatusAlert()}

      {/* 进度条 */}
      {generationStatus === 'generating' && (
        <Card style={{ marginBottom: '24px' }}>
          <div style={{ textAlign: 'center' }}>
            <Progress 
              percent={progress} 
              status="active"
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
            />
            <Text type="secondary" style={{ marginTop: '8px', display: 'block' }}>
              正在收集数据并生成方案...
            </Text>
          </div>
        </Card>
      )}

      {/* 表单 */}
      {currentStep === 0 && (
        <Card 
          title={
            <Space>
              <GlobalOutlined />
              旅行需求
            </Space>
          }
          style={{ 
            borderRadius: '12px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
          }}
        >
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmit}
            size="large"
          >
            <Row gutter={[24, 16]}>
              <Col xs={24} sm={12}>
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
              
              <Col xs={24} sm={12}>
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
            </Row>
            
            <Row gutter={[24, 16]}>
              <Col xs={24} sm={12}>
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
            </Row>
            
            <Form.Item name="requirements" label="特殊要求">
              <Input.TextArea 
                placeholder="请输入特殊要求（如：带老人、带小孩、无障碍设施等）"
                rows={3}
              />
            </Form.Item>
            
            <Form.Item>
              <Button 
                type="primary" 
                htmlType="submit" 
                loading={loading}
                icon={<SearchOutlined />}
                size="large"
                style={{ 
                  width: '100%',
                  height: '48px',
                  borderRadius: '8px'
                }}
              >
                {loading ? '正在创建计划...' : '开始生成方案'}
              </Button>
            </Form.Item>
          </Form>
        </Card>
      )}

      {/* 生成中状态 */}
      {currentStep > 0 && currentStep < 3 && (
        <Card style={{ textAlign: 'center', padding: '40px' }}>
          <Spin size="large" />
          <div style={{ marginTop: '16px' }}>
            <Title level={4}>
              {currentStep === 1 && '正在分析您的需求...'}
              {currentStep === 2 && '正在生成旅行方案...'}
            </Title>
            <Paragraph>
              {currentStep === 1 && 'AI正在理解您的旅行偏好和需求'}
              {currentStep === 2 && '正在收集航班、酒店、景点等信息，为您生成最佳方案'}
            </Paragraph>
          </div>
        </Card>
      )}

      {/* 完成状态 */}
      {currentStep === 3 && (
        <Card style={{ textAlign: 'center', padding: '40px' }}>
          <CheckCircleOutlined style={{ fontSize: '64px', color: '#52c41a', marginBottom: '16px' }} />
          <Title level={3} style={{ color: '#52c41a' }}>
            方案生成完成！
          </Title>
          <Paragraph>
            您的专属旅行方案已生成，即将跳转到详情页面查看完整方案。
          </Paragraph>
        </Card>
      )}
    </div>
  );
};

export default TravelPlanPage;
