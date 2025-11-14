import React, { useEffect, useState, useCallback } from 'react';
import { Card, Table, Tag, Typography, Space, Spin, Button, message, Grid } from 'antd';
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
  const [pagination, setPagination] = useState<{ current: number; pageSize: number; total: number }>({ current: 1, pageSize: 10, total: 0 });
  const screens = Grid.useBreakpoint();

  const fetchPlans = useCallback(async (page = 1, pageSize = pagination.pageSize) => {
    setLoading(true);
    try {
      const skip = (page - 1) * pageSize;
      const res = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLANS + `?skip=${skip}&limit=${pageSize}`));
      const data = await res.json();
      const list = Array.isArray(data?.plans) ? data.plans : [];
      const total = typeof data?.total === 'number' ? data.total : list.length;
      setPlans(list);
      setPagination(prev => ({ ...prev, current: page, pageSize, total }));
    } catch (e) {
      setPlans([]);
    } finally {
      setLoading(false);
    }
  }, [pagination.pageSize]);

  useEffect(() => {
    fetchPlans(1, pagination.pageSize);
  }, [fetchPlans, pagination.pageSize]);

  const handleDeletePlan = async (planId: number) => {
    if (!window.confirm(`确认删除计划 ${planId} ?`)) return;
    try {
      const response = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_DETAIL(planId)), {
        method: 'DELETE',
      });
      if (response.ok) {
        message.success('计划已删除');
        fetchPlans(pagination.current, pagination.pageSize);
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
        fetchPlans(pagination.current, pagination.pageSize);
      } else {
        const err = await res.json();
        message.error(err?.detail || '批量删除失败');
      }
    } catch (e) {
      message.error('请求失败');
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id' },
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '目的地', dataIndex: 'destination', key: 'destination', ellipsis: true, responsive: ['sm'] },
    { title: '开始/结束', key: 'dates', responsive: ['md'], render: (_: any, r: TravelPlan) => `${r.start_date} ~ ${r.end_date}` },
    { title: '天数', dataIndex: 'duration_days', key: 'duration_days', responsive: ['lg'] },
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
              pagination={{
                current: pagination.current,
                pageSize: pagination.pageSize,
                total: pagination.total,
                showSizeChanger: true,
                onChange: (page, pageSize) => {
                  fetchPlans(page, pageSize);
                  setSelectedIds([]);
                },
              }}
              size={screens.xs ? 'small' : 'middle'}
              scroll={{ x: 'max-content' }}
            />
          )}
        </Card>
      </Space>
    </div>
  );
};

export default HistoryAdminPage;
