import React, { useEffect, useMemo, useState } from 'react';
import { Card, Row, Col, Typography, Input, Space, Tag, Image, Modal, List, Button, Spin, Empty, Carousel, Select, DatePicker } from 'antd';
import { GlobalOutlined, SearchOutlined, EnvironmentOutlined, CalendarOutlined, DollarOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';
import { authFetch } from '../../utils/auth';

const { Title, Paragraph, Text } = Typography;

interface Destination {
  id: number;
  name: string;
  country: string;
  city?: string;
  region?: string;
  latitude?: number;
  longitude?: number;
  timezone?: string;
  description?: string;
  highlights?: string[];
  best_time_to_visit?: string;
  popularity_score?: number;
  cost_level?: string; // low, medium, high
  images?: string[];
  continent?: string; // 新增：洲别（亚洲、欧洲、美洲、大洋洲、非洲）
}

interface TravelPlan {
  id: number;
  title: string;
  description?: string;
  destination: string;
  start_date: string;
  end_date: string;
  duration_days: number;
  budget?: number;
  status: string;
  score?: number;
  is_public?: boolean;
}

// 默认热门目的地数据（当后台无数据或加载失败时展示）
const DEFAULT_DESTINATIONS: Destination[] = [
  { id: 1, name: '北京', country: '中国', city: '北京', region: '华北', continent: '亚洲', best_time_to_visit: '4-6月、9-10月', cost_level: '中', popularity_score: 95, description: '历史与现代交织的城市，故宫与长城闻名于世。', highlights: ['天安门广场', '故宫', '八达岭长城', '颐和园', '南锣鼓巷'], images: ['https://picsum.photos/seed/beijing/800/600'] },
  { id: 2, name: '上海', country: '中国', city: '上海', region: '华东', continent: '亚洲', best_time_to_visit: '3-5月、9-11月', cost_level: '中-高', popularity_score: 92, description: '国际化都市，外滩与东方明珠地标林立。', highlights: ['外滩', '东方明珠', '城隍庙', '田子坊', '迪士尼'], images: ['https://picsum.photos/seed/shanghai/800/600'] },
  { id: 3, name: '杭州', country: '中国', city: '杭州', region: '华东', continent: '亚洲', best_time_to_visit: '3-5月、9-11月', cost_level: '中', popularity_score: 90, description: '江南名城，西湖十景与人文古迹相映成趣。', highlights: ['西湖', '灵隐寺', '雷峰塔', '宋城', '千岛湖'], images: ['https://picsum.photos/seed/hangzhou/800/600'] },
  { id: 4, name: '香港', country: '中国', city: '香港', region: '华南', continent: '亚洲', best_time_to_visit: '10-12月、3-5月', cost_level: '高', popularity_score: 90, description: '亚洲金融中心，美食购物与夜景皆精彩。', highlights: ['维多利亚港', '太平山顶', '旺角', '迪士尼', '海洋公园'], images: ['https://picsum.photos/seed/hongkong/800/600'] },
  { id: 5, name: '东京', country: '日本', city: '东京', region: '关东', continent: '亚洲', best_time_to_visit: '3-4月樱花季、10-11月红叶季', cost_level: '中-高', popularity_score: 94, description: '传统与科技并存，街区文化与美食丰富。', highlights: ['浅草寺', '秋叶原', '涩谷', '东京塔', '上野公园'], images: ['https://kimi-web-img.moonshot.cn/img/cdn.visualwilderness.com/f67ffa1d10aae2e8fc89407abc33b98dd0ab0981.jpg'] },
  { id: 6, name: '京都', country: '日本', city: '京都', region: '关西', continent: '亚洲', best_time_to_visit: '3-4月樱花季、11月红叶季', cost_level: '中', popularity_score: 89, description: '古都风情，神社寺庙与和风街巷。', highlights: ['清水寺', '伏见稻荷大社', '岚山', '金阁寺', '祇园'], images: ['https://kimi-web-img.moonshot.cn/img/t4.ftcdn.net/b1135b9652d1ced6c89f5427aa67d4acaf13df63.jpg'] },
  { id: 7, name: '大阪', country: '日本', city: '大阪', region: '关西', continent: '亚洲', best_time_to_visit: '4-6月、10-11月', cost_level: '中', popularity_score: 87, description: '活力都市，美食与娱乐集大成。', highlights: ['大阪城', '道顿堀', '环球影城', '黑门市场', '梅田空中庭园'], images: ['https://picsum.photos/seed/osaka/800/600'] },
  { id: 8, name: '伦敦', country: '英国', city: '伦敦', region: '英格兰', continent: '欧洲', best_time_to_visit: '5-9月', cost_level: '高', popularity_score: 91, description: '历史与现代交融的世界城市。', highlights: ['大英博物馆', '伦敦塔桥', '白金汉宫', '西敏寺', '伦敦眼'], images: ['https://picsum.photos/seed/london/800/600'] },
  { id: 9, name: '纽约', country: '美国', city: '纽约', region: '纽约州', continent: '美洲', best_time_to_visit: '4-6月、9-11月', cost_level: '高', popularity_score: 93, description: '不夜城，文化与金融中心。', highlights: ['自由女神像', '时代广场', '中央公园', '大都会博物馆', '布鲁克林大桥'], images: ['https://kimi-web-img.moonshot.cn/img/images.squarespace-cdn.com/bf537a708e57e7aa7de2bb39d360534877f4a5dc.jpg'] },
  { id: 10, name: '新加坡', country: '新加坡', city: '新加坡', region: '东南亚', continent: '亚洲', best_time_to_visit: '全年（避暑季降雨高峰）', cost_level: '中-高', popularity_score: 88, description: '花园城市，秩序与多元文化并存。', highlights: ['滨海湾花园', '鱼尾狮公园', '圣淘沙', '克拉码头', '牛车水'], images: ['https://picsum.photos/seed/singapore/800/600'] },
  { id: 11, name: '曼谷', country: '泰国', city: '曼谷', region: '中部', continent: '亚洲', best_time_to_visit: '11-2月', cost_level: '中', popularity_score: 85, description: '微笑之国的门户，寺庙与夜市闻名。', highlights: ['大皇宫', '卧佛寺', '恰图恰周末市场', '考山路', '湄南河'], images: ['https://picsum.photos/seed/bangkok/800/600'] },
  { id: 12, name: '巴塞罗那', country: '西班牙', city: '巴塞罗那', region: '加泰罗尼亚', continent: '欧洲', best_time_to_visit: '4-6月、9-10月', cost_level: '中', popularity_score: 86, description: '高迪之城，建筑艺术与地中海风情。', highlights: ['圣家堂', '奎尔公园', '兰布拉大道', '巴特略之家', '海滨区'], images: ['https://picsum.photos/seed/barcelona/800/600'] },
  { id: 13, name: '巴黎', country: '法国', city: '巴黎', region: '法兰西岛', continent: '欧洲', best_time_to_visit: '4-6月、9-10月', cost_level: '高', popularity_score: 96, description: '浪漫之都，艺术与建筑的殿堂。', highlights: ['埃菲尔铁塔', '卢浮宫', '凯旋门', '塞纳河', '巴黎圣母院'], images: ['https://kimi-web-img.moonshot.cn/img/res.cloudinary.com/f2f3ad305fff24c7348dc0d5654d0dfb9d8a9e8e'] },
  
];

const DestinationsPage: React.FC = () => {
  const navigate = useNavigate();
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState<string>('');
  const [filterContinent, setFilterContinent] = useState<string>('全部');

  // 相关方案弹窗
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [activeDest, setActiveDest] = useState<Destination | null>(null);
  const [plansLoading, setPlansLoading] = useState<boolean>(false);
  const [plans, setPlans] = useState<TravelPlan[]>([]);
  const [planQ, setPlanQ] = useState<string>('');
  const [planMinScore, setPlanMinScore] = useState<number | undefined>(undefined);
  const [planDateRange, setPlanDateRange] = useState<any[]>([]);
  const [planStatus, setPlanStatus] = useState<string>('全部');

  useEffect(() => {
    const fetchDestinations = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await authFetch(buildApiUrl(API_ENDPOINTS.DESTINATIONS));
      if (!res.ok) throw new Error(`加载目的地失败 (${res.status})`);
      const data = await res.json();
      const list = Array.isArray(data) ? data : [];
      setDestinations(list.length ? list : DEFAULT_DESTINATIONS);
    } catch (e: any) {
      setError(e.message || '加载目的地失败，显示默认热门目的地');
      setDestinations(DEFAULT_DESTINATIONS);
    } finally {
      setLoading(false);
    }
    };
    fetchDestinations();
  }, []);

  const filteredDestinations = useMemo(() => {
    const keyword = q.trim().toLowerCase();
    
    let results = destinations;

    // 1. 按大洲筛选
    if (filterContinent !== '全部') {
      results = results.filter(d => d.continent === filterContinent);
    }

    // 2. 按关键字筛选
    if (keyword) {
      results = results.filter((d) => {
        const hay = [d.name, d.city, d.country, d.region, d.description].filter(Boolean).join(' ').toLowerCase();
        return hay.includes(keyword);
      });
    }

    return results;
  }, [destinations, q, filterContinent]);

  const coverImage = (d: Destination) => {
    const imgs = d.images || [];
    const first = imgs.find((u) => typeof u === 'string' && u.length > 0);
    return first;
  };

  const openPlansModal = async (d: Destination) => {
    setActiveDest(d);
    setModalOpen(true);
    setPlansLoading(true);
    setPlanQ(d.name || '');
    setPlanMinScore(undefined);
    setPlanDateRange([]);
    setPlanStatus('全部');
    try {
      // 加载个人方案与公开方案并合并，前端按目的地关键词包含过滤
      const [resPrivate, resPublic] = await Promise.all([
        authFetch(buildApiUrl(`${API_ENDPOINTS.TRAVEL_PLANS}?skip=0&limit=100`)),
        fetch(buildApiUrl(`${API_ENDPOINTS.TRAVEL_PLANS_PUBLIC}?skip=0&limit=100`))
      ]);
      if (!resPrivate.ok) throw new Error(`加载个人方案失败 (${resPrivate.status})`);
      if (!resPublic.ok) throw new Error(`加载公开方案失败 (${resPublic.status})`);
      const dataPrivate = await resPrivate.json();
      const dataPublic = await resPublic.json();
      const listPrivate: TravelPlan[] = Array.isArray(dataPrivate?.plans) ? dataPrivate.plans : (Array.isArray(dataPrivate) ? dataPrivate : []);
      const listPublic: TravelPlan[] = Array.isArray(dataPublic?.plans) ? dataPublic.plans : (Array.isArray(dataPublic) ? dataPublic : []);

      const targetName = (d.name || '').trim().toLowerCase();
      const cityName = (d.city || '').trim().toLowerCase();
      const matchByDestination = (p: TravelPlan) => {
        const dest = (p.destination || '').toLowerCase();
        return dest.includes(targetName) || (!!cityName && dest.includes(cityName));
      };

      const matchedPrivate = listPrivate.filter(matchByDestination);
      const matchedPublic = listPublic.filter(matchByDestination);
      const mergedMap = new Map<number, TravelPlan>();
      [...matchedPublic, ...matchedPrivate].forEach((p) => mergedMap.set(p.id, p));
      setPlans(Array.from(mergedMap.values()));
    } catch (e: any) {
      setPlans([]);
    } finally {
      setPlansLoading(false);
    }
  };

  const filteredPlans = useMemo(() => {
    const keyword = planQ.trim().toLowerCase();
    let result = plans;

    if (keyword) {
      result = result.filter((p) => {
        const hay = [p.title, p.description, p.status].filter(Boolean).join(' ').toLowerCase();
        return hay.includes(keyword);
      });
    }

    if (typeof planMinScore === 'number') {
      result = result.filter((p) => typeof p.score === 'number' && (p.score as number) >= planMinScore);
    }

    if (planStatus && planStatus !== '全部') {
      result = result.filter((p) => p.status === planStatus);
    }

    if (Array.isArray(planDateRange) && planDateRange.length === 2 && planDateRange[0] && planDateRange[1]) {
      const [r0, r1] = planDateRange;
      result = result.filter((p) => {
        const ds = dayjs(p.start_date);
        const de = dayjs(p.end_date);
        if (!ds.isValid() || !de.isValid()) return false;
        return !ds.isAfter(r1, 'day') && !de.isBefore(r0, 'day');
      });
    }

    return result;
  }, [plans, planQ, planMinScore, planStatus, planDateRange]);

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <Title level={2}><GlobalOutlined /> 探索热门目的地</Title>
        <Paragraph type="secondary">点击任一目的地，即刻查看该地的相关旅行方案，并在弹窗内进行二级检索</Paragraph>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <Input
            allowClear
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="搜索目的地（名称、国家、城市、区域、描述）"
            prefix={<SearchOutlined />}
          />
          <Space wrap>
            {['全部', '亚洲', '欧洲', '美洲', '大洋洲', '非洲'].map((c) => (
              <Button key={c} type={filterContinent === c ? 'primary' : 'default'} shape="round" onClick={() => setFilterContinent(c)}>
                {c}
              </Button>
            ))}
          </Space>
        </Space>
      </Card>

      {/* 热门推荐轮播 */}
      <Card style={{ marginBottom: 24 }}>
        <Title level={4} style={{ marginBottom: 12 }}>热门推荐目的地</Title>
        <Carousel autoplay dots>
          {DEFAULT_DESTINATIONS.filter(d => (d.popularity_score || 0) >= 92).map((d) => {
            const cover = (d.images && d.images[0]) || undefined;
            return (
              <div key={d.id}>
                <Row gutter={16} align="middle">
                  <Col xs={24} md={10}>
                    <Image
                       src={resolveLocalImage(d)}
                       fallback={getFallbackImage(d)}
                       alt={d.name}
                       height={220}
                       style={{ objectFit: 'cover', width: '100%' }}
                       onError={(e) => {
                         const img = e.currentTarget as HTMLImageElement;
                         const fb = getFallbackImage(d);
                         if (img.src !== fb) img.src = fb;
                       }}
                     />
                  </Col>
                  <Col xs={24} md={14}>
                    <Space direction="vertical" size={6} style={{ width: '100%' }}>
                      <Title level={4} style={{ margin: 0 }}>{d.name}</Title>
                      <Text type="secondary"><EnvironmentOutlined /> {d.country}{d.city ? ` · ${d.city}` : ''}</Text>
                      {d.best_time_to_visit && <Text type="secondary"><CalendarOutlined /> 最佳旅行时间：{d.best_time_to_visit}</Text>}
                      {d.highlights && d.highlights.length > 0 && (
                        <>
                          <Text type="secondary">热门景点：</Text>
                          <Space wrap>
                            {d.highlights.slice(0, 6).map((h) => <Tag key={h}>{h}</Tag>)}
                          </Space>
                        </>
                      )}
                      <Space>
                        <Button type="primary" onClick={() => openPlansModal(d)}>查看相关方案</Button>
                        <Button onClick={() => setFilterContinent(d.continent || '全部')}>同洲筛选</Button>
                      </Space>
                    </Space>
                  </Col>
                </Row>
              </div>
            );
          })}
        </Carousel>
      </Card>

      {/* 目的地网格 */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
        </div>
      ) : error ? (
        <Empty description={error} />
      ) : (
        <Row gutter={[16, 16]}>
          {filteredDestinations.map((d) => {
            const cover = coverImage(d);
            return (
              <Col xs={24} sm={12} md={8} lg={6} key={d.id}>
                <Card
                  hoverable
                  style={{ borderRadius: 12, overflow: 'hidden' }}
                  onClick={() => openPlansModal(d)}
                  cover={(
                    <Image src={resolveLocalImage(d)}
                      fallback={getFallbackImage(d)}
                      alt={d.name}
                      height={160}
                      preview={false}
                      style={{ objectFit: 'cover', borderTopLeftRadius: 12, borderTopRightRadius: 12 }}
                      onError={(e) => {
                        const img = e.currentTarget as HTMLImageElement;
                        const fb = getFallbackImage(d);
                        if (img.src !== fb) img.src = fb;
                      }}
                    />
                  )}
                >
                  <Space direction="vertical" size={6} style={{ width: '100%' }}>
                    <Title level={4} style={{ margin: 0 }}>{d.name}</Title>
                    <Text type="secondary">
                      <EnvironmentOutlined /> {d.country}{d.city ? ` · ${d.city}` : ''}
                    </Text>
                    <Space wrap>
                      {d.region && <Tag>{d.region}</Tag>}
                      {d.cost_level && <Tag color="orange">消费：{d.cost_level}</Tag>}
                      {typeof d.popularity_score === 'number' && <Tag color="blue">热度：{Math.round(d.popularity_score)}</Tag>}
                    </Space>
                    {d.best_time_to_visit && (
                      <Text type="secondary"><CalendarOutlined /> 最佳旅行时间：{d.best_time_to_visit}</Text>
                    )}
                  </Space>
                </Card>
              </Col>
            );
          })}
        </Row>
      )}

      {/* 相关方案弹窗 */}
      <Modal
        title={activeDest ? `目的地：${activeDest.name} · 相关方案` : '相关方案'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        footer={null}
        width={900}
      >
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <Space wrap size="middle">
            <Input.Search
              placeholder="关键词（标题/描述/状态）"
              allowClear
              style={{ width: 280 }}
              value={planQ}
              onChange={(e) => setPlanQ(e.target.value)}
              onSearch={(v) => setPlanQ(v.trim())}
            />
            <Select
              placeholder="评分"
              allowClear
              style={{ width: 160 }}
              value={planMinScore}
              onChange={(v) => setPlanMinScore(v as number | undefined)}
              options={[
                { value: 1, label: '1星及以上' },
                { value: 2, label: '2星及以上' },
                { value: 3, label: '3星及以上' },
                { value: 4, label: '4星及以上' },
                { value: 5, label: '5星' },
              ]}
            />
            <DatePicker.RangePicker
              value={planDateRange as any}
              onChange={(range) => setPlanDateRange(range || [])}
            />
            <Select
              placeholder="状态"
              allowClear
              style={{ width: 160 }}
              value={planStatus === '全部' ? undefined : planStatus}
              onChange={(v) => setPlanStatus((v as string) || '全部')}
              options={[
                { value: 'draft', label: '草稿' },
                { value: 'generating', label: '生成中' },
                { value: 'completed', label: '已完成' },
                { value: 'failed', label: '失败' },
                { value: 'archived', label: '已归档' },
              ]}
            />
            <Button onClick={() => { setPlanQ(''); setPlanMinScore(undefined); setPlanDateRange([]); setPlanStatus('全部'); }}>
              重置
            </Button>
          </Space>

          {plansLoading ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin />
            </div>
          ) : !filteredPlans.length ? (
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <Empty description="暂无相关方案" />
              {activeDest && (
                <Card>
                  <Space direction="vertical" size={6} style={{ width: '100%' }}>
                    <Title level={5} style={{ margin: 0 }}>目的地概览</Title>
                    {activeDest.description && (
                      <Paragraph type="secondary">{activeDest.description}</Paragraph>
                    )}
                    {Array.isArray(activeDest.highlights) && activeDest.highlights.length > 0 && (
                      <>
                        <Text type="secondary">热门景点：</Text>
                        <Space wrap>
                          {activeDest.highlights.map((h) => (
                            <Tag key={h}>{h}</Tag>
                          ))}
                        </Space>
                      </>
                    )}
                    <Space>
                      <Button type="primary" onClick={() => navigate('/travel')}>去创建方案</Button>
                    </Space>
                  </Space>
                </Card>
              )}
            </Space>
          ) : (
            <List
              dataSource={filteredPlans}
              grid={{ gutter: 12, column: 2 }}
              pagination={{ pageSize: 8, hideOnSinglePage: true }}
              size="small"
              renderItem={(p) => (
                <List.Item>
                  <Card hoverable style={{ width: '100%' }} bodyStyle={{ padding: 12 }}>
                    <Row gutter={12} align="middle">
                      <Col flex="auto">
                        <Space direction="vertical" size={4}>
                          <Text strong ellipsis style={{ fontSize: 16 }}>{p.title}</Text>
                          <Text type="secondary" ellipsis>
                            <EnvironmentOutlined /> {p.destination} · {dayjs(p.start_date).format('YYYY-MM-DD')} ~ {dayjs(p.end_date).format('YYYY-MM-DD')}
                          </Text>
                          <Space wrap>
                              <Tag color="blue">状态：{({ draft: '草稿', generating: '生成中', completed: '已完成', failed: '失败', archived: '已归档' } as Record<string, string>)[p.status] || p.status}</Tag>
                              {typeof p.budget === 'number' && <Tag color="orange"><DollarOutlined /> 预算：¥{p.budget}</Tag>}
                              {typeof p.score === 'number' && <Tag color="gold">评分：{p.score}</Tag>}
                              {p.is_public && <Tag color="cyan">公开</Tag>}
                            </Space>
                        </Space>
                      </Col>
                      <Col>
                        <Space>
                          <Button type="primary" onClick={() => navigate(`/plan/${p.id}`)}>查看详情</Button>
                        </Space>
                      </Col>
                    </Row>
                  </Card>
                </List.Item>
              )}
            />
          )}
        </Space>
      </Modal>
    </div>
  );
};

export default DestinationsPage;
const toSlug = (name: string) =>
  name.trim().replace(/\s+/g, '-');
const resolveLocalImage = (d: Destination) =>
  `/static/images/destinations/${toSlug(d.name)}.jpg`;
const getFallbackImage = (d: Destination) => {
  const imgs = Array.isArray(d.images) ? d.images : [];
  const first = imgs.find((u) => typeof u === 'string' && u.length > 0);
  return first || `https://picsum.photos/seed/${toSlug(d.name)}/800/600`;
};
