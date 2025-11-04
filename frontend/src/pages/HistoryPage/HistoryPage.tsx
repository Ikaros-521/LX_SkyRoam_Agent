import React, { useState, useEffect } from 'react';
import { 
  Card, 
  List, 
  Typography, 
  Space,
  Tag,
  Button,
  Row,
  Col,
  Empty,
  Spin,
  Pagination
} from 'antd';
import { 
  CalendarOutlined, 
  EnvironmentOutlined,
  EyeOutlined,
  DeleteOutlined,
  EditOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';
import { authFetch } from '../../utils/auth';

const { Title, Paragraph, Text } = Typography;

interface TravelPlan {
  id: number;
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  duration_days: number;
  status: string;
  score: number;
  created_at: string;
}

const HistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [plans, setPlans] = useState<TravelPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 6;

  useEffect(() => {
    fetchPlans();
  }, [currentPage]);

  const fetchPlans = async () => {
    try {
      setLoading(true);
      const response = await authFetch(
        buildApiUrl(`/travel-plans/?skip=${(currentPage - 1) * pageSize}&limit=${pageSize}`)
      );
      
      if (!response.ok) {
        throw new Error('获取历史记录失败');
      }
      
      const data = await response.json();
      setPlans(data.plans || data); // 兼容新旧格式
      setTotal(data.total || data.length); // 使用API返回的总数
    } catch (error) {
      console.error('获取历史记录失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleViewPlan = (planId: number) => {
    navigate(`/plan/${planId}`);
  };

  const handleEditPlan = (planId: number) => {
    navigate(`/plan?edit=${planId}`);
  };

  const handleDeletePlan = async (planId: number) => {
    try {
      const response = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_DETAIL(planId)), {
        method: 'DELETE',
      });

      if (response.ok) {
        fetchPlans(); // 刷新列表
      }
    } catch (error) {
      console.error('删除计划失败:', error);
    }
  };

  const getStatusTag = (status: string) => {
    const statusMap = {
      draft: { color: 'default', text: '草稿' },
      generating: { color: 'processing', text: '生成中' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' },
      archived: { color: 'default', text: '已归档' }
    };
    
    const config = statusMap[status as keyof typeof statusMap] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN');
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
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

  return (
    <div className="history-page" style={{ maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ marginBottom: '24px' }}>
        <Title level={2}>我的旅行计划</Title>
        <Paragraph style={{ color: '#666' }}>
          查看和管理您的所有旅行计划
        </Paragraph>
      </div>

      {plans.length === 0 ? (
        <Card>
          <Empty
            description="还没有旅行计划"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button 
              type="primary" 
              onClick={() => navigate('/plan')}
            >
              创建第一个计划
            </Button>
          </Empty>
        </Card>
      ) : (
        <>
          <Row gutter={[16, 16]}>
            {plans.map((plan) => (
              <Col xs={24} sm={12} lg={8} key={plan.id}>
                <Card
                  className="travel-card"
                  hoverable
                  actions={[
                    <Button 
                      type="text" 
                      icon={<EyeOutlined />}
                      onClick={() => handleViewPlan(plan.id)}
                    >
                      查看
                    </Button>,
                    <Button 
                      type="text" 
                      icon={<EditOutlined />}
                      onClick={() => handleEditPlan(plan.id)}
                    >
                      编辑
                    </Button>,
                    <Button 
                      type="text" 
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() => handleDeletePlan(plan.id)}
                    >
                      删除
                    </Button>
                  ]}
                >
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <Title level={4} style={{ margin: 0, flex: 1 }}>
                        {plan.title}
                      </Title>
                      <Tag color="purple" style={{ marginLeft: '8px' }}>
                        ID: {plan.id}
                      </Tag>
                    </div>
                    
                    <Space>
                      <Tag color="blue" icon={<EnvironmentOutlined />}>
                        {plan.destination}
                      </Tag>
                      <Tag color="green" icon={<CalendarOutlined />}>
                        {plan.duration_days} 天
                      </Tag>
                    </Space>
                    
                    <div>
                      <Text type="secondary">
                        {formatDate(plan.start_date)} - {formatDate(plan.end_date)}
                      </Text>
                    </div>
                    
                    <div>
                      {getStatusTag(plan.status)}
                      {plan.score && (
                        <Tag color="orange">
                          评分: {plan.score.toFixed(1)}
                        </Tag>
                      )}
                    </div>
                    
                    <div>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        创建时间: {formatDateTime(plan.created_at)}
                      </Text>
                    </div>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>

          <div style={{ textAlign: 'center', marginTop: '24px' }}>
            <Pagination
              current={currentPage}
              total={total}
              pageSize={pageSize}
              onChange={setCurrentPage}
              showSizeChanger={false}
              showQuickJumper
              showTotal={(total, range) => 
                `第 ${range[0]}-${range[1]} 条，共 ${total} 条`
              }
            />
          </div>
        </>
      )}
    </div>
  );
};

export default HistoryPage;
