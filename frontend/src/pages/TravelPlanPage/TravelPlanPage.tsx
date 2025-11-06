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
  Checkbox,
  Empty,
  Tooltip,
  Tag,
  Tabs,
  List,
  Image
} from 'antd';
import { 
  SearchOutlined, 
  GlobalOutlined, 
  CalendarOutlined,
  DollarOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  UserOutlined,
  HeartOutlined,
  EnvironmentOutlined,
  StarFilled,
  FireOutlined,
  LinkOutlined,
  ClockCircleOutlined,
  PictureOutlined
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
  departure?: string;  // 出发地（可选）
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
  // 新增：预览数据
  const [previewData, setPreviewData] = useState<any | null>(null);

  // 预览渲染工具函数（在组件内，便于使用）
  const getTitle = (item: any, fallback: string = '未命名') => (
    item?.title || item?.name || item?.note_title || item?.poiName || item?.restaurant_name || fallback
  );

  const getDesc = (item: any) => (
    item?.desc || item?.description || item?.note_desc || item?.summary || item?.address || ''
  );

  const getImage = (item: any) => {
    const pickUrl = (u: any) => {
      if (!u) return undefined;
      const s = String(u).trim().replace(/[`"]/g, '');
      return s.split(/\s+/)[0];
    };
    const candidates: (string | undefined)[] = [];

    // 小红书优先使用 img_urls
    if (Array.isArray(item?.img_urls) && item.img_urls.length) {
      candidates.push(pickUrl(item.img_urls[0]));
    }

    // 常见图片字段
    candidates.push(
      pickUrl(item?.cover_url),
      pickUrl(item?.image_url),
      pickUrl(item?.thumbnail)
    );

    // images 可能是字符串或对象
    if (Array.isArray(item?.images) && item.images.length) {
      const img0 = item.images[0];
      candidates.push(pickUrl(typeof img0 === 'string' ? img0 : img0?.url));
    }

    // photos 可能是字符串或对象（如高德返回 { url }）
    if (Array.isArray(item?.photos) && item.photos.length) {
      const p0 = item.photos[0];
      candidates.push(pickUrl(typeof p0 === 'string' ? p0 : p0?.url));
    }

    return candidates.find((u) => typeof u === 'string' && u.length > 0);
  };

  const getPrice = (item: any) => {
    const p = item?.price || item?.price_total || item?.min_price || item?.avg_price || item?.price_per_night;
    return typeof p === 'number' ? `¥${p}` : typeof p === 'string' ? p : undefined;
  };

  const getLikes = (item: any) => {
    const v = item?.likes || item?.like_count || item?.liked_count;
    return typeof v === 'number' ? v : undefined;
  };

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
          title: (values.departure ? `${values.departure} → ` : '') + `${values.destination} 旅行计划`,
          departure: values.departure || null,
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
    setPreviewData(null); // 重置预览
    
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
        
        // 如果处于生成中，尝试读取预览
        if (status.status === 'generating') {
          const preview = Array.isArray(status.generated_plans)
            ? status.generated_plans.find((p: any) => p?.is_preview && p?.preview_type === 'raw_data_preview')
            : null;
          setPreviewData(preview || null);
        }
        
        // 动态更新进度，基于轮询次数
        const newProgress = Math.min(10 + (pollCount * 0.6), 90);
        setProgress(newProgress);
        
        console.log(`状态: ${status.status}, 进度: ${newProgress}%`);
        
        if (status.status === 'completed') {
          clearInterval(pollInterval);
          setCurrentStep(3);
          setGenerationStatus('completed');
          setProgress(100);
          setPreviewData(null); // 完成后清空预览
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

      {/* 预览数据展示 */}
      {generationStatus === 'generating' && previewData && (
        <Card title={previewData.title || '数据预览'} style={{ marginBottom: '24px' }}>
          <Tabs
            defaultActiveKey="weather"
            items={[
              {
                key: 'weather',
                label: '天气',
                children: (
                  (() => {
                    const weatherRaw = previewData.sections?.weather;
                    const isArray = Array.isArray(weatherRaw);
                    const weatherObj = isArray ? { location: '', forecast: weatherRaw, recommendations: [] } : weatherRaw;
                    const location = weatherObj?.location;
                    const forecast = Array.isArray(weatherObj?.forecast) ? weatherObj?.forecast : (isArray ? weatherRaw : []);
                    const recommendations = Array.isArray(weatherObj?.recommendations) ? weatherObj?.recommendations : [];
                    const emojiFor = (w?: string) => {
                      const s = (w || '').toLowerCase();
                      if (!s) return '🌤️';
                      if (s.includes('晴')) return '☀️';
                      if (s.includes('云')) return '☁️';
                      if (s.includes('雨')) return '🌧️';
                      if (s.includes('雪')) return '❄️';
                      if (s.includes('雷')) return '⛈️';
                      if (s.includes('阴')) return '☁️';
                      return '🌤️';
                    };
                    return forecast && forecast.length ? (
                      <Card>
                        <Space direction="vertical" size={12} style={{ width: '100%' }}>
                          {location && <Text type="secondary">地区：{location}</Text>}
                          <List
                            grid={{ gutter: 16, xs: 1, sm: 2, md: 3, lg: 4 }}
                            dataSource={forecast}
                            style={{ maxHeight: 420, overflow: 'auto', paddingRight: 8 }}
                            renderItem={(d: any) => (
                              <List.Item>
                                <Card hoverable>
                                  <Space direction="vertical" size={6} style={{ width: '100%' }}>
                                    <div style={{ fontWeight: 600 }}>{d?.date || ''}（周{d?.week || ''}）</div>
                                    <Space size={8}>
                                      <Tag>{emojiFor(d?.dayweather)} 日间 {d?.dayweather}</Tag>
                                      <Tag>{emojiFor(d?.nightweather)} 夜间 {d?.nightweather}</Tag>
                                    </Space>
                                    <Space size={8}>
                                      {d?.daytemp && <Tag color="blue">最高 {d.daytemp}℃</Tag>}
                                      {d?.nighttemp && <Tag color="cyan">最低 {d.nighttemp}℃</Tag>}
                                    </Space>
                                    <Space size={8}>
                                      {(d?.daywind || d?.nightwind) && <Tag color="green">风向 {d?.daywind || d?.nightwind}</Tag>}
                                      {(d?.daypower || d?.nightpower) && <Tag>风力 {d?.daypower || d?.nightpower}</Tag>}
                                    </Space>
                                  </Space>
                                </Card>
                              </List.Item>
                            )}
                          />
                          {recommendations.length ? (
                            <Alert
                              type="info"
                              showIcon
                              message="出行建议"
                              description={recommendations.join('、')}
                            />
                          ) : null}
                        </Space>
                      </Card>
                    ) : (
                      <Empty description="暂无天气数据" />
                    );
                  })()
                ),
              },
              
              {
                key: 'hotels',
                label: '酒店',
                children: (
                  (previewData.sections?.hotels || []).length ? (
                    <List
                      grid={{ gutter: 16, xs: 1, sm: 2, md: 3, lg: 4 }}
                      dataSource={previewData.sections?.hotels}
                      style={{ maxHeight: 420, overflow: 'auto', paddingRight: 8 }}
                      renderItem={(h: any) => {
                        const cover = getImage(h);
                        return (
                          <List.Item>
                            <Card
                              hoverable
                              cover={
                                cover ? (
                                  <Image src={cover} alt={getTitle(h)} height={160} style={{ objectFit: 'cover' }} />
                                ) : undefined
                              }
                            >
                              <Space direction="vertical" size={8}>
                                <div style={{ fontWeight: 600 }}>{getTitle(h, '酒店')}</div>
                                <Space size={8}>
                                  {h?.rating && <Tag color="gold">评分 {h.rating}</Tag>}
                                  {getPrice(h) && <Tag color="orange">{getPrice(h)}</Tag>}
                                </Space>
                                {getDesc(h) && <div style={{ color: '#666' }}>{getDesc(h)}</div>}
                              </Space>
                            </Card>
                          </List.Item>
                        );
                      }}
                    />
                  ) : (
                    <Empty description="暂无数据" />
                  )
                ),
              },
              {
                key: 'attractions',
                label: '景点',
                children: (
                  (previewData.sections?.attractions || []).length ? (
                    <List
                      grid={{ gutter: 16, xs: 1, sm: 2, md: 3, lg: 4 }}
                      dataSource={previewData.sections?.attractions}
                      style={{ maxHeight: 420, overflow: 'auto', paddingRight: 8 }}
                      renderItem={(a: any) => {
                        const cover = getImage(a);
                        const title = getTitle(a, '景点');
                        const desc = getDesc(a);
                        return (
                          <List.Item>
                            <Card
                              hoverable
                              cover={
                                cover ? (
                                  <div style={{ position: 'relative', height: 160, overflow: 'hidden' }}>
                                    <Image src={cover} alt={title} height={160} style={{ objectFit: 'cover', width: '100%' }} />
                                    {a?.rating && (
                                      <Tag color="gold" style={{ position: 'absolute', top: 8, right: 8 }}>
                                        <StarFilled /> {a.rating}
                                      </Tag>
                                    )}
                                  </div>
                                ) : undefined
                              }
                            >
                              <Space direction="vertical" size={8}>
                                <div style={{ fontWeight: 600 }}>{title}</div>
                                <Space wrap size={6}>
                                  {a?.category && <Tag>{a.category}</Tag>}
                                  {a?.business_area && <Tag color="green">{a.business_area}</Tag>}
                                  {a?.distance && <Tag color="blue">距 {a.distance}m</Tag>}
                                  {a?.price_range && <Tag color="orange">{a.price_range}</Tag>}
                                </Space>
                                {a?.address && (
                                  <Text type="secondary">{a.address}</Text>
                                )}
                                {desc && <div style={{ color: '#666' }}>{desc}</div>}
                              </Space>
                            </Card>
                          </List.Item>
                        );
                      }}
                    />
                  ) : (
                    <Empty description="暂无数据" />
                  )
                ),
              },
              {
                key: 'restaurants',
                label: '餐厅',
                children: (
                  (previewData.sections?.restaurants || []).length ? (
                    <List
                      grid={{ gutter: 16, xs: 1, sm: 2, md: 3, lg: 4 }}
                      dataSource={previewData.sections?.restaurants}
                      style={{ maxHeight: 420, overflow: 'auto', paddingRight: 8 }}
                      renderItem={(r: any) => {
                        const cover = getImage(r);
                        const title = getTitle(r, '餐厅');
                        const desc = getDesc(r);
                        const price = getPrice(r);
                        return (
                          <List.Item>
                            <Card
                              hoverable
                              cover={
                                cover ? (
                                  <div style={{ position: 'relative', height: 160, overflow: 'hidden' }}>
                                    <Image src={cover} alt={title} height={160} style={{ objectFit: 'cover', width: '100%' }} />
                                    {r?.rating && (
                                      <Tag color="gold" style={{ position: 'absolute', top: 8, right: 8 }}>
                                        <StarFilled /> {r.rating}
                                      </Tag>
                                    )}
                                  </div>
                                ) : undefined
                              }
                            >
                              <Space direction="vertical" size={8}>
                                <div style={{ fontWeight: 600 }}>{title}</div>
                                <Space wrap size={6}>
                                  {price && <Tag color="orange">{price}</Tag>}
                                  {r?.price_range && <Tag color="orange">{r.price_range}</Tag>}
                                  {r?.opening_hours && <Tag icon={<ClockCircleOutlined />} color="green">{r.opening_hours}</Tag>}
                                  {r?.business_area && <Tag color="green">{r.business_area}</Tag>}
                                </Space>
                                {r?.address && <Text type="secondary">{r.address}</Text>}
                                {Array.isArray(r?.specialties) && r.specialties.length > 0 && (
                                  <Space wrap size={4}>
                                    {r.specialties.slice(0, 5).map((s: string, idx: number) => (
                                      <Tag key={idx} color="geekblue">{s}</Tag>
                                    ))}
                                  </Space>
                                )}
                                {desc && <div style={{ color: '#666' }}>{desc}</div>}
                              </Space>
                            </Card>
                          </List.Item>
                        );
                      }}
                    />
                  ) : (
                    <Empty description="暂无数据" />
                  )
                ),
              },
              {
                key: 'flights',
                label: '航班',
                children: (
                  (previewData.sections?.flights || []).length ? (
                    <List
                      itemLayout="vertical"
                      dataSource={previewData.sections?.flights}
                      style={{ maxHeight: 420, overflow: 'auto', paddingRight: 8 }}
                      renderItem={(f: any) => (
                        <List.Item>
                          <Card hoverable>
                            <Space wrap size={12}>
                              <div style={{ fontWeight: 600 }}>{getTitle(f, '航班')}</div>
                              {f?.airline && <Tag color="blue">{f.airline}</Tag>}
                              {f?.flight_no && <Tag>{f.flight_no}</Tag>}
                              {f?.departure_time && <Tag color="green">出发 {f.departure_time}</Tag>}
                              {f?.arrival_time && <Tag color="green">到达 {f.arrival_time}</Tag>}
                              {getPrice(f) && <Tag color="orange">{getPrice(f)}</Tag>}
                            </Space>
                            {getDesc(f) && (
                              <div style={{ marginTop: 8, color: '#666' }}>{getDesc(f)}</div>
                            )}
                          </Card>
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Empty description="暂无数据" />
                  )
                ),
              },
              {
                key: 'xhs',
                label: '小红书',
                children: (
                  (previewData.sections?.xiaohongshu_notes || []).length ? (
                    <List
                      grid={{ gutter: 16, xs: 1, sm: 2, md: 3, lg: 4 }}
                      dataSource={previewData.sections?.xiaohongshu_notes}
                      style={{ maxHeight: 420, overflow: 'auto', paddingRight: 8 }}
                      renderItem={(item: any) => {
                        const cover = getImage(item);
                        const title = getTitle(item);
                        const desc = getDesc(item);
                        const likes = getLikes(item);
                        const tags = Array.isArray(item?.tag_list) ? item.tag_list.slice(0, 5) : [];
                        const location = item?.location;
                        return (
                          <List.Item>
                            <Card
                              hoverable
                              cover={
                                cover ? (
                                  <div style={{ position: 'relative', height: 160, overflow: 'hidden' }}>
                                    <Image src={cover} alt={title} height={160} style={{ objectFit: 'cover', width: '100%' }} />
                                    {typeof likes === 'number' && (
                                      <Tag color="magenta" style={{ position: 'absolute', top: 8, right: 8 }}>
                                        <HeartOutlined /> {likes}
                                      </Tag>
                                    )}
                                  </div>
                                ) : undefined
                              }
                            >
                              <Space direction="vertical" size={8} style={{ width: '100%' }}>
                                <Tooltip title={title}>
                                  <div style={{ fontWeight: 600, lineHeight: 1.4, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                                    {title}
                                  </div>
                                </Tooltip>
                                {tags.length > 0 && (
                                  <Space wrap size={4}>
                                    {tags.map((t: string) => (
                                      <Tag key={t} color="geekblue">{t}</Tag>
                                    ))}
                                  </Space>
                                )}
                                {location && (
                                  <Tag icon={<EnvironmentOutlined />} color="green">
                                    {location}
                                  </Tag>
                                )}
                                {desc && (
                                  <div style={{ color: '#666', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                                    {desc}
                                  </div>
                                )}
                                <Space size={8}>
                                  {item?.url && (
                                    <Button size="small" type="link" href={item.url} target="_blank" icon={<LinkOutlined />}> 
                                      查看原文
                                    </Button>
                                  )}
                                </Space>
                              </Space>
                            </Card>
                          </List.Item>
                        );
                      }}
                    />
                  ) : (
                    <Empty description="暂无数据" />
                  )
                ),
              },
            ]}
          />
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
              <Col xs={24} sm={12} style={{ minWidth: 0 }}>
                <Form.Item
                  name="dateRange"
                  label="出行时间"
                  rules={[{ required: true, message: '请选择出行时间' }]}
                >
                  <RangePicker 
                    className="mobile-vertical-range"
                    popupClassName="mobile-vertical-range-dropdown"
                    style={{ width: '100%', minWidth: 0 }}
                    placeholder={["出发日期", "返回日期"]}
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
                  label="预算范围(单项开支)"
                  rules={[{ required: true, message: '请选择预算范围' }]}
                >
                  <Select placeholder="选择预算范围">
                    <Option value={200}>200元以下</Option>
                    <Option value={500}>500元以下</Option>
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
