import React, { useEffect, useState } from 'react';
import { Card, Form, Input, Button, DatePicker, Select, Space, message, Typography, Spin } from 'antd';
import { useParams, useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';
import { authFetch } from '../../utils/auth';

const { Title } = Typography;
const { RangePicker } = DatePicker;

interface PlanDetail {
  id: number;
  title: string;
  description?: string;
  destination: string;
  start_date?: string;
  end_date?: string;
  duration_days?: number;
  status: string;
}

const statusOptions = [
  { value: 'draft', label: '草稿' },
  { value: 'generating', label: '生成中' },
  { value: 'completed', label: '已完成' },
  { value: 'failed', label: '失败' },
  { value: 'archived', label: '已归档' }
];

const PlanEditPage: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const planId = Number(id);
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [plan, setPlan] = useState<PlanDetail | null>(null);

  useEffect(() => {
    const fetchDetail = async () => {
      setLoading(true);
      try {
        if (!planId) throw new Error('缺少计划ID');
        const resp = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_DETAIL(planId)));
        if (!resp.ok) throw new Error(`获取计划详情失败 (${resp.status})`);
        const data = await resp.json();
        setPlan(data);
        form.setFieldsValue({
          title: data.title,
          description: data.description,
          destination: data.destination,
          dateRange: data.start_date && data.end_date ? [dayjs(data.start_date), dayjs(data.end_date)] : undefined,
          status: data.status,
        });
      } catch (e) {
        console.error('加载计划详情失败:', e);
        message.error('无法加载计划详情');
      } finally {
        setLoading(false);
      }
    };
    fetchDetail();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planId]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const body: any = {};
      if (typeof values.title === 'string') body.title = values.title.trim();
      if (typeof values.description === 'string') body.description = values.description.trim();
      if (typeof values.destination === 'string') body.destination = values.destination.trim();
      if (Array.isArray(values.dateRange) && values.dateRange.length === 2) {
        const [start, end] = values.dateRange;
        body.start_date = start.format('YYYY-MM-DD HH:mm:ss');
        body.end_date = end.format('YYYY-MM-DD HH:mm:ss');
        body.duration_days = end.diff(start, 'day') + 1;
      }
      if (typeof values.status === 'string') body.status = values.status;

      setSaving(true);
      const resp = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_DETAIL(planId)), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      if (!resp.ok) throw new Error(`更新计划失败 (${resp.status})`);
      message.success('保存成功');
      navigate(`/plan/${planId}`);
    } catch (e) {
      console.error('保存失败:', e);
      message.error('保存失败，请检查表单');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Title level={3} style={{ marginBottom: 0 }}>编辑旅行计划</Title>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '24px' }}>
              <Spin />
            </div>
          ) : (
            <Form form={form} layout="vertical">
              <Form.Item label="标题" name="title" rules={[{ required: true, message: '请输入标题' }]}> 
                <Input placeholder="计划标题" />
              </Form.Item>
              <Form.Item label="目的地" name="destination" rules={[{ required: true, message: '请输入目的地' }]}> 
                <Input placeholder="例如：北京" />
              </Form.Item>
              <Form.Item label="出行日期" name="dateRange"> 
                <RangePicker showTime />
              </Form.Item>
              <Form.Item label="状态" name="status"> 
                <Select options={statusOptions} placeholder="选择状态" allowClear />
              </Form.Item>
              <Form.Item label="描述" name="description"> 
                <Input.TextArea placeholder="计划描述" rows={4} />
              </Form.Item>

              <Space>
                <Button onClick={() => navigate(`/plan/${planId}`)}>取消</Button>
                <Button type="primary" loading={saving} onClick={handleSave}>保存</Button>
              </Space>
            </Form>
          )}
        </Space>
      </Card>
    </div>
  );
};

export default PlanEditPage;