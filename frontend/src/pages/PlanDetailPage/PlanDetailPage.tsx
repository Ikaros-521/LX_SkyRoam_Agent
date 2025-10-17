import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Button, 
  Row, 
  Col, 
  Typography, 
  Space,
  Tabs,
  Tag,
  List,
  Avatar,
  Divider,
  Alert,
  Spin,
  Modal,
  Rate,
  Image
} from 'antd';
import { 
  CalendarOutlined, 
  DollarOutlined,
  StarOutlined,
  EnvironmentOutlined,
  ClockCircleOutlined,
  ExportOutlined,
  ShareAltOutlined,
  EditOutlined,
  CloudOutlined,
  ThunderboltOutlined,
  PhoneOutlined,
  PictureOutlined,
  ShopOutlined,
  TagOutlined,
  HomeOutlined
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';
import MapComponent from '../../components/MapComponent/MapComponent';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

interface PlanDetail {
  id: number;
  title: string;
  destination: string;
  duration_days: number;
  generated_plans: any[];
  selected_plan: any;
  status: string;
  score: number;
}

const PlanDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [planDetail, setPlanDetail] = useState<PlanDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedPlanIndex, setSelectedPlanIndex] = useState(0);
  const [exportModalVisible, setExportModalVisible] = useState(false);
  const [showAllHotels, setShowAllHotels] = useState(false);

  useEffect(() => {
    fetchPlanDetail();
  }, [id]);

  const fetchPlanDetail = async () => {
    try {
      const response = await fetch(buildApiUrl(`/travel-plans/${id}`));
      if (!response.ok) {
        throw new Error('获取计划详情失败');
      }
      const data = await response.json();
      setPlanDetail(data);
    } catch (error) {
      console.error('获取计划详情失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPlan = async (planIndex: number) => {
    try {
      const response = await fetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_SELECT(Number(id))), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ plan_index: planIndex }),
      });

      if (response.ok) {
        setSelectedPlanIndex(planIndex);
        fetchPlanDetail(); // 刷新数据
        console.log(`方案 ${planIndex} 选择成功`);
      } else {
        const errorData = await response.json();
        console.error('选择方案失败:', errorData);
      }
    } catch (error) {
      console.error('选择方案失败:', error);
    }
  };

  const handleExport = async (format: string) => {
    try {
      const response = await fetch(buildApiUrl(`/travel-plans/${id}/export?format=${format}`));
      if (response.ok) {
        // 处理导出逻辑
        console.log(`导出为 ${format} 格式`);
      }
    } catch (error) {
      console.error('导出失败:', error);
    }
    setExportModalVisible(false);
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <div style={{ marginTop: '16px' }}>
          <Text>加载中...</Text>
        </div>
      </div>
    );
  }

  if (!planDetail) {
    return (
      <Alert
        message="计划不存在"
        description="您访问的旅行计划不存在或已被删除。"
        type="error"
        showIcon
      />
    );
  }

  const currentPlan = planDetail.generated_plans?.[selectedPlanIndex];

  // 格式化餐厅图片URL
  const formatRestaurantImage = (photos: any): string | undefined => {
    if (!photos || !Array.isArray(photos) || photos.length === 0) {
      return undefined;
    }
    
    const firstPhoto = photos[0];
    
    // 如果是对象，提取url属性
    if (typeof firstPhoto === 'object' && firstPhoto.url) {
      return firstPhoto.url;
    }
    
    // 如果是字符串且是完整的URL，直接返回
    if (typeof firstPhoto === 'string' && firstPhoto.startsWith('http')) {
      return firstPhoto;
    }
    
    // 如果是字符串但是相对路径，添加基础URL
    if (typeof firstPhoto === 'string') {
      return `https://example.com${firstPhoto}`;
    }
    
    return undefined;
  };

  // 格式化价格信息
  const formatPrice = (restaurant: any): string => {
    if (restaurant.price_range) {
      return restaurant.price_range;
    }
    if (restaurant.cost) {
      return `¥${restaurant.cost}`;
    }
    return '价格面议';
  };

  // 格式化距离信息
  const formatDistance = (distance: any): string => {
    if (!distance || distance === '未知') return '';
    
    if (typeof distance === 'number') {
      if (distance < 1000) {
        return `${distance}m`;
      } else {
        return `${(distance / 1000).toFixed(1)}km`;
      }
    }
    
    if (typeof distance === 'string') {
      // 处理字符串格式的距离，如 "1200" 或 "1.2km"
      const numMatch = distance.match(/(\d+\.?\d*)/);
      if (numMatch) {
        const num = parseFloat(numMatch[1]);
        if (distance.includes('km')) {
          return `${num}km`;
        } else if (distance.includes('m')) {
          return `${num}m`;
        } else {
          // 假设是米
          if (num < 1000) {
            return `${num}m`;
          } else {
            return `${(num / 1000).toFixed(1)}km`;
          }
        }
      }
    }
    
    return String(distance);
  };

  // 安全格式化展示交通信息，避免将对象直接作为 React 子节点
  const formatTransportation = (transportation: any): React.ReactNode => {
    if (!transportation) return '暂无';

    if (Array.isArray(transportation)) {
      return (
        <Space wrap size="small">
          {transportation.map((t: any, idx: number) => {
            if (t == null) return <span key={idx}>-</span>;
            if (typeof t === 'object') {
              const type = t.type || '交通';
              const distance = typeof t.distance === 'number' ? `${t.distance} 公里` : (t.distance || '');
              const duration = typeof t.duration === 'number' ? `${t.duration} 分钟` : (t.duration || '');
              const cost = t.cost != null ? `¥${t.cost}` : '';
              const parts = [type, distance, duration, cost].filter(Boolean).join(' · ');
              return <span key={idx}>{parts || type}</span>;
            }
            return <span key={idx}>{String(t)}</span>;
          })}
        </Space>
      );
    }

    if (typeof transportation === 'object') {
      const type = transportation.type || '交通';
      const distance = typeof transportation.distance === 'number' ? `${transportation.distance} 公里` : (transportation.distance || '');
      const duration = typeof transportation.duration === 'number' ? `${transportation.duration} 分钟` : (transportation.duration || '');
      const cost = transportation.cost != null ? `¥${transportation.cost}` : '';
      const parts = [type, distance, duration, cost].filter(Boolean).join(' · ');
      return parts || type;
    }

    return String(transportation);
  };

  return (
    <div className="plan-detail-page" style={{ maxWidth: '1200px', margin: '0 auto' }}>
      {/* 计划头部信息 */}
      <Card style={{ marginBottom: '24px' }}>
        <Row gutter={[24, 16]} align="middle">
          <Col xs={24} md={16}>
            <Space direction="vertical" size="small">
              <Title level={2} style={{ margin: 0 }}>
                {planDetail.title}
              </Title>
              <Space>
                <Tag color="blue" icon={<EnvironmentOutlined />}>
                  {planDetail.destination}
                </Tag>
                <Tag color="green" icon={<CalendarOutlined />}>
                  {planDetail.duration_days} 天
                </Tag>
                <Tag color="orange" icon={<StarOutlined />}>
                  评分: {planDetail.score?.toFixed(1) || 'N/A'}
                </Tag>
              </Space>
            </Space>
          </Col>
          <Col xs={24} md={8}>
            <Space>
              <Button 
                icon={<EditOutlined />}
                onClick={() => navigate(`/plan?edit=${id}`)}
              >
                编辑
              </Button>
              <Button 
                icon={<ShareAltOutlined />}
                onClick={() => setExportModalVisible(true)}
              >
                分享
              </Button>
              <Button 
                type="primary"
                icon={<ExportOutlined />}
                onClick={() => setExportModalVisible(true)}
              >
                导出
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 方案选择 */}
      {planDetail.generated_plans && planDetail.generated_plans.length > 1 && (
        <Card title="选择方案" style={{ marginBottom: '24px' }}>
          <Row gutter={[16, 16]}>
            {planDetail.generated_plans.map((plan, index) => (
              <Col xs={24} sm={12} md={8} key={index}>
                <Card
                  size="small"
                  hoverable
                  onClick={() => handleSelectPlan(index)}
                  style={{
                    border: selectedPlanIndex === index ? '2px solid #1890ff' : '1px solid #d9d9d9',
                    cursor: 'pointer'
                  }}
                >
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <Text strong>{plan.type}</Text>
                    <Text type="secondary">{plan.title}</Text>
                    <Space>
                      <Text>评分: {plan.score?.toFixed(1)}</Text>
                      <Text type="secondary">
                        预算: ¥{plan.total_cost?.total?.toLocaleString()}
                      </Text>
                    </Space>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      )}

      {/* 方案详情 */}
      {currentPlan && (
        <Tabs defaultActiveKey="overview" style={{ marginBottom: '24px' }}>
          <TabPane tab="方案概览" key="overview">
            <Row gutter={[24, 24]}>
              <Col xs={24} lg={16}>
                <Card title="行程安排">
                  <List
                    dataSource={currentPlan.daily_itineraries}
                    renderItem={(day: any, index: number) => (
                      <List.Item>
                        <Card size="small" style={{ width: '100%' }}>
                          <Space direction="vertical" size="small" style={{ width: '100%' }}>
                            <Title level={4}>第 {day.day} 天 - {day.date}</Title>
                            <List
                              size="small"
                              dataSource={day.attractions}
                              renderItem={(attraction: any) => (
                                <List.Item>
                                  <Space>
                                    <Avatar size="small" icon={<EnvironmentOutlined />} />
                                    <div>
                                      <Text strong>{attraction.name}</Text>
                                      <br />
                                      <Text type="secondary">{attraction.category}</Text>
                                    </div>
                                    <Rate disabled defaultValue={attraction.rating || 0} />
                                  </Space>
                                </List.Item>
                              )}
                            />
                            <Divider />
                            <Row gutter={16}>
                              <Col span={24}>
                                <Text type="secondary">餐饮推荐</Text>
                                <div style={{ marginTop: '8px' }}>
                                  {day.meals && day.meals.length > 0 ? (
                                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                                      {day.meals.map((meal: any, mealIndex: number) => (
                                        <Card key={mealIndex} size="small" style={{ backgroundColor: '#fafafa' }}>
                                          <Row gutter={[8, 4]} align="middle">
                                            <Col span={16}>
                                              <Space direction="vertical" size={2}>
                                                <Text strong style={{ fontSize: '13px' }}>
                                                  {meal.name || meal.suggestion}
                                                </Text>
                                                {meal.category && (
                                                  <Text type="secondary" style={{ fontSize: '11px' }}>
                                                    {meal.category}
                                                  </Text>
                                                )}
                                                {meal.address && (
                                                  <Text 
                                                    type="secondary" 
                                                    style={{ 
                                                      fontSize: '10px',
                                                      wordBreak: 'break-all',
                                                      whiteSpace: 'normal',
                                                      lineHeight: '1.4'
                                                    }}
                                                  >
                                                    <EnvironmentOutlined style={{ marginRight: '4px' }} /> {meal.address}
                                                  </Text>
                                                )}
                                              </Space>
                                            </Col>
                                            <Col span={8} style={{ textAlign: 'right' }}>
                                              <Space direction="vertical" size={2} align="end">
                                                {meal.rating && (
                                                  <Rate 
                                                    disabled 
                                                    defaultValue={meal.rating} 
                                                    style={{ fontSize: '10px' }}
                                                  />
                                                )}
                                                <Text style={{ fontSize: '11px', color: '#52c41a' }}>
                                                   <DollarOutlined /> {formatPrice(meal)}
                                                 </Text>
                                                {meal.phone && (
                                                  <Text style={{ fontSize: '10px', color: '#1890ff' }}>
                                                    <PhoneOutlined /> {meal.phone}
                                                  </Text>
                                                )}
                                              </Space>
                                            </Col>
                                          </Row>
                                        </Card>
                                      ))}
                                    </Space>
                                  ) : (
                                    <Text type="secondary">暂无餐饮推荐</Text>
                                  )}
                                </div>
                              </Col>
                            </Row>
                            <Divider />
                            <Row gutter={16}>
                              <Col span={12}>
                                <Text type="secondary">交通</Text>
                                <br />
                                <Text>{formatTransportation(day.transportation)}</Text>
                              </Col>
                              <Col span={12}>
                                <Text type="secondary">预计费用</Text>
                                <br />
                                <Text>¥{day.estimated_cost}</Text>
                              </Col>
                            </Row>
                          </Space>
                        </Card>
                      </List.Item>
                    )}
                  />
                </Card>
              </Col>
              
              <Col xs={24} lg={8}>
                <Space direction="vertical" size="large" style={{ width: '100%' }}>
                  {/* 预算分析 */}
                  <Card title="预算分析" size="small">
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      <Row justify="space-between">
                        <Text>机票</Text>
                        <Text>¥{currentPlan.total_cost?.flight || 0}</Text>
                      </Row>
                      <Row justify="space-between">
                        <Text>酒店</Text>
                        <Text>¥{currentPlan.total_cost?.hotel || 0}</Text>
                      </Row>
                      <Row justify="space-between">
                        <Text>景点</Text>
                        <Text>¥{currentPlan.total_cost?.attractions || 0}</Text>
                      </Row>
                      <Row justify="space-between">
                        <Text>餐饮</Text>
                        <Text>¥{currentPlan.total_cost?.meals || 0}</Text>
                      </Row>
                      <Row justify="space-between">
                        <Text>交通</Text>
                        <Text>¥{currentPlan.total_cost?.transportation || 0}</Text>
                      </Row>
                      <Divider />
                      <Row justify="space-between">
                        <Text strong>总计</Text>
                        <Text strong>¥{currentPlan.total_cost?.total || 0}</Text>
                      </Row>
                    </Space>
                  </Card>

                  {/* 天气信息 */}
                  {currentPlan.weather_info && (
                    <Card title={
                      <Space>
                        <CloudOutlined />
                        <span>天气信息</span>
                      </Space>
                    } size="small" styles={{ body: { padding: '16px' } }}>
                      <Space direction="vertical" size="small" style={{ width: '100%' }}>
                        {/* 天气预报数据 */}
                        {currentPlan.weather_info.raw_data && Object.keys(currentPlan.weather_info.raw_data).length > 0 && (
                          <div>
                            {/* 地点信息 */}
                            {currentPlan.weather_info.raw_data.location && (
                              <div style={{ marginBottom: '12px' }}>
                                <Text strong style={{ color: '#1890ff' }}>
                                  📍 {currentPlan.weather_info.raw_data.location} 天气预报
                                </Text>
                              </div>
                            )}
                            
                            {/* 多天天气预报 */}
                            {currentPlan.weather_info.raw_data.forecast && currentPlan.weather_info.raw_data.forecast.length > 0 && (
                              <div style={{ marginBottom: '12px' }}>
                                {currentPlan.weather_info.raw_data.forecast.map((day: any, index: number) => (
                                  <div key={index} style={{ 
                                    padding: '8px', 
                                    border: '1px solid #f0f0f0', 
                                    borderRadius: '6px', 
                                    marginBottom: '8px',
                                    backgroundColor: index === 0 ? '#f6ffed' : '#fafafa'
                                  }}>
                                    <Row justify="space-between" align="middle">
                                      <Col span={8}>
                                        <Text strong style={{ color: index === 0 ? '#52c41a' : '#666' }}>
                                          {day.date} {day.week && `周${day.week}`}
                                        </Text>
                                      </Col>
                                      <Col span={8} style={{ textAlign: 'center' }}>
                                        <div>
                                          <Text style={{ fontSize: '12px', color: '#666' }}>
                                            {day.dayweather}
                                          </Text>
                                          {day.nightweather && day.nightweather !== day.dayweather && (
                                            <Text style={{ fontSize: '12px', color: '#666' }}>
                                              转{day.nightweather}
                                            </Text>
                                          )}
                                        </div>
                                      </Col>
                                      <Col span={8} style={{ textAlign: 'right' }}>
                                        <Text strong style={{ color: '#ff4d4f' }}>
                                          {day.daytemp}°
                                        </Text>
                                        <Text style={{ color: '#1890ff', margin: '0 4px' }}>
                                          /
                                        </Text>
                                        <Text style={{ color: '#1890ff' }}>
                                          {day.nighttemp}°
                                        </Text>
                                      </Col>
                                    </Row>
                                    {(day.daywind || day.daypower) && (
                                      <Row style={{ marginTop: '4px' }}>
                                        <Text style={{ fontSize: '11px', color: '#999' }}>
                                          {day.daywind} {day.daypower}级
                                        </Text>
                                      </Row>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}
                            
                            {/* 兼容旧格式的天气数据 */}
                            {!currentPlan.weather_info.raw_data.forecast && (
                              <div style={{ marginTop: '8px' }}>
                                {currentPlan.weather_info.raw_data.temperature && (
                                  <Row justify="space-between">
                                    <Text>温度</Text>
                                    <Text>{currentPlan.weather_info.raw_data.temperature}°C</Text>
                                  </Row>
                                )}
                                {currentPlan.weather_info.raw_data.weather && (
                                  <Row justify="space-between">
                                    <Text>天气</Text>
                                    <Text>{currentPlan.weather_info.raw_data.weather}</Text>
                                  </Row>
                                )}
                                {currentPlan.weather_info.raw_data.humidity && (
                                  <Row justify="space-between">
                                    <Text>湿度</Text>
                                    <Text>{currentPlan.weather_info.raw_data.humidity}%</Text>
                                  </Row>
                                )}
                                {currentPlan.weather_info.raw_data.wind_speed && (
                                  <Row justify="space-between">
                                    <Text>风速</Text>
                                    <Text>{currentPlan.weather_info.raw_data.wind_speed} km/h</Text>
                                  </Row>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                        
                        {/* 旅游建议 */}
                        {currentPlan.weather_info.travel_recommendations && currentPlan.weather_info.travel_recommendations.length > 0 && (
                          <div>
                            <Divider style={{ margin: '12px 0' }} />
                            <Text strong style={{ color: '#52c41a' }}>
                              <ThunderboltOutlined /> 旅游建议
                            </Text>
                            <div style={{ marginTop: '8px' }}>
                              {currentPlan.weather_info.travel_recommendations.map((recommendation: string, index: number) => (
                                <div key={index} style={{ marginBottom: '4px' }}>
                                  <Text type="secondary" style={{ fontSize: '12px' }}>
                                    • {recommendation}
                                  </Text>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </Space>
                    </Card>
                  )}

                  {/* 推荐餐厅 */}
                  <Card title={
                    <Space>
                      <ShopOutlined />
                      <span>推荐餐厅</span>
                    </Space>
                  } size="small">
                    <List
                      size="small"
                      dataSource={currentPlan.restaurants}
                      renderItem={(restaurant: any) => (
                        <List.Item style={{ padding: '12px 0' }}>
                          <Card 
                            size="small" 
                            style={{ width: '100%' }}
                            bodyStyle={{ padding: '12px' }}
                          >
                            <Row gutter={[12, 8]} align="top">
                              {/* 餐厅图片 */}
                               <Col span={6}>
                                 {formatRestaurantImage(restaurant.photos) ? (
                                   <Image
                                     width={60}
                                     height={60}
                                     src={formatRestaurantImage(restaurant.photos)}
                                     alt={restaurant.name}
                                     style={{ borderRadius: '6px', objectFit: 'cover' }}
                                     fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjYwIiBoZWlnaHQ9IjYwIiBmaWxsPSIjRjVGNUY1Ii8+CjxwYXRoIGQ9Ik0yMCAyMEg0MFY0MEgyMFYyMFoiIGZpbGw9IiNEOUQ5RDkiLz4KPC9zdmc+"
                                     preview={{
                                       mask: <PictureOutlined style={{ fontSize: '16px' }} />
                                     }}
                                   />
                                 ) : (
                                   <div 
                                     style={{ 
                                       width: 60, 
                                       height: 60, 
                                       backgroundColor: '#f5f5f5', 
                                       borderRadius: '6px',
                                       display: 'flex',
                                       alignItems: 'center',
                                       justifyContent: 'center'
                                     }}
                                   >
                                     <PictureOutlined style={{ color: '#ccc', fontSize: '20px' }} />
                                   </div>
                                 )}
                               </Col>
                              
                              {/* 餐厅基本信息 */}
                              <Col span={18}>
                                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                                  {/* 餐厅名称和评分 */}
                                  <Row justify="space-between" align="middle">
                                    <Col>
                                      <Text strong style={{ fontSize: '14px' }}>
                                        {restaurant.name}
                                      </Text>
                                    </Col>
                                    <Col>
                                      <Space size={4}>
                                        <Rate 
                                          disabled 
                                          defaultValue={restaurant.rating || 0} 
                                          style={{ fontSize: '12px' }}
                                        />
                                        <Text style={{ fontSize: '12px', color: '#666' }}>
                                          {restaurant.rating ? restaurant.rating.toFixed(1) : 'N/A'}
                                        </Text>
                                      </Space>
                                    </Col>
                                  </Row>
                                  
                                  {/* 菜系类型和价格范围 */}
                                  <Row justify="space-between" align="middle">
                                    <Col>
                                      <Space size={4}>
                                        <TagOutlined style={{ fontSize: '12px', color: '#666' }} />
                                        <Text type="secondary" style={{ fontSize: '12px' }}>
                                          {restaurant.cuisine_type || restaurant.category || '餐厅'}
                                        </Text>
                                      </Space>
                                    </Col>
                                    <Col>
                                       <Space size={4}>
                                         <DollarOutlined style={{ fontSize: '12px', color: '#52c41a' }} />
                                         <Text style={{ fontSize: '12px', color: '#52c41a' }}>
                                           {formatPrice(restaurant)}
                                         </Text>
                                       </Space>
                                     </Col>
                                  </Row>
                                  
                                  {/* 地址信息 */}
                                  {restaurant.address && (
                                    <Row>
                                      <Col span={24}>
                                        <Space size={4} align="start">
                                          <EnvironmentOutlined style={{ fontSize: '12px', color: '#666', marginTop: '2px' }} />
                                          <Text 
                                            type="secondary" 
                                            style={{ 
                                              fontSize: '11px',
                                              wordBreak: 'break-all',
                                              whiteSpace: 'normal',
                                              lineHeight: '1.4'
                                            }}
                                          >
                                            {restaurant.address}
                                          </Text>
                                        </Space>
                                      </Col>
                                    </Row>
                                  )}
                                  
                                  {/* 电话和距离 */}
                                  <Row justify="space-between" align="middle">
                                    {restaurant.phone && (
                                      <Col>
                                        <Space size={4}>
                                          <PhoneOutlined style={{ fontSize: '12px', color: '#1890ff' }} />
                                          <Text style={{ fontSize: '11px', color: '#1890ff' }}>
                                            {restaurant.phone}
                                          </Text>
                                        </Space>
                                      </Col>
                                    )}
                                    {restaurant.distance && (
                                       <Col>
                                         <Text type="secondary" style={{ fontSize: '11px' }}>
                                           距离: {formatDistance(restaurant.distance)}
                                         </Text>
                                       </Col>
                                     )}
                                  </Row>
                                  
                                  {/* 营业区域和标签 */}
                                  {(restaurant.business_area || restaurant.tags) && (
                                    <Row>
                                      <Col span={24}>
                                        <Space size={4} wrap>
                                          {restaurant.business_area && (
                                            <Tag color="blue" style={{ fontSize: '11px' }}>
                                               {restaurant.business_area}
                                             </Tag>
                                          )}
                                          {restaurant.tags && restaurant.tags.slice(0, 2).map((tag: string, index: number) => (
                                            <Tag key={index} color="default" style={{ fontSize: '11px' }}>
                                               {tag}
                                             </Tag>
                                          ))}
                                        </Space>
                                      </Col>
                                    </Row>
                                  )}
                                </Space>
                              </Col>
                            </Row>
                          </Card>
                        </List.Item>
                      )}
                    />
                  </Card>

                </Space>
              </Col>
            </Row>
            
            {/* 地图组件 - 独立的全宽区域 */}
            <Row style={{ marginTop: '24px' }}>
              <Col span={24}>
                <MapComponent 
                  destination={currentPlan?.destination || planDetail?.destination}
                  latitude={currentPlan.destination_info?.latitude || 39.9042}
                  longitude={currentPlan.destination_info?.longitude || 116.4074}
                  title="目的地地图"
                />
              </Col>
            </Row>
          </TabPane>

          <TabPane tab="详细信息" key="details">
            <Row gutter={[24, 24]}>
              <Col xs={24} md={12}>
                <Card title="航班信息" size="small">
                  {currentPlan.flight ? (
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      {/* 航班基本信息 */}
                      <Row justify="space-between" align="middle">
                        <Col>
                          <Text strong style={{ fontSize: '16px' }}>
                            {currentPlan.flight.flight_number || 'N/A'}
                          </Text>
                        </Col>
                        <Col>
                          <Tag color="blue">
                            {currentPlan.flight.cabin_class || '经济舱'}
                          </Tag>
                        </Col>
                      </Row>
                      
                      {/* 航空公司 */}
                      <Row>
                        <Text>
                          <strong>航空公司:</strong> {currentPlan.flight.airline_name || currentPlan.flight.airline || 'N/A'}
                        </Text>
                      </Row>
                      
                      {/* 时间信息 */}
                      <Row gutter={16}>
                        <Col span={12}>
                          <Space direction="vertical" size={2}>
                            <Text type="secondary" style={{ fontSize: '12px' }}>出发时间</Text>
                            <Text strong>
                              {currentPlan.flight.departure_time ? 
                                (currentPlan.flight.departure_time.includes('T') ? 
                                  currentPlan.flight.departure_time.split('T')[1].substring(0, 5) : 
                                  currentPlan.flight.departure_time) : 'N/A'}
                            </Text>
                            <Text type="secondary" style={{ fontSize: '11px' }}>
                              {currentPlan.flight.origin || 'N/A'}
                            </Text>
                          </Space>
                        </Col>
                        <Col span={12}>
                          <Space direction="vertical" size={2}>
                            <Text type="secondary" style={{ fontSize: '12px' }}>到达时间</Text>
                            <Text strong>
                              {currentPlan.flight.arrival_time ? 
                                (currentPlan.flight.arrival_time.includes('T') ? 
                                  currentPlan.flight.arrival_time.split('T')[1].substring(0, 5) : 
                                  currentPlan.flight.arrival_time) : 'N/A'}
                            </Text>
                            <Text type="secondary" style={{ fontSize: '11px' }}>
                              {currentPlan.flight.destination || 'N/A'}
                            </Text>
                          </Space>
                        </Col>
                      </Row>
                      
                      {/* 飞行时长和中转 */}
                      <Row gutter={16}>
                        <Col span={12}>
                          <Text>
                            <strong>飞行时长:</strong> {currentPlan.flight.duration || 'N/A'}
                          </Text>
                        </Col>
                        <Col span={12}>
                          <Text>
                            <strong>中转:</strong> {
                              currentPlan.flight.stops === 0 ? '直飞' : 
                              currentPlan.flight.stops ? `${currentPlan.flight.stops}次中转` : 'N/A'
                            }
                          </Text>
                        </Col>
                      </Row>
                      
                      {/* 价格信息 */}
                      <Row justify="space-between" align="middle" style={{ 
                        padding: '8px 12px', 
                        backgroundColor: '#f6ffed', 
                        borderRadius: '6px',
                        border: '1px solid #b7eb8f'
                      }}>
                        <Col>
                          <Text strong style={{ color: '#52c41a', fontSize: '16px' }}>
                            ¥{currentPlan.flight.price_cny || currentPlan.flight.price || 'N/A'}
                          </Text>
                        </Col>
                        <Col>
                          {currentPlan.flight.currency && currentPlan.flight.currency !== 'CNY' && (
                            <Text type="secondary" style={{ fontSize: '12px' }}>
                              原价: {currentPlan.flight.price} {currentPlan.flight.currency}
                            </Text>
                          )}
                        </Col>
                      </Row>
                      
                      {/* 行李额度 */}
                      {currentPlan.flight.baggage_allowance && (
                        <Row>
                          <Text style={{ fontSize: '12px' }}>
                            <strong>行李额度:</strong> {currentPlan.flight.baggage_allowance}
                          </Text>
                        </Row>
                      )}
                    </Space>
                  ) : (
                    <Text type="secondary">暂无航班信息</Text>
                  )}
                </Card>
              </Col>
              
              <Col xs={24} md={12}>
                <Card title={
                  <Space>
                    <ShopOutlined />
                    <span>酒店信息</span>
                  </Space>
                } size="small">
                  {currentPlan.hotel ? (
                    <Card 
                      size="small" 
                      style={{ width: '100%' }}
                      bodyStyle={{ padding: '12px' }}
                    >
                      <Row gutter={[12, 8]} align="top">
                        {/* 酒店图片 */}
                        <Col span={6}>
                          {currentPlan.hotel.images && currentPlan.hotel.images.length > 0 ? (
                            <Image
                              width={70}
                              height={70}
                              src={currentPlan.hotel.images[0]}
                              alt={currentPlan.hotel.name}
                              style={{ borderRadius: '8px', objectFit: 'cover' }}
                              fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjYwIiBoZWlnaHQ9IjYwIiBmaWxsPSIjRjVGNUY1Ii8+CjxwYXRoIGQ9Ik0yMCAyMEg0MFY0MEgyMFYyMFoiIGZpbGw9IiNEOUQ5RDkiLz4KPC9zdmc+"
                              preview={{
                                mask: <PictureOutlined style={{ fontSize: '16px' }} />
                              }}
                            />
                          ) : (
                            <div 
                              style={{ 
                                width: 70, 
                                height: 70, 
                                backgroundColor: '#f5f5f5', 
                                borderRadius: '8px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                border: '1px solid #e8e8e8'
                              }}
                            >
                              <PictureOutlined style={{ color: '#ccc', fontSize: '24px' }} />
                            </div>
                          )}
                        </Col>
                        
                        {/* 酒店基本信息 */}
                        <Col span={18}>
                          <Space direction="vertical" size={4} style={{ width: '100%' }}>
                            {/* 酒店名称和评分 */}
                            <Row justify="space-between" align="middle">
                              <Col>
                                <Text strong style={{ fontSize: '14px' }}>
                                  {currentPlan.hotel.name}
                                </Text>
                              </Col>
                              <Col>
                                <Space size={4}>
                                  <Rate 
                                    disabled 
                                    defaultValue={currentPlan.hotel.rating || 0} 
                                    style={{ fontSize: '12px' }}
                                  />
                                  <Text style={{ fontSize: '12px', color: '#666' }}>
                                    {currentPlan.hotel.rating ? currentPlan.hotel.rating.toFixed(1) : 'N/A'}
                                  </Text>
                                </Space>
                              </Col>
                            </Row>
                            
                            {/* 星级和价格 */}
                            <Row justify="space-between" align="middle">
                              <Col>
                                <Space size={4}>
                                  <StarOutlined style={{ fontSize: '12px', color: '#faad14' }} />
                                  <Text type="secondary" style={{ fontSize: '12px' }}>
                                    {currentPlan.hotel.star_rating ? `${currentPlan.hotel.star_rating}星级` : '星级未知'}
                                  </Text>
                                </Space>
                              </Col>
                              <Col>
                                <Space size={4}>
                                  <DollarOutlined style={{ fontSize: '12px', color: '#52c41a' }} />
                                  <Text style={{ fontSize: '12px', color: '#52c41a' }}>
                                    每晚: ¥{currentPlan.hotel.price_per_night}
                                  </Text>
                                </Space>
                              </Col>
                            </Row>
                            
                            {/* 地址信息 */}
                            {currentPlan.hotel.address && (
                              <Row>
                                <Col span={24}>
                                  <Space size={4} align="start">
                                    <EnvironmentOutlined style={{ fontSize: '12px', color: '#666', marginTop: '2px' }} />
                                    <Text 
                                      type="secondary" 
                                      style={{ 
                                        fontSize: '11px',
                                        wordBreak: 'break-all',
                                        whiteSpace: 'normal',
                                        lineHeight: '1.4'
                                      }}
                                    >
                                      {currentPlan.hotel.address}
                                    </Text>
                                  </Space>
                                </Col>
                              </Row>
                            )}
                            
                            {/* 电话和距离 */}
                            <Row justify="space-between" align="middle">
                              {currentPlan.hotel.phone && (
                                <Col>
                                  <Space size={4}>
                                    <PhoneOutlined style={{ fontSize: '12px', color: '#1890ff' }} />
                                    <Text style={{ fontSize: '11px', color: '#1890ff' }}>
                                      {currentPlan.hotel.phone}
                                    </Text>
                                  </Space>
                                </Col>
                              )}
                              {currentPlan.hotel.distance && (
                                <Col>
                                  <Text type="secondary" style={{ fontSize: '11px' }}>
                                    距离: {formatDistance(currentPlan.hotel.distance)}
                                  </Text>
                                </Col>
                              )}
                            </Row>
                            
                            {/* 酒店设施 */}
                            {currentPlan.hotel.amenities && currentPlan.hotel.amenities.length > 0 && (
                              <Row>
                                <Col span={24}>
                                  <Space size={4} wrap>
                                    {currentPlan.hotel.amenities.slice(0, 4).map((amenity: string, index: number) => (
                                      <Tag 
                                        key={index} 
                                        color="blue"
                                        style={{ 
                                          fontSize: '10px', 
                                          padding: '2px 6px',
                                          margin: '1px',
                                          height: '20px',
                                          lineHeight: '16px',
                                          borderRadius: '4px'
                                        }}
                                      >
                                        {amenity}
                                      </Tag>
                                    ))}
                                    {currentPlan.hotel.amenities.length > 4 && (
                                      <Text type="secondary" style={{ fontSize: '10px', fontWeight: '500' }}>
                                        +{currentPlan.hotel.amenities.length - 4}项
                                      </Text>
                                    )}
                                  </Space>
                                </Col>
                              </Row>
                            )}
                            
                            {/* 入住退房时间 */}
                            {(currentPlan.hotel.check_in || currentPlan.hotel.check_out) && (
                              <Row>
                                <Col span={24}>
                                  <Space size={8}>
                                    {currentPlan.hotel.check_in && (
                                      <Text type="secondary" style={{ fontSize: '10px' }}>
                                        <ClockCircleOutlined style={{ marginRight: '2px' }} />
                                        入住: {currentPlan.hotel.check_in}
                                      </Text>
                                    )}
                                    {currentPlan.hotel.check_out && (
                                      <Text type="secondary" style={{ fontSize: '10px' }}>
                                        退房: {currentPlan.hotel.check_out}
                                      </Text>
                                    )}
                                  </Space>
                                </Col>
                              </Row>
                            )}
                          </Space>
                        </Col>
                      </Row>
                    </Card>
                  ) : (
                    <Text type="secondary">暂无酒店信息</Text>
                  )}
                  
                  {/* 更多酒店选择 */}
                  {currentPlan.hotel?.available_options && currentPlan.hotel.available_options.length > 1 && (
                    <Card 
                      size="small" 
                      title={
                        <Space>
                          <HomeOutlined />
                          <span>更多酒店选择</span>
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            ({currentPlan.hotel.available_options.length}个选项)
                          </Text>
                        </Space>
                      }
                      style={{ marginTop: '12px' }}
                    >
                      <Row gutter={[8, 8]}>
                        {(showAllHotels 
                          ? currentPlan.hotel.available_options.slice(1) 
                          : currentPlan.hotel.available_options.slice(1, 6)
                        ).map((hotel: any, index: number) => (
                          <Col span={24} key={index}>
                            <Card size="small" style={{ backgroundColor: '#fafafa' }}>
                              <Row gutter={8} align="middle">
                                <Col flex="60px">
                                  <div style={{
                                    width: '50px',
                                    height: '50px',
                                    backgroundColor: '#f0f0f0',
                                    borderRadius: '4px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontSize: '20px'
                                  }}>
                                    🏨
                                  </div>
                                </Col>
                                <Col flex="auto">
                                  <Space direction="vertical" size={2} style={{ width: '100%' }}>
                                    <Row justify="space-between" align="middle">
                                      <Col>
                                        <Text strong style={{ fontSize: '13px' }}>
                                          {hotel.name}
                                        </Text>
                                      </Col>
                                      <Col>
                                        <Rate 
                                          disabled 
                                          value={hotel.star_rating || Math.round(hotel.rating)} 
                                          style={{ fontSize: '10px' }}
                                        />
                                      </Col>
                                    </Row>
                                    
                                    <Row gutter={[8, 2]}>
                                      <Col span={8}>
                                        <Text style={{ fontSize: '11px', color: '#ff4d4f' }}>
                                          ¥{hotel.price_per_night}/晚
                                        </Text>
                                      </Col>
                                      <Col span={8}>
                                        <Text type="secondary" style={{ fontSize: '10px' }}>
                                          评分: {hotel.rating}
                                        </Text>
                                      </Col>
                                      {hotel.distance && formatDistance(hotel.distance) && (
                                        <Col span={8}>
                                          <Text type="secondary" style={{ fontSize: '10px' }}>
                                            距离: {formatDistance(hotel.distance)}
                                          </Text>
                                        </Col>
                                      )}
                                    </Row>
                                    
                                    <Row>
                                      <Col span={24}>
                                        <Text 
                                          type="secondary" 
                                          style={{ 
                                            fontSize: '10px',
                                            display: '-webkit-box',
                                            WebkitLineClamp: 1,
                                            WebkitBoxOrient: 'vertical',
                                            overflow: 'hidden'
                                          }}
                                        >
                                          {hotel.address}
                                        </Text>
                                      </Col>
                                    </Row>
                                    
                                    {hotel.amenities && hotel.amenities.length > 0 && (
                                      <Row>
                                        <Col span={24}>
                                          <Space size={2} wrap>
                                            {hotel.amenities.slice(0, 3).map((amenity: string, amenityIndex: number) => (
                                              <Tag 
                                                key={amenityIndex} 
                                                style={{ 
                                                  fontSize: '9px', 
                                                  padding: '0px 3px',
                                                  margin: '1px',
                                                  height: '16px',
                                                  lineHeight: '14px'
                                                }}
                                              >
                                                {amenity}
                                              </Tag>
                                            ))}
                                            {hotel.amenities.length > 3 && (
                                              <Text type="secondary" style={{ fontSize: '9px' }}>
                                                +{hotel.amenities.length - 3}项
                                              </Text>
                                            )}
                                          </Space>
                                        </Col>
                                      </Row>
                                    )}
                                  </Space>
                                </Col>
                              </Row>
                            </Card>
                          </Col>
                        ))}
                        
                        {currentPlan.hotel.available_options.length > 6 && (
                          <Col span={24}>
                            <div style={{ textAlign: 'center', marginTop: '8px' }}>
                              <Button 
                                type="link" 
                                size="small"
                                onClick={() => setShowAllHotels(!showAllHotels)}
                                style={{ fontSize: '11px', padding: '0' }}
                              >
                                {showAllHotels 
                                  ? '收起酒店选项' 
                                  : `展开查看剩余 ${currentPlan.hotel.available_options.length - 6} 个酒店选项`
                                }
                              </Button>
                            </div>
                          </Col>
                        )}
                      </Row>
                    </Card>
                  )}
                </Card>
              </Col>
            </Row>
          </TabPane>
        </Tabs>
      )}

      {/* 导出模态框 */}
      <Modal
        title="导出方案"
        open={exportModalVisible}
        onCancel={() => setExportModalVisible(false)}
        footer={null}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Button 
            block 
            size="large"
            onClick={() => handleExport('pdf')}
          >
            导出为 PDF
          </Button>
          <Button 
            block 
            size="large"
            onClick={() => handleExport('html')}
          >
            导出为 HTML
          </Button>
          <Button 
            block 
            size="large"
            onClick={() => handleExport('json')}
          >
            导出为 JSON
          </Button>
        </Space>
      </Modal>
    </div>
  );
};

export default PlanDetailPage;