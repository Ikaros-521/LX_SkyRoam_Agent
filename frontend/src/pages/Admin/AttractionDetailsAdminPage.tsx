import React, { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Tag,
  Typography,
  Space,
  Spin,
  Button,
  message,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Row,
  Col,
  Popconfirm,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined } from '@ant-design/icons';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';
import { authFetch } from '../../utils/auth';

const { Title } = Typography;
const { TextArea } = Input;

interface AttractionDetailItem {
  id: number;
  name: string;
  destination: string;
  city?: string;
  phone?: string;
  website?: string;
  email?: string;
  wechat?: string;
  ticket_price?: number;
  ticket_price_child?: number;
  ticket_price_student?: number;
  currency: string;
  price_note?: string;
  opening_hours?: any;
  opening_hours_text?: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  image_url?: string;
  extra_info?: any;
  match_priority: number;
  verified: string;
}

const AttractionDetailsAdminPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<AttractionDetailItem[]>([]);
  const [total, setTotal] = useState(0);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  const [destinations, setDestinations] = useState<string[]>([]);
  const [cities, setCities] = useState<string[]>([]);
  
  // 搜索和筛选
  const [searchText, setSearchText] = useState('');
  const [filterDestination, setFilterDestination] = useState<string | undefined>();
  const [filterCity, setFilterCity] = useState<string | undefined>();
  
  // 编辑/创建 Modal
  const [modalVisible, setModalVisible] = useState(false);
  const [editingItem, setEditingItem] = useState<AttractionDetailItem | null>(null);
  const [form] = Form.useForm();

  // 加载列表数据
  const fetchItems = async (skip = 0, limit = 10) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        skip: skip.toString(),
        limit: limit.toString(),
      });
      if (searchText) params.append('search', searchText);
      if (filterDestination) params.append('destination', filterDestination);
      if (filterCity) params.append('city', filterCity);

      const res = await authFetch(
        buildApiUrl(`${API_ENDPOINTS.ATTRACTION_DETAILS}?${params.toString()}`)
      );
      const data = await res.json();
      if (res.ok) {
        setItems(data.items || []);
        setTotal(data.total || 0);
      } else {
        message.error(data.detail || '加载失败');
      }
    } catch (e) {
      message.error('请求失败');
    } finally {
      setLoading(false);
    }
  };

  // 加载目的地和城市列表
  const fetchDestinations = async () => {
    try {
      const res = await authFetch(buildApiUrl(API_ENDPOINTS.ATTRACTION_DETAILS_DESTINATIONS));
      const data = await res.json();
      if (res.ok) {
        setDestinations(data || []);
      }
    } catch (e) {
      console.error('加载目的地列表失败', e);
    }
  };

  const fetchCities = async () => {
    try {
      const params = filterDestination ? `?destination=${filterDestination}` : '';
      const res = await authFetch(buildApiUrl(`${API_ENDPOINTS.ATTRACTION_DETAILS_CITIES}${params}`));
      const data = await res.json();
      if (res.ok) {
        setCities(data || []);
      }
    } catch (e) {
      console.error('加载城市列表失败', e);
    }
  };

  useEffect(() => {
    fetchDestinations();
  }, []);

  useEffect(() => {
    fetchCities();
  }, [filterDestination]);

  useEffect(() => {
    const skip = (pagination.current - 1) * pagination.pageSize;
    fetchItems(skip, pagination.pageSize);
  }, [pagination, searchText, filterDestination, filterCity]);

  const handleCreate = () => {
    setEditingItem(null);
    form.resetFields();
    form.setFieldsValue({
      currency: 'CNY',
      match_priority: 100,
      verified: 'pending',
    });
    setModalVisible(true);
  };

  const handleEdit = (item: AttractionDetailItem) => {
    setEditingItem(item);
    form.setFieldsValue({
      ...item,
      opening_hours: item.opening_hours ? JSON.stringify(item.opening_hours, null, 2) : '',
      extra_info: item.extra_info ? JSON.stringify(item.extra_info, null, 2) : '',
    });
    setModalVisible(true);
  };

  const handleDelete = async (id: number) => {
    try {
      const res = await authFetch(buildApiUrl(API_ENDPOINTS.ATTRACTION_DETAIL(id)), {
        method: 'DELETE',
      });
      if (res.ok) {
        message.success('删除成功');
        fetchItems((pagination.current - 1) * pagination.pageSize, pagination.pageSize);
      } else {
        const err = await res.json();
        message.error(err?.detail || '删除失败');
      }
    } catch (e) {
      message.error('请求失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      // 处理 JSON 字段
      if (values.opening_hours) {
        try {
          values.opening_hours = JSON.parse(values.opening_hours);
        } catch (e) {
          message.error('营业时间格式错误，请输入有效的 JSON');
          return;
        }
      }
      if (values.extra_info) {
        try {
          values.extra_info = JSON.parse(values.extra_info);
        } catch (e) {
          message.error('额外信息格式错误，请输入有效的 JSON');
          return;
        }
      }

      const url = editingItem
        ? buildApiUrl(API_ENDPOINTS.ATTRACTION_DETAIL(editingItem.id))
        : buildApiUrl(API_ENDPOINTS.ATTRACTION_DETAILS);
      
      const method = editingItem ? 'PUT' : 'POST';
      
      const res = await authFetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });

      if (res.ok) {
        message.success(editingItem ? '更新成功' : '创建成功');
        setModalVisible(false);
        setEditingItem(null);
        fetchItems((pagination.current - 1) * pagination.pageSize, pagination.pageSize);
      } else {
        const err = await res.json();
        message.error(err?.detail || '操作失败');
      }
    } catch (e: any) {
      if (e?.errorFields) return; // 表单验证错误
      message.error('请求失败');
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: '景点名称', dataIndex: 'name', key: 'name', width: 150 },
    { title: '目的地', dataIndex: 'destination', key: 'destination', width: 120 },
    { title: '城市', dataIndex: 'city', key: 'city', width: 100 },
    {
      title: '成人票价',
      key: 'ticket_price',
      width: 100,
      render: (_: any, record: AttractionDetailItem) =>
        record.ticket_price ? `${record.currency} ${record.ticket_price}` : '-',
    },
    { title: '联系电话', dataIndex: 'phone', key: 'phone', width: 120 },
    {
      title: '状态',
      dataIndex: 'verified',
      key: 'verified',
      width: 100,
      render: (v: string) => {
        const colors: Record<string, string> = {
          verified: 'green',
          pending: 'orange',
          outdated: 'red',
        };
        const texts: Record<string, string> = {
          verified: '已核实',
          pending: '待核实',
          outdated: '已过期',
        };
        return <Tag color={colors[v] || 'default'}>{texts[v] || v}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right' as const,
      render: (_: any, record: AttractionDetailItem) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
            size="small"
          >
            编辑
          </Button>
          <Popconfirm
            title={`确认删除景点 "${record.name}" 的详细信息？`}
            onConfirm={() => handleDelete(record.id)}
          >
            <Button type="link" danger icon={<DeleteOutlined />} size="small">
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto', padding: '20px' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={2}>景点详细信息管理</Title>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新增景点信息
          </Button>
        </div>

        <Card>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            {/* 搜索和筛选 */}
            <Row gutter={16}>
              <Col span={8}>
                <Input
                  placeholder="搜索景点名称、地址、电话"
                  prefix={<SearchOutlined />}
                  value={searchText}
                  onChange={(e) => {
                    setSearchText(e.target.value);
                    setPagination({ ...pagination, current: 1 });
                  }}
                  allowClear
                />
              </Col>
              <Col span={6}>
                <Select
                  placeholder="筛选目的地"
                  style={{ width: '100%' }}
                  value={filterDestination}
                  onChange={(v) => {
                    setFilterDestination(v);
                    setFilterCity(undefined);
                    setPagination({ ...pagination, current: 1 });
                  }}
                  allowClear
                >
                  {destinations.map((d) => (
                    <Select.Option key={d} value={d}>
                      {d}
                    </Select.Option>
                  ))}
                </Select>
              </Col>
              <Col span={6}>
                <Select
                  placeholder="筛选城市"
                  style={{ width: '100%' }}
                  value={filterCity}
                  onChange={(v) => {
                    setFilterCity(v);
                    setPagination({ ...pagination, current: 1 });
                  }}
                  allowClear
                  disabled={!filterDestination}
                >
                  {cities.map((c) => (
                    <Select.Option key={c} value={c}>
                      {c}
                    </Select.Option>
                  ))}
                </Select>
              </Col>
            </Row>

            {/* 数据表格 */}
            {loading ? (
              <div style={{ textAlign: 'center', padding: 32 }}>
                <Spin />
              </div>
            ) : (
              <Table
                rowKey="id"
                columns={columns as any}
                dataSource={items}
                scroll={{ x: 1200 }}
                pagination={{
                  current: pagination.current,
                  pageSize: pagination.pageSize,
                  total: total,
                  showTotal: (total) => `共 ${total} 条`,
                  onChange: (page, pageSize) => {
                    setPagination({ current: page, pageSize });
                  },
                }}
              />
            )}
          </Space>
        </Card>
      </Space>

      {/* 创建/编辑 Modal */}
      <Modal
        title={editingItem ? '编辑景点信息' : '新增景点信息'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          setEditingItem(null);
          form.resetFields();
        }}
        okText="保存"
        cancelText="取消"
        width={800}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="景点名称"
                rules={[{ required: true, message: '请输入景点名称' }]}
              >
                <Input placeholder="例如：故宫博物院" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="destination"
                label="目的地"
                rules={[{ required: true, message: '请输入目的地' }]}
              >
                <Input placeholder="例如：北京" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="city" label="城市">
                <Input placeholder="例如：北京市" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="match_priority" label="匹配优先级">
                <InputNumber min={0} max={1000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="address" label="详细地址">
            <Input placeholder="例如：北京市东城区景山前街4号" />
          </Form.Item>

          <Form.Item name="image_url" label="图片链接">
            <Input placeholder="例如：https://example.com/image.jpg" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="latitude" label="纬度">
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="例如：39.9163"
                  precision={6}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="longitude" label="经度">
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="例如：116.3972"
                  precision={6}
                />
              </Form.Item>
            </Col>
          </Row>

          <Title level={5}>联系方式</Title>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="phone" label="联系电话">
                <Input placeholder="例如：010-85007421" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="website" label="官网">
                <Input placeholder="例如：https://www.dpm.org.cn" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="email" label="邮箱">
                <Input type="email" placeholder="例如：info@example.com" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="wechat" label="微信号/公众号">
                <Input placeholder="例如：故宫博物院" />
              </Form.Item>
            </Col>
          </Row>

          <Title level={5}>价格信息</Title>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="ticket_price" label="成人票价">
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="例如：60"
                  min={0}
                  precision={2}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="ticket_price_child" label="儿童票价">
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="例如：30"
                  min={0}
                  precision={2}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="ticket_price_student" label="学生票价">
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="例如：30"
                  min={0}
                  precision={2}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="currency" label="货币单位">
                <Select>
                  <Select.Option value="CNY">CNY（人民币）</Select.Option>
                  <Select.Option value="USD">USD（美元）</Select.Option>
                  <Select.Option value="EUR">EUR（欧元）</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="verified" label="验证状态">
                <Select>
                  <Select.Option value="pending">待核实</Select.Option>
                  <Select.Option value="verified">已核实</Select.Option>
                  <Select.Option value="outdated">已过期</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="price_note"
            label="价格说明"
            tooltip="例如：旺季(7-8月)门票120元，淡季80元；学生需持学生证；60岁以上老人免费"
          >
            <TextArea
              rows={3}
              placeholder="例如：旺季(7-8月)门票120元，淡季80元；学生需持学生证"
            />
          </Form.Item>

          <Title level={5}>营业时间</Title>
          <Form.Item
            name="opening_hours_text"
            label="营业时间（文本）"
            tooltip="便于阅读的文本描述"
          >
            <TextArea
              rows={2}
              placeholder="例如：周一至周日 08:30-17:00（16:00停止入馆）"
            />
          </Form.Item>

          <Form.Item
            name="opening_hours"
            label="营业时间（JSON）"
            tooltip='JSON格式，例如：{"周一":"08:00-18:00","节假日":"08:00-20:00"}'
          >
            <TextArea
              rows={4}
              placeholder='{"周一":"08:00-18:00","周二":"08:00-18:00","节假日":"08:00-20:00"}'
            />
          </Form.Item>

          <Title level={5}>其他信息（JSON格式）</Title>
          <Form.Item
            name="extra_info"
            label="额外信息"
            tooltip='JSON格式，可存储推荐游览时长、最佳时间、提示、设施等信息'
          >
            <TextArea
              rows={6}
              placeholder='{"recommended_duration":"2-3小时","best_visit_time":"春季和秋季","tips":["建议提前预约"],"facilities":["停车场","餐厅"]}'
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AttractionDetailsAdminPage;

