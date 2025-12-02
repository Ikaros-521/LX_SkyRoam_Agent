import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Card, Typography, Space, Tag, Button, Row, Col, Empty, Spin, Pagination, Input, Select, DatePicker, Rate, Tabs, Alert } from 'antd';
import { CalendarOutlined, EnvironmentOutlined, EyeOutlined, DeleteOutlined, EditOutlined, HistoryOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';
import { authFetch, getToken } from '../../utils/auth';

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
  is_public?: boolean;
}

type TabKey = 'my' | 'public';

const PlansLibraryPage: React.FC = () => {
  const navigate = useNavigate();
  const location = window.location; // 直接读取以避免引入额外 hook
  const token = getToken();
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    const checkAdmin = async () => {
      const token = getToken();
      if (!token) { setIsAdmin(false); return; }
      try {
        const res = await authFetch(buildApiUrl('/users/me'));
        if (res.ok) {
          const me = await res.json();
          setIsAdmin(me?.role === 'admin');
        }
      } catch (e) {
        setIsAdmin(false);
      }
    };
    checkAdmin();
  }, []);

  const [activeTab, setActiveTab] = useState<TabKey>(() => {
    try {
      const search = new URLSearchParams(location.search);
      const q = (search.get('tab') || (location.hash || '').replace('#', '')).toLowerCase();
      return q === 'public' ? 'public' : 'my';
    } catch {
      return 'my';
    }
  });

  // 我的计划状态
  const myLatestReq = useRef(0);
  const [myPlans, setMyPlans] = useState<TravelPlan[]>([]);
  const [myLoading, setMyLoading] = useState(true);
  const myPageSize = 6;
  const [myCurrentPage, setMyCurrentPage] = useState(1);
  const [myTotal, setMyTotal] = useState(0);
  const [myKeyword, setMyKeyword] = useState<string>('');
  const [myMinScore, setMyMinScore] = useState<number | undefined>();
  const [myDateRange, setMyDateRange] = useState<any[]>([]);

  // 公开计划状态
  const pubLatestReq = useRef(0);
  const [pubPlans, setPubPlans] = useState<TravelPlan[]>([]);
  const [pubLoading, setPubLoading] = useState(true);
  const pubPageSize = 6;
  const [pubCurrentPage, setPubCurrentPage] = useState(1);
  const [pubTotal, setPubTotal] = useState(0);
  const [pubKeyword, setPubKeyword] = useState<string>('');
  const [pubMinScore, setPubMinScore] = useState<number | undefined>();
  const [pubDateRange, setPubDateRange] = useState<any[]>([]);

  useEffect(() => {
    if (activeTab === 'my') fetchMyPlans();
    if (activeTab === 'public') fetchPublicPlans();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, myCurrentPage, myMinScore, myDateRange, pubCurrentPage, pubMinScore, pubDateRange]);
  
  // 注意：keyword 不在依赖中，只在用户点击搜索按钮时才会更新并触发搜索

  const toDateStr = (d: any): string => {
    if (!d) return '';
    try {
      const dj = (typeof d.isValid === 'function') ? d : dayjs(d);
      if (!dj.isValid()) return '';
      return dj.format('YYYY-MM-DD');
    } catch { return ''; }
  };

  const fetchMyPlans = async (keywordOverride?: string) => {
    const reqId = ++myLatestReq.current;
    try {
      setMyLoading(true);
      if (!token) {
        setMyPlans([]);
        setMyTotal(0);
        return;
      }
      const params = new URLSearchParams();
      params.set('skip', String((myCurrentPage - 1) * myPageSize));
      params.set('limit', String(myPageSize));
      // 优先使用传入的 keyword，否则使用状态中的 keyword
      const keywordToUse = keywordOverride !== undefined ? keywordOverride : myKeyword;
      if (keywordToUse && keywordToUse.trim()) params.set('keyword', keywordToUse.trim());
      if (typeof myMinScore === 'number') params.set('min_score', String(myMinScore));
      if (myDateRange && myDateRange.length === 2 && myDateRange[0] && myDateRange[1]) {
        const fromStr = toDateStr(myDateRange[0]);
        const toStr = toDateStr(myDateRange[1]);
        if (fromStr) params.set('travel_from', fromStr);
        if (toStr) params.set('travel_to', toStr);
      }
      const response = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLANS + `?${params.toString()}`));
      if (!response.ok) throw new Error('获取我的计划失败');
      const data = await response.json();
      if (reqId !== myLatestReq.current) return;
      const list = Array.isArray(data?.plans) ? data.plans : (Array.isArray(data) ? data : []);
      const totalCount = typeof data?.total === 'number' ? data.total : (Array.isArray(data) ? data.length : 0);
      setMyPlans(list);
      setMyTotal(totalCount);
    } catch (e) {
      if (reqId !== myLatestReq.current) return;
      setMyPlans([]);
      setMyTotal(0);
    } finally {
      if (reqId === myLatestReq.current) setMyLoading(false);
    }
  };

  const fetchPublicPlans = async (keywordOverride?: string) => {
    const reqId = ++pubLatestReq.current;
    try {
      setPubLoading(true);
      const params = new URLSearchParams();
      params.set('skip', String((pubCurrentPage - 1) * pubPageSize));
      params.set('limit', String(pubPageSize));
      // 优先使用传入的 keyword，否则使用状态中的 keyword
      const keywordToUse = keywordOverride !== undefined ? keywordOverride : pubKeyword;
      if (keywordToUse && keywordToUse.trim()) params.set('keyword', keywordToUse.trim());
      if (typeof pubMinScore === 'number') params.set('min_score', String(pubMinScore));
      if (pubDateRange && pubDateRange.length === 2 && pubDateRange[0] && pubDateRange[1]) {
        const fromStr = toDateStr(pubDateRange[0]);
        const toStr = toDateStr(pubDateRange[1]);
        if (fromStr) params.set('travel_from', fromStr);
        if (toStr) params.set('travel_to', toStr);
      }
      const response = await fetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLANS_PUBLIC + `?${params.toString()}`));
      if (!response.ok) throw new Error('获取公开计划失败');
      const data = await response.json();
      if (reqId !== pubLatestReq.current) return;
      const list = Array.isArray(data?.plans) ? data.plans : (Array.isArray(data) ? data : []);
      const totalCount = typeof data?.total === 'number' ? data.total : (Array.isArray(data) ? data.length : 0);
      setPubPlans(list);
      setPubTotal(totalCount);
    } catch (e) {
      if (reqId !== pubLatestReq.current) return;
      setPubPlans([]);
      setPubTotal(0);
    } finally {
      if (reqId === pubLatestReq.current) setPubLoading(false);
    }
  };

  const getStatusTag = (status: string) => {
    const statusMap = {
      draft: { color: 'default', text: '草稿' },
      generating: { color: 'processing', text: '生成中' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' },
      archived: { color: 'default', text: '已归档' }
    } as Record<string, { color: string; text: string }>;
    const config = statusMap[status] || { color: 'default', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const renderCard = (plan: TravelPlan, tab: TabKey) => (
    <Card
      className="travel-card glass-card"
      hoverable
      actions={[
        <Button type="text" icon={<EyeOutlined />} onClick={() => navigate(`/plan/${plan.id}`)}>查看</Button>,
        ...(tab === 'my' ? [
          (isAdmin ? <Button type="text" icon={<EditOutlined />} onClick={() => navigate(`/plan/${plan.id}/edit`)}>编辑</Button> : null),
          <Button type="text" danger icon={<DeleteOutlined />} onClick={() => handleDeletePlan(plan.id)}>删除</Button>
        ].filter(Boolean) as any : [])
      ]}
    >
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Title level={4} style={{ margin: 0, flex: 1 }}>{plan.title}</Title>
          <Space>
            <Tag color="purple">ID: {plan.id}</Tag>
            {plan.is_public && <Tag color="cyan">公开</Tag>}
          </Space>
        </div>
        <Space>
          <Tag color="blue" icon={<EnvironmentOutlined />}>{plan.destination}</Tag>
          <Tag color="green" icon={<CalendarOutlined />}>{plan.duration_days} 天</Tag>
        </Space>
        <div>
          <Text type="secondary">{new Date(plan.start_date).toLocaleDateString('zh-CN')} - {new Date(plan.end_date).toLocaleDateString('zh-CN')}</Text>
        </div>
        <div>
          <Space>
            {getStatusTag(plan.status)}
            {typeof plan.score === 'number' && (
              <>
                <Tag color="orange">评分: {plan.score.toFixed(1)}</Tag>
                <Rate disabled allowHalf value={plan.score} style={{ fontSize: 14 }} />
              </>
            )}
          </Space>
        </div>
        <div>
          <Text type="secondary" style={{ fontSize: '12px' }}>创建时间: {new Date(plan.created_at).toLocaleString('zh-CN')}</Text>
        </div>
      </Space>
    </Card>
  );

  const handleDeletePlan = async (planId: number) => {
    try {
      const response = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_DETAIL(planId)), { method: 'DELETE' });
      if (response.ok) fetchMyPlans();
    } catch (e) {
      // 忽略错误
    }
  };

  const FilterBar = React.memo((props: {
    keyword: string; setKeyword: (v: string) => void;
    minScore?: number; setMinScore: (v: number | undefined) => void;
    dateRange: any[]; setDateRange: (v: any[]) => void;
    onReset: () => void;
    onSearch: (keyword: string) => void;
  }) => {
    const { setKeyword, setMinScore, setDateRange, onReset, onSearch } = props;
    
    // 完全独立的本地输入状态，不依赖外部 keyword
    const [localInput, setLocalInput] = useState('');
    
    const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
      setLocalInput(e.target.value);
    }, []);

    const handleSearch = useCallback((value: string) => {
      // 使用 onSearch 传入的值，而不是 localInput（避免闭包问题）
      const t = (value || localInput).trim();
      setKeyword(t);
      setLocalInput(t);
      // 手动触发搜索，直接传递最新的 keyword 值，避免状态更新延迟问题
      onSearch(t);
    }, [localInput, setKeyword, onSearch]);

    const handleScoreChange = useCallback((v: number | undefined) => {
      setMinScore(v);
    }, [setMinScore]);

    const handleDateRangeChange = useCallback((range: any) => {
      setDateRange(range || []);
    }, [setDateRange]);

    const handleReset = useCallback(() => {
      setLocalInput('');
      onReset();
    }, [onReset]);

    return (
      <Card style={{ marginBottom: 16 }}>
        <Space wrap size="middle">
          <Input.Search
            placeholder="关键词（标题/目的地/描述）"
            allowClear
            style={{ width: 280 }}
            value={localInput}
            onChange={handleSearchChange}
            onSearch={handleSearch}
            enterButton
          />
          <Select
            placeholder="评分"
            allowClear
            style={{ width: 160 }}
            value={props.minScore}
            onChange={handleScoreChange}
            options={[
              { value: 1, label: '1星及以上' },
              { value: 2, label: '2星及以上' },
              { value: 3, label: '3星及以上' },
              { value: 4, label: '4星及以上' },
              { value: 5, label: '5星' },
            ]}
          />
          <DatePicker.RangePicker
            value={props.dateRange as any}
            onChange={handleDateRangeChange}
          />
          <Button onClick={handleReset}>重置</Button>
        </Space>
      </Card>
    );
  });

  const myResetHandler = useCallback(() => {
    setMyKeyword('');
    setMyMinScore(undefined);
    setMyDateRange([]);
    setMyCurrentPage(1);
  }, []);

  const pubResetHandler = useCallback(() => {
    setPubKeyword('');
    setPubMinScore(undefined);
    setPubDateRange([]);
    setPubCurrentPage(1);
  }, []);

  const renderTabContent = (tab: TabKey) => {
    const list = tab === 'my' ? myPlans : pubPlans;
    const loading = tab === 'my' ? myLoading : pubLoading;
    const total = tab === 'my' ? myTotal : pubTotal;
    const currentPage = tab === 'my' ? myCurrentPage : pubCurrentPage;
    const setPage = tab === 'my' ? setMyCurrentPage : setPubCurrentPage;
    // FilterBar 内部管理输入状态，所以这里创建新对象不会导致重新渲染
    const filterProps = tab === 'my' ? {
      keyword: myKeyword, setKeyword: setMyKeyword,
      minScore: myMinScore, setMinScore: setMyMinScore,
      dateRange: myDateRange, setDateRange: setMyDateRange,
      onReset: myResetHandler,
      onSearch: (keyword: string) => fetchMyPlans(keyword)
    } : {
      keyword: pubKeyword, setKeyword: setPubKeyword,
      minScore: pubMinScore, setMinScore: setPubMinScore,
      dateRange: pubDateRange, setDateRange: setPubDateRange,
      onReset: pubResetHandler,
      onSearch: (keyword: string) => fetchPublicPlans(keyword)
    };

    if (tab === 'my' && !token) {
      return (
        <Card>
          <Empty description="请先登录以查看我的计划">
            <Button type="primary" onClick={() => navigate('/login')}>去登录</Button>
          </Empty>
        </Card>
      );
    }

    return (
      <>
        <FilterBar {...filterProps} />
        {loading ? (
          <div style={{ textAlign: 'center', padding: 50 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}><Text>加载中...</Text></div>
          </div>
        ) : list.length === 0 ? (
          <Card>
            <Empty description={tab === 'my' ? '还没有旅行计划' : '暂无公开计划'} image={Empty.PRESENTED_IMAGE_SIMPLE}>
              {tab === 'my' && (
                <Button type="primary" onClick={() => navigate('/plan')}>创建第一个计划</Button>
              )}
            </Empty>
          </Card>
        ) : (
          <>
            <Row gutter={[16, 16]}>
              {list.map((plan) => (
                <Col xs={24} sm={12} lg={8} key={plan.id}>
                  {renderCard(plan, tab)}
                </Col>
              ))}
            </Row>
            <div style={{ textAlign: 'center', marginTop: 24 }}>
              <Pagination current={currentPage} total={total} pageSize={tab === 'my' ? myPageSize : pubPageSize} onChange={setPage} showSizeChanger={false} showQuickJumper showTotal={(t, r) => `第 ${r[0]}-${r[1]} 条，共 ${t} 条`} />
            </div>
          </>
        )}
      </>
    );
  };

  return (
    <div className="plans-library-page" style={{ maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>
          <HistoryOutlined style={{ marginRight: 8 }} />
          计划库
        </Title>
        <Paragraph style={{ color: '#666' }}>浏览公开方案和管理我的方案</Paragraph>
        <Alert type="info" showIcon message="公开计划为只读视图；若无法查看详情将自动回退公开接口" style={{ marginTop: 8 }} />
      </div>
      <Tabs activeKey={activeTab} onChange={(k) => setActiveTab(k as TabKey)} items={[
        { key: 'my', label: '我的计划', children: renderTabContent('my') },
        { key: 'public', label: '公开计划', children: renderTabContent('public') },
      ]} />
    </div>
  );
};

export default PlansLibraryPage;