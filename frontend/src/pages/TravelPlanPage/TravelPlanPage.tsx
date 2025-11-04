import React, { useState, useEffect, useRef } from 'react';
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
  Progress,
  InputNumber,
  Checkbox
} from 'antd';
import { 
  SearchOutlined, 
  GlobalOutlined, 
  CalendarOutlined,
  DollarOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  UserOutlined,
  HeartOutlined
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import dayjs from 'dayjs';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';
import { authFetch } from '../../utils/auth';

const { Title, Paragraph, Text } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;
const { Step } = Steps;
// const { CheckboxGroup } = Checkbox; // 暂时不使用

interface TravelRequest {
  departure: string;  // 出发地
  destination: string;
  dateRange: [dayjs.Dayjs, dayjs.Dayjs];
  budget: number;
  preferences: string[];
  requirements: string;
  transportation?: string;  // 出行方式（可选）
  travelers: number;  // 出行人数
  foodPreferences: string[];  // 口味偏好
  dietaryRestrictions: string[];  // 忌口/饮食限制
  ageGroups: string[];  // 年龄组成
}

const TravelPlanPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [planId, setPlanId] = useState<number | null>(null);
  const [generationStatus, setGenerationStatus] = useState<string>('idle');
  const [progress, setProgress] = useState(0);
  const [autoSubmitting, setAutoSubmitting] = useState(false);
  const hasAutoSubmitted = useRef(false);

  // 接收来自首页的表单数据并自动提交
  useEffect(() => {
    const formData = location.state?.formData;
    if (formData && !hasAutoSubmitted.current) {
      console.log('接收到首页表单数据，自动提交:', formData);
      
      // 处理日期数据：将字符串转换为dayjs对象
      const processedData = { ...formData };
      if (formData.dateRange && Array.isArray(formData.dateRange) && formData.dateRange.length === 2) {
        processedData.dateRange = [
          dayjs(formData.dateRange[0]),
          dayjs(formData.dateRange[1])
        ];
      }
      
      // 预填表单
      form.setFieldsValue(processedData);
      
      // 标记已自动提交，防止重复提交
      hasAutoSubmitted.current = true;
      setAutoSubmitting(true);
      
      setTimeout(() => {
        form.submit();
      }, 100); // 稍微延迟确保表单已渲染
    }
  }, [location.state]); // 移除form依赖，避免重复提交

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
    setAutoSubmitting(false); // 重置自动提交状态
    setCurrentStep(1);
    
    try {
      // 创建旅行计划
      const response = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLANS), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: `${values.departure} → ${values.destination} 旅行计划`, // 自动生成标题
          departure: values.departure,
          destination: values.destination,
          start_date: values.dateRange[0].format('YYYY-MM-DD HH:mm:ss'),
          end_date: values.dateRange[1].format('YYYY-MM-DD HH:mm:ss'),
          duration_days: values.dateRange[1].diff(values.dateRange[0], 'day') + 1,
          budget: values.budget,
          transportation: values.transportation,
          preferences: { 
            interests: values.preferences,
            travelers: values.travelers,
            food_preferences: values.foodPreferences,
            dietary_restrictions: values.dietaryRestrictions,
            age_groups: values.ageGroups
          },
          requirements: { 
            special_requirements: values.requirements,
            travelers_count: values.travelers,
            dietary_info: values.dietaryRestrictions?.join(', ') || ''
          }
        }),
      });

      if (!response.ok) {
        throw new Error('创建计划失败');
      }

      const plan = await response.json();
      console.log('创建计划响应:', plan);
      
      if (!plan || !plan.id) {
        throw new Error('创建计划响应格式错误');
      }
      
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
    console.log('开始生成方案:', { planId, preferences });
    setCurrentStep(2);
    setGenerationStatus('generating');
    
    try {
      // 启动方案生成
      const response = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_GENERATE(planId)), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preferences: {
            budget_priority: preferences.budget < 3000 ? 'low' : 'medium',
            activity_preference: preferences.preferences || ['culture'],
            travelers_count: preferences.travelers,
            food_preferences: preferences.foodPreferences,
            dietary_restrictions: preferences.dietaryRestrictions,
            age_groups: preferences.ageGroups
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
    let pollCount = 0;
    const maxPolls = 150; // 最大轮询次数：150次 * 6秒 = 15分钟
    const pollInterval = setInterval(async () => {
      try {
        pollCount++;
        console.log(`轮询状态 ${pollCount}/${maxPolls}: 计划 ${planId}`);
        
        const response = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_STATUS(planId)));
        const status = await response.json();
        
        // 动态更新进度，基于轮询次数
        const newProgress = Math.min(10 + (pollCount * 0.6), 90);
        setProgress(newProgress);
        
        console.log(`状态: ${status.status}, 进度: ${newProgress}%`);
        
        if (status.status === 'completed') {
          clearInterval(pollInterval);
          setCurrentStep(3);
          setGenerationStatus('completed');
          setProgress(100);
          console.log('方案生成完成！');
          
          // 跳转到方案详情页
          setTimeout(() => {
            navigate(`/plan/${planId}`);
          }, 2000);
        } else if (status.status === 'failed') {
          clearInterval(pollInterval);
          setGenerationStatus('failed');
          console.log('方案生成失败');
        } else if (pollCount >= maxPolls) {
          clearInterval(pollInterval);
          setGenerationStatus('timeout');
          console.log('轮询超时，已达到最大次数');
        }
      } catch (error) {
        console.error('轮询状态失败:', error);
      }
    }, 6000);
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
            message="生成时间较长"
            description="方案生成时间较长，您可以稍后查看历史记录页面，或重新生成。"
            type="warning"
            showIcon
            style={{ marginBottom: 24 }}
            action={
              <Button 
                size="small" 
                onClick={() => navigate('/history')}
              >
                查看历史记录
              </Button>
            }
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
      
      {/* 自动提交提示 */}
      {autoSubmitting && (
        <Card style={{ marginBottom: '24px' }}>
          <Alert
            message="正在自动处理您的旅行需求"
            description="检测到您从首页跳转，正在自动提交表单..."
            type="info"
            showIcon
          />
        </Card>
      )}

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
            initialValues={{
              travelers: 2,
              foodPreferences: [],
              dietaryRestrictions: [],
              ageGroups: []
            }}
          >
            <Row gutter={[24, 16]}>
              <Col xs={24} sm={12}>
                <Form.Item
                  name="departure"
                  label="出发地"
                  rules={[{ required: true, message: '请输入出发地' }]}
                >
                  <Input 
                    placeholder="请输入出发地" 
                    prefix={<GlobalOutlined />}
                  />
                </Form.Item>
              </Col>
              
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
            </Row>
            
            <Row gutter={[24, 16]}>
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
              
              <Col xs={24} sm={12}>
                <Form.Item
                  name="travelers"
                  label="出行人数"
                  rules={[{ required: true, message: '请选择出行人数' }]}
                >
                  <InputNumber
                    min={1}
                    max={200}
                    style={{ width: '100%' }}
                    placeholder="请输入出行人数"
                    prefix={<UserOutlined />}
                    addonAfter="人"
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
                <Form.Item
                  name="transportation"
                  label="出行方式"
                >
                  <Select placeholder="请选择出行方式（可选）" allowClear>
                    <Option value="flight">飞机</Option>
                    <Option value="train">火车</Option>
                    <Option value="bus">大巴</Option>
                    <Option value="car">自驾</Option>
                    <Option value="mixed">混合交通</Option>
                  </Select>
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
                <Form.Item name="ageGroups" label="年龄组成">
                  <Select 
                    mode="multiple" 
                    placeholder="选择出行人员年龄组成"
                    allowClear
                  >
                    <Option value="infant">婴幼儿（0-2岁）</Option>
                    <Option value="child">儿童（3-12岁）</Option>
                    <Option value="teenager">青少年（13-17岁）</Option>
                    <Option value="adult">成人（18-59岁）</Option>
                    <Option value="senior">老年人（60岁以上）</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={[24, 16]}>
              <Col xs={24} sm={12}>
                <Form.Item name="foodPreferences" label="口味偏好">
                  <Select 
                    mode="multiple" 
                    placeholder="选择您的口味偏好"
                    allowClear
                  >
                    <Option value="spicy">辣味</Option>
                    <Option value="sweet">甜味</Option>
                    <Option value="sour">酸味</Option>
                    <Option value="light">清淡</Option>
                    <Option value="heavy">重口味</Option>
                    <Option value="seafood">海鲜</Option>
                    <Option value="meat">肉类</Option>
                    <Option value="vegetarian">素食</Option>
                    <Option value="local">当地特色</Option>
                    <Option value="international">国际美食</Option>
                  </Select>
                </Form.Item>
              </Col>

              <Col xs={24} sm={12}>
                <Form.Item name="dietaryRestrictions" label="忌口/饮食限制">
                  <Select 
                    mode="multiple" 
                    placeholder="选择忌口或饮食限制"
                    allowClear
                  >
                    <Option value="no_pork">不吃猪肉</Option>
                    <Option value="no_beef">不吃牛肉</Option>
                    <Option value="no_seafood">不吃海鲜</Option>
                    <Option value="no_spicy">不吃辣</Option>
                    <Option value="vegetarian">素食主义</Option>
                    <Option value="vegan">严格素食</Option>
                    <Option value="halal">清真食品</Option>
                    <Option value="kosher">犹太洁食</Option>
                    <Option value="gluten_free">无麸质</Option>
                    <Option value="lactose_free">无乳糖</Option>
                    <Option value="nut_allergy">坚果过敏</Option>
                    <Option value="diabetes">糖尿病饮食</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>
            
            <Form.Item name="requirements" label="特殊要求">
              <Input.TextArea 
                placeholder="请输入特殊要求（如：带老人、带小孩、无障碍设施、特殊饮食需求等）"
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
