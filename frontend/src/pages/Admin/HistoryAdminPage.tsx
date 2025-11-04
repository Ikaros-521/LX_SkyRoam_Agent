import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Typography, Space, Spin, Button, message } from 'antd';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';
import { authFetch } from '../../utils/auth';
import { useNavigate } from 'react-router-dom';

const { Title } = Typography;

interface TravelPlan {
  id: number;
  user_id: number;
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  duration_days: number;
  status: string;
  score?: number;
  created_at: string;
}

const HistoryAdminPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [plans, setPlans] = useState<TravelPlan[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  const fetchPlans = async () => {
    setLoading(true);
    try {
      const res = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLANS + '?skip=0&limit=50'));
      const data = await res.json();
      const list = Array.isArray(data?.plans) ? data.plans : [];
      setPlans(list);
    } catch (e) {
      setPlans([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlans();
  }, []);

  const handleDeletePlan = async (planId: number) => {
    if (!window.confirm(`确认删除计划 ${planId} ?`)) return;
    try {
      const response = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_DETAIL(planId)), {
        method: 'DELETE',
      });
      if (response.ok) {
        message.success('计划已删除');
        fetchPlans();
      } else {
        const err = await response.json();
        message.error(err?.detail || '删除失败');
      }
    } catch (error) {
      message.error('请求失败');
    }
  };

  const handleBatchDelete = async () => {
    if (selectedIds.length === 0) {
      message.warning('请先选择要删除的计划');
      return;
    }
    if (!window.confirm(`确认批量删除 ${selectedIds.length} 条计划？`)) return;
    try {
      const res = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLANS_BATCH_DELETE), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: selectedIds }),
      });
      if (res.ok) {
        const data = await res.json();
        message.success(`已删除 ${data?.deleted || 0} 条计划`);
        setSelectedIds([]);
        fetchPlans();
      } else {
        const err = await res.json();
        message.error(err?.detail || '批量删除失败');
      }
    } catch (e) {
      message.error('请求失败');
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: '用户ID', dataIndex: 'user_id', key: 'user_id', width: 100 },
    { title: '标题', dataIndex: 'title', key: 'title' },
    { title: '目的地', dataIndex: 'destination', key: 'destination', width: 140 },
    { title: '开始', dataIndex: 'start_date', key: 'start_date', width: 180 },
    { title: '结束', dataIndex: 'end_date', key: 'end_date', width: 180 },
    { title: '天数', dataIndex: 'duration_days', key: 'duration_days', width: 80 },
    { 
      title: '状态', 
      dataIndex: 'status', 
      key: 'status',
      render: (status: string) => {
        const color = status === 'completed' ? 'green' : status === 'generating' ? 'blue' : 'default';
        return <Tag color={color}>{status}</Tag>;
      }
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: TravelPlan) => (
        <Space>
          <Button type="link" onClick={() => navigate(`/plan/${record.id}`)}>查看</Button>
          <Button type="link" danger onClick={() => handleDeletePlan(record.id)}>删除</Button>
        </Space>
      )
    }
  ];

  const rowSelection = {
    selectedRowKeys: selectedIds,
    onChange: (keys: React.Key[]) => setSelectedIds(keys as number[]),
  };

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={2}>历史记录管理</Title>
          <Button danger onClick={handleBatchDelete}>删除所选</Button>
        </div>
        <Card>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 32 }}>
              <Spin />
            </div>
          ) : (
            <Table
              rowKey="id"
              columns={columns as any}
              dataSource={plans}
              rowSelection={rowSelection}
              pagination={{ pageSize: 10 }}
            />
          )}
        </Card>
      </Space>
    </div>
  );
};

export default HistoryAdminPage;