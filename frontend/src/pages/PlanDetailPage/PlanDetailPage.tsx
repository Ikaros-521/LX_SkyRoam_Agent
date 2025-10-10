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
  Progress,
  Divider,
  Alert,
  Spin,
  Modal,
  Rate
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
  HeartOutlined
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';

const { Title, Paragraph, Text } = Typography;
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

  useEffect(() => {
    fetchPlanDetail();
  }, [id]);

  const fetchPlanDetail = async () => {
    try {
      const response = await fetch(`/api/v1/travel-plans/${id}`);
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
      const response = await fetch(`/api/v1/travel-plans/${id}/select-plan`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ plan_index: planIndex }),
      });

      if (response.ok) {
        setSelectedPlanIndex(planIndex);
        fetchPlanDetail(); // 刷新数据
      }
    } catch (error) {
      console.error('选择方案失败:', error);
    }
  };

  const handleExport = async (format: string) => {
    try {
      const response = await fetch(`/api/v1/travel-plans/${id}/export?format=${format}`);
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
                              <Col span={8}>
                                <Text type="secondary">餐饮</Text>
                                <br />
                                <Text>{day.meals?.map((m: any) => m.suggestion).join(', ')}</Text>
                              </Col>
                              <Col span={8}>
                                <Text type="secondary">交通</Text>
                                <br />
                                <Text>{day.transportation}</Text>
                              </Col>
                              <Col span={8}>
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

                  {/* 推荐餐厅 */}
                  <Card title="推荐餐厅" size="small">
                    <List
                      size="small"
                      dataSource={currentPlan.restaurants}
                      renderItem={(restaurant: any) => (
                        <List.Item>
                          <Space>
                            <Avatar size="small" icon={<HeartOutlined />} />
                            <div>
                              <Text strong>{restaurant.name}</Text>
                              <br />
                              <Text type="secondary">{restaurant.cuisine_type}</Text>
                            </div>
                            <Rate disabled defaultValue={restaurant.rating || 0} />
                          </Space>
                        </List.Item>
                      )}
                    />
                  </Card>

                  {/* 地图占位 */}
                  <Card title="目的地地图" size="small">
                    <div style={{ 
                      height: '200px', 
                      width: '100%',
                      background: '#f5f5f5',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderRadius: '6px'
                    }}>
                      <Text type="secondary">地图功能开发中...</Text>
                    </div>
                  </Card>
                </Space>
              </Col>
            </Row>
          </TabPane>

          <TabPane tab="详细信息" key="details">
            <Row gutter={[24, 24]}>
              <Col xs={24} md={12}>
                <Card title="航班信息" size="small">
                  {currentPlan.flight ? (
                    <Space direction="vertical" size="small">
                      <Text strong>{currentPlan.flight.airline}</Text>
                      <Text>{currentPlan.flight.flight_number}</Text>
                      <Text>出发: {currentPlan.flight.departure_time}</Text>
                      <Text>到达: {currentPlan.flight.arrival_time}</Text>
                      <Text>价格: ¥{currentPlan.flight.price}</Text>
                    </Space>
                  ) : (
                    <Text type="secondary">暂无航班信息</Text>
                  )}
                </Card>
              </Col>
              
              <Col xs={24} md={12}>
                <Card title="酒店信息" size="small">
                  {currentPlan.hotel ? (
                    <Space direction="vertical" size="small">
                      <Text strong>{currentPlan.hotel.name}</Text>
                      <Text>{currentPlan.hotel.address}</Text>
                      <Rate disabled defaultValue={currentPlan.hotel.rating || 0} />
                      <Text>每晚: ¥{currentPlan.hotel.price_per_night}</Text>
                    </Space>
                  ) : (
                    <Text type="secondary">暂无酒店信息</Text>
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