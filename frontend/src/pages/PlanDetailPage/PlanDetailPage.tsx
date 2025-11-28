import React, { useState, useEffect, useCallback } from 'react';
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
  Divider,
  Timeline,
  Alert,
  Spin,
  Modal,
  Rate,
  Image,
  Collapse,
  Input,
  message
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
import { Badge } from 'antd';
import { useParams, useNavigate } from 'react-router-dom';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';
import { authFetch, fetchJson, getToken } from '../../utils/auth';
import MapComponent from '../../components/MapComponent/MapComponent';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

// 景点接口定义
interface Attraction {
  name?: string;
  category?: string;
  description?: string;
  price?: number | string;
  rating?: number | string;
  visit_time?: string;
  opening_hours?: string;
  best_visit_time?: string;
  highlights?: string[];
  photography_spots?: string[];
  address?: string;
  route_tips?: string;
  experience_tips?: string[];
  tips?: string;
}

interface ScheduleEntry {
  start_time?: string;
  end_time?: string;
  time?: string;
  activity?: string;
  location?: string;
  description?: string;
  details?: string;
  cost?: number | string;
  tips?: string;
}

// 每日行程接口定义
interface DailyItinerary {
  day: number;
  date: string;
  schedule: ScheduleEntry[];
  attractions: Array<Attraction | string>;
  estimated_cost: number;
  daily_tips?: string[];
  meals?: any[];
  transportation?: any;
  stay?: {
    name?: string;
    address?: string;
    price?: number | string;
    rating?: number | string;
    stars?: number | string;
    amenities?: Array<string | { name: string }>;
  };
}

interface PlanDetail {
  id: number;
  title: string;
  destination: string;
  duration_days: number;
  generated_plans: any[];
  selected_plan: any;
  status: string;
  score: number;
  is_public?: boolean;
  public_at?: string | null;
}

interface RatingSummary {
  average: number;
  count: number;
}

interface UserRating {
  score: number | null;
  comment: string;
}

const toNumber = (value: any, fallback = 0): number => {
  if (value === undefined || value === null || value === '') return fallback;
  const num = typeof value === 'number' ? value : parseFloat(value);
  return Number.isFinite(num) ? num : fallback;
};

const ensureArray = (value: any): any[] => {
  if (Array.isArray(value)) return value;
  if (value === undefined || value === null || value === '') return [];
  return [value];
};

const normalizeAttractions = (items: any): Attraction[] =>
  ensureArray(items).map((item: any, index: number) => {
    if (!item) return {};
    if (typeof item === 'string') {
      return { name: item };
    }
    if (typeof item === 'object') {
      return item as Attraction;
    }
    return { name: `景点${index + 1}` };
  });

const normalizeScheduleEntries = (entries: any): ScheduleEntry[] =>
  ensureArray(entries).map((entry: any, index: number) => {
    if (!entry) return { activity: `行程 ${index + 1}` };
    if (typeof entry === 'string') {
      return { description: entry };
    }
    return entry as ScheduleEntry;
  });

const normalizeMeals = (meals: any): any[] =>
  ensureArray(meals).map((meal: any) => {
    if (!meal) return {};
    if (typeof meal === 'string') {
      return { description: meal };
    }
    return meal;
  });

const formatScheduleTime = (entry: ScheduleEntry): string => {
  if (entry.start_time || entry.end_time) {
    const start = entry.start_time || '未定';
    const end = entry.end_time ? ` - ${entry.end_time}` : '';
    return `${start}${end}`;
  }
  if (entry.time) return entry.time;
  return '时间待定';
};

const parseTimeToMinutes = (value?: string, fallback = Number.MAX_SAFE_INTEGER): number => {
  if (!value) return fallback;
  const lower = value.toLowerCase();
  const primarySegment = value.includes('-') ? value.split('-')[0] : value;
  const match = primarySegment.match(/(\d{1,2}):(\d{2})/);
  if (match) {
    let hour = parseInt(match[1], 10);
    const minute = parseInt(match[2], 10);
    if ((/下午|晚上|傍晚|pm/.test(lower)) && hour < 12) {
      hour += 12;
    }
    if ((/凌晨/.test(lower) || /am/.test(lower)) && hour === 12) {
      hour = 0;
    }
    return hour * 60 + minute;
  }
  const digitMatch = primarySegment.match(/(\d{1,2})/);
  if (digitMatch) {
    return parseInt(digitMatch[1], 10) * 60;
  }
  return fallback;
};

const formatRestaurantImage = (photos: any): string | undefined => {
  if (!photos || !Array.isArray(photos) || photos.length === 0) {
    return undefined;
  }

  const firstPhoto = photos[0];

  if (typeof firstPhoto === 'object' && firstPhoto.url) {
    return firstPhoto.url;
  }

  if (typeof firstPhoto === 'string' && firstPhoto.startsWith('http')) {
    return firstPhoto;
  }

  if (typeof firstPhoto === 'string') {
    return `https://example.com${firstPhoto}`;
  }

  return undefined;
};

const formatPrice = (restaurant: any): string => {
  if (typeof restaurant.price === 'number') {
    return `约 ¥${restaurant.price}`;
  }
  if (restaurant.price_range) {
    return restaurant.price_range;
  }
  if (restaurant.cost) {
    return `约 ¥${restaurant.cost}`;
  }
  return '价格未知';
};

const formatDistance = (distance: any): string => {
  if (!distance || distance === '未知') return '';

  if (typeof distance === 'number') {
    if (distance < 1000) {
      return `${distance}m`;
    }
    return `${(distance / 1000).toFixed(1)}km`;
  }

  if (typeof distance === 'string') {
    const numMatch = distance.match(/(\d+\.?\d*)/);
    if (numMatch) {
      const num = parseFloat(numMatch[1]);
      if (distance.includes('km')) {
        return `${num}km`;
      }
      if (distance.includes('m')) {
        return `${num}m`;
      }
      if (num < 1000) {
        return `${num}m`;
      }
      return `${(num / 1000).toFixed(1)}km`;
    }
  }

  return String(distance);
};

const TRANSPORT_TYPE_LABELS: Record<string, string> = {
  car: '自驾/汽车',
  driving: '自驾',
  taxi: '打车',
  ride: '打车',
  bus: '公交',
  coach: '大巴',
  subway: '地铁',
  metro: '地铁',
  train: '火车',
  highspeed_train: '高铁',
  flight: '航班',
  airplane: '航班',
  bike: '骑行',
  bicycle: '骑行',
  walk: '步行',
  ferry: '轮渡',
  ship: '轮渡',
  boat: '船',
  tram: '有轨电车',
};

const getTransportationTypeLabel = (type?: string): string => {
  if (!type) return '交通';
  const key = String(type).toLowerCase();
  return TRANSPORT_TYPE_LABELS[key] || type;
};

const formatTransportation = (transportation: any): React.ReactNode => {
  if (!transportation) return '暂无';

  if (Array.isArray(transportation)) {
    return (
      <Space wrap size="small">
        {transportation.map((t: any, idx: number) => {
          if (t == null) return <span key={idx}>-</span>;
          if (typeof t === 'object') {
            const type = getTransportationTypeLabel(t.type);
            const distance = typeof t.distance === 'number' ? `${t.distance} 公里` : (t.distance || '');
            const duration = typeof t.duration === 'number' ? `${t.duration} 分钟` : (t.duration || '');
            const hasPrice = t.price !== undefined && t.price !== null;
            const price = hasPrice ? `¥${toNumber(t.price)}` : (t.cost != null ? `¥${toNumber(t.cost)}` : '');
            const parts = [type, distance, duration, price].filter(Boolean).join(' · ');
            return <span key={idx}>{parts || type}</span>;
          }
          return <span key={idx}>{String(t)}</span>;
        })}
      </Space>
    );
  }

  if (typeof transportation === 'object') {
    const type = getTransportationTypeLabel(transportation.type);
    const distance = typeof transportation.distance === 'number' ? `${transportation.distance} 公里` : (transportation.distance || '');
    const duration = typeof transportation.duration === 'number' ? `${transportation.duration} 分钟` : (transportation.duration || '');
    const hasPrice = transportation.price !== undefined && transportation.price !== null;
    const price = hasPrice ? `¥${toNumber(transportation.price)}` : (transportation.cost != null ? `¥${toNumber(transportation.cost)}` : '');
    const parts = [type, distance, duration, price].filter(Boolean).join(' · ');
    return parts || type;
  }

  return String(transportation);
};

const renderTransportationPriceTag = (price: any): React.ReactNode => {
  if (price === undefined || price === null || price === '') return null;
  const value = toNumber(price, 0);
  const isFree = value === 0;
  return (
    <Tag color={isFree ? 'cyan' : 'gold'}>
      {isFree ? '费用 ¥0 (免费)' : `费用 ¥${value}`}
    </Tag>
  );
};

interface LimitedTagListProps {
  items: any[];
  color?: string;
  max?: number;
  tagStyle?: React.CSSProperties;
  renderItem?: (item: any, index: number) => React.ReactNode;
}

const LimitedTagList: React.FC<LimitedTagListProps> = ({ items, color = 'default', max, tagStyle, renderItem }) => {
  if (!items || items.length === 0) return null;
  const data = typeof max === 'number' ? items.slice(0, max) : items;
  return (
    <Space wrap size={4} className="limited-tags">
      {data.map((item, index) => (
        <Tag key={index} color={color} style={{ fontSize: 10, ...tagStyle }}>
          {renderItem ? renderItem(item, index) : (typeof item === 'string' ? item : item?.name || '推荐项')}
        </Tag>
      ))}
    </Space>
  );
};

const ActivityTimelineCard: React.FC<{ entry: ScheduleEntry }> = ({ entry }) => (
  <Card size="small" bordered={false} style={{ backgroundColor: 'rgba(96, 165, 250, 0.12)' }}>
    <Space direction="vertical" size={2} style={{ width: '100%' }}>
      <Space size={6} wrap align="center">
        <Tag color="blue" style={{ marginBottom: 0 }}>{formatScheduleTime(entry)}</Tag>
        {entry.activity && <Text strong>{entry.activity}</Text>}
      </Space>
      {entry.location && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          <EnvironmentOutlined style={{ marginRight: 4 }} /> {entry.location}
        </Text>
      )}
      {(entry.description || entry.details) && (
        <Text style={{ fontSize: 13 }}>
          {entry.description || entry.details}
        </Text>
      )}
      {(entry.cost !== undefined && entry.cost !== null) && (
        <Tag color="gold">预计费用 ¥{toNumber(entry.cost)}</Tag>
      )}
      {entry.tips && (
        <Text type="secondary" style={{ fontSize: 12 }}>{entry.tips}</Text>
      )}
    </Space>
  </Card>
);

const MealTimelineCard: React.FC<{ meal: any }> = ({ meal }) => (
  <Card size="small" bordered={false} style={{ backgroundColor: 'rgba(250, 140, 22, 0.12)' }}>
    <Space direction="vertical" size={2} style={{ width: '100%' }}>
      <Space size={6} wrap align="center">
        <Tag color="orange" style={{ marginBottom: 0 }}>{meal.type || '餐饮'}</Tag>
        <Tag color="geekblue" style={{ marginBottom: 0 }}>{meal.time || '时间待定'}</Tag>
      </Space>
      <Text strong>{meal.restaurant_name || meal.name || meal.cuisine || '餐饮安排'}</Text>
      {meal.address && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          <EnvironmentOutlined style={{ marginRight: 4 }} /> {meal.address}
        </Text>
      )}
      {meal.description && (
        <Text style={{ fontSize: 12 }}>{meal.description}</Text>
      )}
      <Space size={4} wrap>
        {meal.cuisine && <Tag color="magenta">{meal.cuisine}</Tag>}
        {meal.estimated_cost != null && (
          <Tag color="gold">约 ¥{toNumber(meal.estimated_cost)}</Tag>
        )}
      </Space>
      {meal.recommended_dishes && ensureArray(meal.recommended_dishes).length > 0 && (
        <LimitedTagList
          items={ensureArray(meal.recommended_dishes)}
          color="geekblue"
          max={3}
          renderItem={(dish: any) => (typeof dish === 'string' ? dish : (dish?.name || '推荐菜'))}
        />
      )}
      {meal.booking_tips && (
        <Text type="secondary" style={{ fontSize: 12 }}>{meal.booking_tips}</Text>
      )}
    </Space>
  </Card>
);

const buildTimelineItems = (scheduleEntries: ScheduleEntry[], meals: any[] = []) => {
  const combined: Array<{ minutes: number; order: number; type: 'activity' | 'meal'; node: React.ReactNode }> = [];
  scheduleEntries.forEach((entry, idx) => {
    const reference = entry.start_time || entry.time?.split('-')[0] || entry.time;
    combined.push({
      minutes: parseTimeToMinutes(reference, 60000 + idx),
      order: idx,
      type: 'activity',
      node: <ActivityTimelineCard entry={entry} />,
    });
  });
  meals.forEach((meal, idx) => {
    combined.push({
      minutes: parseTimeToMinutes(meal.time, 70000 + idx),
      order: idx,
      type: 'meal',
      node: <MealTimelineCard meal={meal} />,
    });
  });
  combined.sort((a, b) => {
    if (a.minutes === b.minutes) {
      return a.order - b.order;
    }
    return a.minutes - b.minutes;
  });
  return combined.map(item => ({
    color: item.type === 'meal' ? '#fa8c16' : '#1890ff',
    dot: item.type === 'meal'
      ? <ShopOutlined style={{ fontSize: 14 }} />
      : <ClockCircleOutlined style={{ fontSize: 14 }} />,
    children: item.node,
  }));
};

const AttractionCard: React.FC<{ attraction: Attraction; index: number }> = ({ attraction, index }) => {
  const ratingValue = toNumber(attraction.rating);
  const highlights = ensureArray(attraction.highlights);
  const experienceTips = ensureArray(attraction.experience_tips);

  return (
    <Card key={index} size="small" style={{ backgroundColor: 'rgba(82, 196, 26, 0.12)' }}>
      <Space direction="vertical" size={4} style={{ width: '100%' }}>
        <Space align="center" style={{ width: '100%', justifyContent: 'space-between' }}>
          <Text strong>{attraction.name || `景点${index + 1}`}</Text>
          <Rate disabled value={ratingValue} style={{ fontSize: 10 }} />
        </Space>
        {attraction.description && (
          <Text type="secondary" style={{ fontSize: 12 }}>{attraction.description}</Text>
        )}
        <Space size={4} wrap>
          {attraction.category && (
            <Tag color="green" style={{ fontSize: 10 }}>
              <TagOutlined style={{ fontSize: 8 }} /> {attraction.category}
            </Tag>
          )}
          {(attraction.visit_time || attraction.best_visit_time) && (
            <Tag color="orange" style={{ fontSize: 10 }}>
              <ClockCircleOutlined style={{ fontSize: 8 }} /> {attraction.visit_time || attraction.best_visit_time}
            </Tag>
          )}
        </Space>
        {highlights.length > 0 && (
          <LimitedTagList items={highlights} color="gold" max={3} />
        )}
        {experienceTips.length > 0 && (
          <LimitedTagList items={experienceTips} color="magenta" max={3} />
        )}
      </Space>
    </Card>
  );
};

const AttractionSection: React.FC<{ attractions: Attraction[] }> = ({ attractions }) => (
  <Card size="small" title="精彩看点" bordered={false}>
    {attractions.length > 0 ? (
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        {attractions.map((attraction, index) => (
          <AttractionCard key={index} attraction={attraction} index={index} />
        ))}
      </Space>
    ) : (
      <Text type="secondary">暂无景点推荐</Text>
    )}
  </Card>
);

const DailyTipsSection: React.FC<{ tips: string[] }> = ({ tips }) => (
  <Card size="small" title="当日建议" bordered={false}>
    <LimitedTagList items={tips} color="geekblue" tagStyle={{ fontSize: '10px' }} />
  </Card>
);

const TransportationDetails: React.FC<{ transportation: any }> = ({ transportation }) => {
  if (!transportation) {
    return <Text type="secondary">暂无交通安排</Text>;
  }

  if (Array.isArray(transportation)) {
    return (
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        {transportation.map((route: any, idx: number) => (
          <Card key={idx} size="small" style={{ borderColor: '#f0f0f0' }}>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Text strong>{getTransportationTypeLabel(route?.type)} {route?.name}</Text>
              {route?.route && <Text type="secondary" style={{ fontSize: 12 }}>{route.route}</Text>}
              <Space size={4} wrap>
                {route?.duration && <Tag color="blue">耗时 {route.duration}{typeof route.duration === 'number' ? ' 分钟' : ''}</Tag>}
                {route?.distance && <Tag color="green">距离 {route.distance}{typeof route.distance === 'number' ? ' 公里' : ''}</Tag>}
                {renderTransportationPriceTag(route?.price ?? route?.cost)}
              </Space>
              {route?.usage_tips && ensureArray(route.usage_tips).length > 0 && (
                <LimitedTagList items={ensureArray(route.usage_tips)} color="geekblue" />
              )}
            </Space>
          </Card>
        ))}
      </Space>
    );
  }

  if (typeof transportation === 'object') {
    const primaryRoutes = ensureArray(transportation.primary_routes);
    const backupRoutes = ensureArray(transportation.backup_routes);
    if (primaryRoutes.length || backupRoutes.length) {
      return (
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          {primaryRoutes.map((route: any, idx: number) => (
            <Card key={`primary-${idx}`} size="small" style={{ borderColor: '#f0f0f0' }}>
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Text strong>{getTransportationTypeLabel(route?.type)} {route?.name}</Text>
                {route?.route && <Text type="secondary" style={{ fontSize: 12 }}>{route.route}</Text>}
                <Space size={4} wrap>
                  {route?.duration && <Tag color="blue">耗时 {route.duration}{typeof route.duration === 'number' ? ' 分钟' : ''}</Tag>}
                  {route?.distance && <Tag color="green">距离 {route.distance}{typeof route.distance === 'number' ? ' 公里' : ''}</Tag>}
                  {renderTransportationPriceTag(route?.price ?? route?.cost)}
                </Space>
                {route?.usage_tips && ensureArray(route.usage_tips).length > 0 && (
                  <LimitedTagList items={ensureArray(route.usage_tips)} color="geekblue" />
                )}
              </Space>
            </Card>
          ))}
          {backupRoutes.length > 0 && (
            <Card size="small" style={{ borderColor: '#f5f5f5' }}>
              <Text strong>备用路线</Text>
              <div style={{ marginTop: 4 }}>
                {backupRoutes.map((route: any, idx: number) => (
                  <Tag key={`backup-${idx}`} style={{ marginBottom: 4 }}>
                    {getTransportationTypeLabel(route?.type) || '路线'} {route?.name}
                  </Tag>
                ))}
              </div>
            </Card>
          )}
          {transportation.daily_transport_cost != null && (
            <Tag color="purple">当日交通费用 ¥{toNumber(transportation.daily_transport_cost)}</Tag>
          )}
          {transportation.tips && ensureArray(transportation.tips).length > 0 && (
            <LimitedTagList items={ensureArray(transportation.tips)} color="cyan" />
          )}
        </Space>
      );
    }
  }

  return <>{formatTransportation(transportation)}</>;
};

const ItineraryPanelHeader: React.FC<{ day: DailyItinerary }> = ({ day }) => {
  const scheduleCount = ensureArray(day.schedule).length;
  const mealsCount = ensureArray(day.meals).length;
  return (
    <Space size={12} wrap align="center">
      <Tag color="geekblue" style={{ marginBottom: 0 }}>第 {day.day} 天</Tag>
      <Text type="secondary">{day.date}</Text>
      <Space size={4}>
        <DollarOutlined style={{ color: '#52c41a' }} />
        <Text>¥{toNumber(day.estimated_cost)}</Text>
      </Space>
      <Text type="secondary" style={{ fontSize: 12 }}>行程 {scheduleCount || 0} 项</Text>
      {mealsCount > 0 && <Text type="secondary" style={{ fontSize: 12 }}>餐饮 {mealsCount} 项</Text>}
    </Space>
  );
};

const DailyItineraryCard: React.FC<{ day: DailyItinerary }> = ({ day }) => {
  const scheduleEntries = normalizeScheduleEntries(day.schedule);
  const meals = normalizeMeals(day.meals);
  const attractions = normalizeAttractions(day.attractions);
  const dailyTips = ensureArray(day.daily_tips);
  const timelineItems = buildTimelineItems(scheduleEntries);

  return (
    <Card size="small" className="glass-card" style={{ width: '100%' }}>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Space size={8} align="center" wrap>
          <Tag color="geekblue">第 {day.day} 天</Tag>
          <Text type="secondary">{day.date}</Text>
          <Tag color="orange">预计花费 ¥{toNumber(day.estimated_cost)}</Tag>
        </Space>
        <Row gutter={[24, 24]}>
          <Col xs={24} lg={14}>
            <Card size="small" title="行程安排" bordered={false} className="glass-card">
              {timelineItems.length > 0 ? (
                <Timeline mode="left" items={timelineItems} />
              ) : (
                <Alert type="info" message="暂无行程安排" showIcon />
              )}
            </Card>
            {meals.length > 0 && (
              <Card size="small" title="餐饮安排" bordered={false} className="glass-card" style={{ marginTop: 16 }}>
                <List
                  size="small"
                  dataSource={meals}
                  renderItem={(meal: any, idx: number) => (
                    <List.Item key={idx}>
                      <MealTimelineCard meal={meal} />
                    </List.Item>
                  )}
                />
              </Card>
            )}
          </Col>
          <Col xs={24} lg={10}>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <AttractionSection attractions={attractions} />
              {day.transportation && (
                <Card size="small" title="交通" bordered={false} className="glass-card">
                  <TransportationDetails transportation={day.transportation} />
                </Card>
              )}
              <Card size="small" title="费用与住宿" bordered={false} className="glass-card">
                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  {day.stay ? (
                    <Space direction="vertical" size={2}>
                      <Text strong>{day.stay.name}</Text>
                      {day.stay.address && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          <EnvironmentOutlined style={{ marginRight: 4 }} /> {day.stay.address}
                        </Text>
                      )}
                      <Space size={4}>
                        {day.stay.rating && <Tag color="gold">评分 {day.stay.rating}</Tag>}
                        {day.stay.price != null && <Tag color="cyan">¥{toNumber(day.stay.price)} /晚</Tag>}
                        {day.stay.stars && <Tag color="blue">{day.stay.stars} 星</Tag>}
                      </Space>
                      {ensureArray(day.stay.amenities).length > 0 && (
                        <Space direction="vertical" size={2} style={{ width: '100%' }}>
                          <Text type="secondary" style={{ fontSize: 12 }}>设施服务</Text>
                          <LimitedTagList
                            items={ensureArray(day.stay.amenities)}
                            color="cyan"
                            max={6}
                            tagStyle={{ fontSize: 10 }}
                          />
                        </Space>
                      )}
                    </Space>
                  ) : (
                    <Text type="secondary">参考主方案住宿</Text>
                  )}
                </Space>
              </Card>
              {dailyTips.length > 0 && <DailyTipsSection tips={dailyTips} />}
            </Space>
          </Col>
        </Row>
      </Space>
    </Card>
  );
};

const normalizeMenuHighlights = (menuHighlights: any): any[] => {
  if (!menuHighlights) return [];
  return Array.isArray(menuHighlights)
    ? menuHighlights
    : Object.values(menuHighlights || {});
};

const RestaurantDishSection: React.FC<{ restaurant: any }> = ({ restaurant }) => {
  const signatureDishes = ensureArray(restaurant.signature_dishes);
  const menuHighlights = normalizeMenuHighlights(restaurant.menu_highlights);
  const specialties = ensureArray(restaurant.specialties);
  const recommended = ensureArray(restaurant.recommended_dishes);

  const primary = signatureDishes.length
    ? signatureDishes
    : menuHighlights.length
      ? menuHighlights
      : specialties.length
        ? specialties
        : recommended;

  if (!primary.length) return null;

  const normalized = primary.map((dish: any) => (
    typeof dish === 'string' ? { name: dish } : dish
  ));

  return (
    <Space direction="vertical" size={4} style={{ width: '100%' }}>
      <Text strong style={{ fontSize: '12px' }}>招牌菜 / 菜品推荐</Text>
      <LimitedTagList
        items={primary}
        color="geekblue"
        max={5}
        renderItem={(dish: any) => (typeof dish === 'string' ? dish : (dish?.name || '推荐菜'))}
      />
      <Collapse size="small" bordered={false} style={{ background: 'transparent' }}>
        <Collapse.Panel header="查看菜品详情" key="dishes">
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            {normalized.slice(0, 6).map((dish: any, idx: number) => (
              <Row key={idx} gutter={8} align="middle">
                <Col span={12}>
                  <Space size={4}>
                    <Tag color="geekblue" style={{ fontSize: '11px' }}>{dish?.name || '推荐菜'}</Tag>
                    {dish?.price && <Text type="secondary" style={{ fontSize: '11px' }}>{dish.price}</Text>}
                  </Space>
                </Col>
                <Col span={12} style={{ textAlign: 'right' }}>
                  {dish?.taste && <Text type="secondary" style={{ fontSize: '11px' }}>{dish.taste}</Text>}
                </Col>
                {dish?.description && (
                  <Col span={24}>
                    <Text type="secondary" style={{ fontSize: '12px' }}>{dish.description}</Text>
                  </Col>
                )}
              </Row>
            ))}
          </Space>
        </Collapse.Panel>
      </Collapse>
    </Space>
  );
};

const RestaurantCard: React.FC<{ restaurant: any }> = ({ restaurant }) => {
  const imageUrl = formatRestaurantImage(restaurant.photos);
  const distanceLabel = restaurant.distance ? formatDistance(restaurant.distance) : '';

  return (
    <Card 
      size="small" 
      style={{ width: '100%' }}
      bodyStyle={{ padding: '12px' }}
    >
      <Row gutter={[12, 8]} align="top">
        <Col span={6}>
          {imageUrl ? (
            <Image
              width={60}
              height={60}
              src={imageUrl}
              alt={restaurant.name}
              style={{ borderRadius: '6px', objectFit: 'cover' }}
              fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjYwIiBoZWlnaHQ9IjYwIiBmaWxsPSIjRjVGNUY1Ii8+CjxwYXRoIGQ9Ik0yMCAyMEg0MFY0MEgyMFYyMFoiIGZpbGw9IiNEOUQ5RDkiLz4KPC9zdmc+"
              preview={{
                mask: <PictureOutlined style={{ fontSize: '16px' }} />
              }}
            />
          ) : (
            <div style={{ width: 60, height: 60, backgroundColor: 'var(--overlay)', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <PictureOutlined style={{ color: 'var(--text-soft)', fontSize: '20px' }} />
            </div>
          )}
        </Col>
        <Col span={18}>
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            <Row justify="space-between" align="middle">
              <Col>
                <Text strong style={{ fontSize: '14px' }}>
                  {restaurant.name}
                </Text>
              </Col>
              <Col>
                <Space size={4}>
                  <Rate disabled defaultValue={restaurant.rating || 0} style={{ fontSize: '12px' }} />
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    {restaurant.rating ? restaurant.rating.toFixed(1) : 'N/A'}
                  </Text>
                </Space>
              </Col>
            </Row>
            <Row justify="space-between" align="middle">
              <Col>
                <Space size={4}>
                  <TagOutlined style={{ fontSize: '12px', color: 'var(--text-soft)' }} />
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
            {restaurant.address && (
              <Row>
                <Col span={24}>
                  <Space size={4} align="start">
                    <EnvironmentOutlined style={{ fontSize: '12px', color: 'var(--text-soft)', marginTop: '2px' }} />
                    <Text type="secondary" style={{ fontSize: '11px', wordBreak: 'break-all', whiteSpace: 'normal', lineHeight: '1.4' }}>
                      {restaurant.address}
                    </Text>
                  </Space>
                </Col>
              </Row>
            )}
            <Row justify="space-between" align="middle">
              {restaurant.phone && (
                <Col>
                  <Space size={4}>
                    <PhoneOutlined style={{ fontSize: '12px', color: '#1890ff' }} />
                    <Text style={{ fontSize: '11px' }}>
                      {restaurant.phone}
                    </Text>
                  </Space>
                </Col>
              )}
              {distanceLabel && (
                <Col>
                  <Text type="secondary" style={{ fontSize: '11px' }}>
                    距离: {distanceLabel}
                  </Text>
                </Col>
              )}
            </Row>
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
            <RestaurantDishSection restaurant={restaurant} />
          </Space>
        </Col>
      </Row>
    </Card>
  );
};

const PlanDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [planDetail, setPlanDetail] = useState<PlanDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedPlanIndex, setSelectedPlanIndex] = useState(0);
  const [exportModalVisible, setExportModalVisible] = useState(false);
  const [shareModalVisible, setShareModalVisible] = useState(false);
  const [showAllHotels, setShowAllHotels] = useState(false);
  // 新增：评分相关状态
  const [ratingSummary, setRatingSummary] = useState<RatingSummary | null>(null);
  const [myRating, setMyRating] = useState<UserRating>({ score: null, comment: '' });
  const [recentRatings, setRecentRatings] = useState<any[]>([]);
  const [submittingRating, setSubmittingRating] = useState(false);
  const [isPublicView, setIsPublicView] = useState<boolean>(!getToken());
  const [publishing, setPublishing] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);

  const fetchPlanDetail = useCallback(async () => {
    try {
      if (!id) throw new Error('缺少计划ID');
      const planId = Number(id);
      const token = getToken();

      if (token) {
        // 优先尝试私有详情；若403/404则回退到公开详情
        const respPrivate = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_DETAIL(planId)));
        if (respPrivate.ok) {
          const data = await respPrivate.json();
          setIsPublicView(false);
          setPlanDetail(data);
          try {
            const idx = (Array.isArray(data.generated_plans) && data.selected_plan)
              ? data.generated_plans.findIndex((p: any) => (
                  (p?.title === data.selected_plan?.title) && (p?.type === data.selected_plan?.type)
                ))
              : 0;
            setSelectedPlanIndex(idx >= 0 ? idx : 0);
          } catch {}
        } else if (respPrivate.status === 403 || respPrivate.status === 404) {
          const respPublic = await fetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_PUBLIC_DETAIL(planId)));
          if (respPublic.ok) {
            const data = await respPublic.json();
            setIsPublicView(true);
            setPlanDetail(data);
            try {
              const idx = (Array.isArray(data.generated_plans) && data.selected_plan)
                ? data.generated_plans.findIndex((p: any) => (
                    (p?.title === data.selected_plan?.title) && (p?.type === data.selected_plan?.type)
                  ))
                : 0;
              setSelectedPlanIndex(idx >= 0 ? idx : 0);
            } catch {}
          } else {
            throw new Error(`获取计划公开详情失败 (${respPublic.status})`);
          }
        } else {
          throw new Error(`获取计划详情失败 (${respPrivate.status})`);
        }
      } else {
        // 未登录用户直接走公开详情
        const respPublic = await fetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_PUBLIC_DETAIL(planId)));
        if (!respPublic.ok) throw new Error(`获取计划公开详情失败 (${respPublic.status})`);
        const data = await respPublic.json();
        setIsPublicView(true);
        setPlanDetail(data);
        try {
          const idx = (Array.isArray(data.generated_plans) && data.selected_plan)
            ? data.generated_plans.findIndex((p: any) => (
                (p?.title === data.selected_plan?.title) && (p?.type === data.selected_plan?.type)
              ))
            : 0;
          setSelectedPlanIndex(idx >= 0 ? idx : 0);
        } catch {}
      }
    } catch (error) {
      console.error('获取计划详情失败:', error);
      message.error('无法加载计划详情');
    } finally {
      setLoading(false);
    }
  }, [id]);

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

  useEffect(() => {
    fetchPlanDetail();
  }, [fetchPlanDetail]);

  // 新增：当计划详情加载完成后获取评分信息（公开视图不请求）
  useEffect(() => {
    if (!id) return;
    if (isPublicView) return;
    const planId = Number(id);
    const run = async () => {
      await Promise.all([
        fetchRatingSummary(planId),
        fetchMyRating(planId),
        fetchRecentRatings(planId)
      ]);
    };
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planDetail?.id, isPublicView]);

  // =============== 评分相关函数 ===============
  const fetchRatingSummary = async (planId: number) => {
    try {
      const resp = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_RATINGS_SUMMARY(planId)));
      if (resp.ok) {
        const data = await resp.json();
        setRatingSummary(data);
      }
    } catch (err) {
      console.error('获取评分汇总失败:', err);
    }
  };

  const fetchMyRating = async (planId: number) => {
    try {
      const resp = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_RATINGS_ME(planId)));
      if (resp.ok) {
        const data = await resp.json();
        if (data) {
          setMyRating({ score: data.score, comment: data.comment || '' });
        } else {
          setMyRating({ score: null, comment: '' });
        }
      }
    } catch (err) {
      console.error('获取个人评分失败:', err);
    }
  };

  const fetchRecentRatings = async (planId: number) => {
    try {
      const resp = await authFetch(buildApiUrl(`${API_ENDPOINTS.TRAVEL_PLAN_RATINGS(planId)}?skip=0&limit=5`));
      if (resp.ok) {
        const data = await resp.json();
        setRecentRatings(data || []);
      }
    } catch (err) {
      console.error('获取评分列表失败:', err);
    }
  };

  const submitRating = async () => {
    if (!id) return;
    const planId = Number(id);
    if (!myRating.score) {
      message.warning('请先选择评分星级');
      return;
    }
    try {
      setSubmittingRating(true);
      const resp = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_RATINGS(planId)), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ score: myRating.score, comment: myRating.comment })
      });
      if (resp.ok) {
        const data = await resp.json();
        setRatingSummary(data.summary);
        // 同步顶部评分的本地显示（不必等待重新获取详情）
        setPlanDetail(prev => prev ? { ...prev, score: data.summary.average } : prev);
        message.success('评分已提交');
        fetchRecentRatings(planId);
      } else {
        message.error('提交评分失败');
      }
    } catch (err) {
      console.error('提交评分失败:', err);
      message.error('提交评分失败');
    } finally {
      setSubmittingRating(false);
    }
  };

  const handleSelectPlan = async (planIndex: number) => {
    if (isPublicView) {
      message.info('公开视图不可选择方案');
      return;
    }
    try {
      const response = await authFetch(buildApiUrl(API_ENDPOINTS.TRAVEL_PLAN_SELECT(Number(id))), {
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

  // 新增：发布/取消发布切换
  const togglePublish = async () => {
    if (!id || !planDetail) return;
    const guardRef = (togglePublish as any)._lastTsRef || ((togglePublish as any)._lastTsRef = { current: 0 });
    const now = Date.now();
    if (now - guardRef.current < 2000) {
      message.warning('操作过于频繁，请稍后再试');
      return;
    }
    guardRef.current = now;
    const planId = Number(id);
    setPublishing(true);
    try {
      const endpoint = planDetail.is_public
        ? API_ENDPOINTS.TRAVEL_PLAN_UNPUBLISH(planId)
        : API_ENDPOINTS.TRAVEL_PLAN_PUBLISH(planId);
      await fetchJson(buildApiUrl(endpoint), { method: 'PUT', headers: { 'Content-Type': 'application/json' } });
      await fetchPlanDetail();
      message.success(planDetail.is_public ? '已取消公开' : '已公开发布');
    } catch (err: any) {
      console.error('发布/取消发布失败:', err);
      console.error(err);
      if (err && err.status === -1) {
        message.error('网络异常或操作过于频繁被阻止，请稍后再试');
      } else {
        const msg = (err && err.message) ? String(err.message) : '';
        message.error(msg || '发布操作失败');
      }
    } finally {
      setPublishing(false);
    }
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
  const getWeatherClass = (desc: string) => {
    const t = String(desc || '').toLowerCase();
    if (!t) return 'weather-default';
    if (t.includes('雷')) return 'weather-thunder';
    if (t.includes('雨')) return 'weather-rainy';
    if (t.includes('雪')) return 'weather-snow';
    if (t.includes('晴') || t.includes('sun')) return 'weather-sunny';
    if (t.includes('云') || t.includes('阴') || t.includes('cloud')) return 'weather-cloudy';
    return 'weather-default';
  };

  return (
    <div className="plan-detail-page" style={{ maxWidth: '1200px', margin: '0 auto' }}>
      {/* 计划头部信息 */}
      <Card className="plan-header-card" style={{ marginBottom: '24px' }}>
        <Row gutter={[24, 16]} align="middle">
          <Col xs={24} md={16}>
            <Space direction="vertical" size="small">
              <Title level={2} className="gradient-text" style={{ margin: 0 }}>
                {planDetail.title}
              </Title>
              <Space>
                <Tag color="blue" icon={<EnvironmentOutlined />}> 
                  {planDetail.destination}
                </Tag>
                <Tag color="green" icon={<CalendarOutlined />}> 
                  {planDetail.duration_days} 天
                </Tag>
                <Tag color="gold" icon={<StarOutlined />}> 
                  评分: {ratingSummary ? ratingSummary.average.toFixed(1) : (planDetail.score?.toFixed(1) || 'N/A')}
                </Tag>
                {typeof planDetail.is_public !== 'undefined' && (
                  <Tag color={planDetail.is_public ? 'cyan' : 'default'}>
                    {planDetail.is_public ? '公开' : '私密'}
                  </Tag>
                )}
              </Space>
            </Space>
          </Col>
          <Col xs={24} md={8}>
            <Space wrap size="small" style={{ width: '100%' }}>
              {!isPublicView && isAdmin && (
                <Button 
                  type="default"
                  size="small"
                  className="btn-secondary"
                  icon={<EditOutlined />}
                  onClick={() => navigate(`/plan/${id}/edit`)}
                >
                  编辑
                </Button>
              )}
              <Button 
                className="btn-secondary"
                size="small"
                icon={<ShareAltOutlined />}
                onClick={() => {
                  setShareModalVisible(true);
                }}
              >
                分享
              </Button>
              {!isPublicView && (
                <>
                  <Button type="default" size="small" className="btn-secondary" icon={<CloudOutlined />} loading={publishing} onClick={togglePublish}>
                    {planDetail.is_public ? '取消公开' : '公开发布'}
                  </Button>
                  <Button 
                    type="primary"
                    className="btn-primary"
                    size="small"
                    icon={<ExportOutlined />}
                    onClick={() => setExportModalVisible(true)}
                  >
                    导出
                  </Button>
                </>
              )}
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 方案选择 */}
      {planDetail.generated_plans && Array.isArray(planDetail.generated_plans) && planDetail.generated_plans.length > 1 && (
        <Card title="选择方案" className="glass-card" style={{ marginBottom: '24px' }}>
          <Row gutter={[16, 16]}>
            {planDetail.generated_plans.map((plan, index) => (
              <Col xs={24} sm={12} md={8} key={index}>
                {selectedPlanIndex === index ? (
                  <Badge.Ribbon text="已选" color="cyan">
                    <Card
                      size="small"
                      hoverable
                      className="glass-card"
                      onClick={() => handleSelectPlan(index)}
                      style={{ cursor: 'pointer' }}
                    >
                      <Space direction="vertical" size="small" style={{ width: '100%' }}>
                        {plan.type && <Tag color={(() => { const t = String(plan.type).toLowerCase(); if (t.includes('经济')||t.includes('budget')) return 'green'; if (t.includes('豪华')||t.includes('luxury')) return 'purple'; if (t.includes('轻奢')||t.includes('premium')) return 'volcano'; return 'geekblue'; })()}>{plan.type}</Tag>}
                        <Text type="secondary">{plan.title}</Text>
                        <Space>
                          {typeof plan.score === 'number' && <Tag color="gold">评分: {plan.score.toFixed(1)}</Tag>}
                          {plan.total_cost?.total && <Tag color="orange">预算: ¥{plan.total_cost.total.toLocaleString()}</Tag>}
                        </Space>
                      </Space>
                    </Card>
                  </Badge.Ribbon>
                ) : (
                  <Card
                    size="small"
                    hoverable
                    className="glass-card"
                    onClick={() => handleSelectPlan(index)}
                    style={{ cursor: 'pointer' }}
                  >
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      {plan.type && <Tag color={(() => { const t = String(plan.type).toLowerCase(); if (t.includes('经济')||t.includes('budget')) return 'green'; if (t.includes('豪华')||t.includes('luxury')) return 'purple'; if (t.includes('轻奢')||t.includes('premium')) return 'volcano'; return 'geekblue'; })()}>{plan.type}</Tag>}
                      <Text type="secondary">{plan.title}</Text>
                      <Space>
                        {typeof plan.score === 'number' && <Tag color="gold">评分: {plan.score.toFixed(1)}</Tag>}
                        {plan.total_cost?.total && <Tag color="orange">预算: ¥{plan.total_cost.total.toLocaleString()}</Tag>}
                      </Space>
                    </Space>
                  </Card>
                )}
              </Col>
            ))}
          </Row>
        </Card>
      )}

      {/* 方案详情 */}
      {planDetail.status === 'generating' ? (
        <Card style={{ textAlign: 'center', padding: '60px 20px' }}>
          <Spin size="large" />
          <div style={{ marginTop: '24px' }}>
            <Title level={4}>方案生成中</Title>
            <Text type="secondary">AI正在为您生成旅行方案，请稍候...</Text>
          </div>
        </Card>
      ) : currentPlan ? (
        <Tabs defaultActiveKey="overview" style={{ marginBottom: '24px' }}>
          <TabPane tab="方案概览" key="overview">
            <Row gutter={[24, 24]}>
              <Col xs={24} lg={16}>
                <Card title="行程安排" className="glass-card">
                  <Tabs size="small" defaultActiveKey="itinerary">
                    <TabPane tab="每日行程" key="itinerary">

                      <Collapse
                        bordered={false}
                        defaultActiveKey={Array.isArray(currentPlan.daily_itineraries) && currentPlan.daily_itineraries.length > 0
                          ? currentPlan.daily_itineraries.slice(0, 1).map((day: DailyItinerary, idx: number) => `day-${day.day ?? idx}`)
                          : []}
                      >
                        {Array.isArray(currentPlan.daily_itineraries) && currentPlan.daily_itineraries.length > 0 ? (
                          currentPlan.daily_itineraries.map((day: DailyItinerary, index: number) => (
                          <Collapse.Panel
                            key={`day-${day.day ?? index}`}
                            header={<ItineraryPanelHeader day={day} />}
                          >
                            <DailyItineraryCard day={day} />
                          </Collapse.Panel>
                          ))
                        ) : (
                          <Alert type="info" message="暂无行程安排" showIcon />
                        )}
                      </Collapse>
                    </TabPane>
                    <TabPane tab="餐厅" key="restaurants">
                      <Card title={<Space><ShopOutlined /><span>推荐餐厅</span></Space>} size="small" className="glass-card">
                        <List
                          size="small"
                          dataSource={Array.isArray(currentPlan.restaurants) ? currentPlan.restaurants : []}
                          renderItem={(restaurant: any) => (
                            <List.Item style={{ padding: '12px 0' }}>
                              <RestaurantCard restaurant={restaurant} />
                            </List.Item>
                          )}
                        />
                      </Card>
                    </TabPane>
                    <TabPane tab="酒店" key="hotel">
                      <Card title={<Space><ShopOutlined /><span>酒店信息</span></Space>} size="small" className="glass-card">
                        {currentPlan.hotel ? (
                          <Card size="small" className="glass-card">
                            <Row gutter={[8, 8]} align="middle">
                              <Col span={24}>
                                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                                  <Row justify="space-between" align="middle">
                                    <Col>
                                      <Text strong style={{ fontSize: '14px' }}>{currentPlan.hotel.name || currentPlan.hotel.hotel_name}</Text>
                                    </Col>
                                    <Col>
                                      <Space size={4}>
                                        <Rate disabled defaultValue={currentPlan.hotel.rating || 0} style={{ fontSize: '12px' }} />
                                        <Text type="secondary" style={{ fontSize: '12px' }}>
                                          {currentPlan.hotel.rating ? currentPlan.hotel.rating.toFixed(1) : 'N/A'}
                                        </Text>
                                      </Space>
                                    </Col>
                                  </Row>
                                  {currentPlan.hotel.address && (
                                    <Text type="secondary" style={{ fontSize: '11px' }}>
                                      <EnvironmentOutlined style={{ marginRight: '4px' }} /> {currentPlan.hotel.address}
                                    </Text>
                                  )}
                                  <Row gutter={[8, 2]}>
                                    {currentPlan.hotel.check_in && (
                                      <Col span={12}>
                                        <Text type="secondary" style={{ fontSize: '11px' }}>
                                          <ClockCircleOutlined style={{ marginRight: '2px' }} /> 入住: {currentPlan.hotel.check_in}
                                        </Text>
                                      </Col>
                                    )}
                                    {currentPlan.hotel.check_out && (
                                      <Col span={12}>
                                        <Text type="secondary" style={{ fontSize: '11px' }}>
                                          退房: {currentPlan.hotel.check_out}
                                        </Text>
                                      </Col>
                                    )}
                                  </Row>
                                  <Row justify="space-between" align="middle">
                                    <Col>
                                      <Space size={4}>
                                        <DollarOutlined style={{ fontSize: '12px', color: '#52c41a' }} />
                                        <Text style={{ fontSize: '12px', color: '#52c41a' }}>
                                          {formatPrice(currentPlan.hotel)}
                                        </Text>
                                      </Space>
                                    </Col>
                                    {currentPlan.hotel.phone && (
                                      <Col>
                                        <Space size={4}>
                                          <PhoneOutlined style={{ fontSize: '12px', color: '#1890ff' }} />
                                          <Text style={{ fontSize: '11px' }}>
                                            {currentPlan.hotel.phone}
                                          </Text>
                                        </Space>
                                      </Col>
                                    )}
                                  </Row>
                                  {ensureArray(currentPlan.hotel.amenities).length > 0 && (
                                    <Space direction="vertical" size={2}>
                                      <Text type="secondary" style={{ fontSize: '11px' }}>设施服务</Text>
                                      <LimitedTagList
                                        items={ensureArray(currentPlan.hotel.amenities)}
                                        color="cyan"
                                        max={8}
                                        tagStyle={{ fontSize: 10 }}
                                      />
                                    </Space>
                                  )}
                                </Space>
                              </Col>
                            </Row>
                          </Card>
                        ) : (
                          <Text type="secondary">暂无酒店信息</Text>
                        )}

                        {Array.isArray(currentPlan.hotel?.available_options) && currentPlan.hotel.available_options.length > 1 && (
                          <Card 
                            size="small" 
                            className="glass-card"
                            title={<Space><HomeOutlined /><span>更多酒店选择</span><Text type="secondary" style={{ fontSize: '12px' }}>({currentPlan.hotel.available_options.length}个选项)</Text></Space>}
                            style={{ marginTop: '12px' }}
                          >
                            <Row gutter={[8, 8]}>
                              {(showAllHotels 
                                ? currentPlan.hotel.available_options.slice(1) 
                                : currentPlan.hotel.available_options.slice(1, 6)
                              ).map((hotel: any, index: number) => (
                                <Col span={24} key={index}>
                                  <Card size="small" className="glass-card">
                                    <Row gutter={8} align="middle">
                                      <Col flex="60px">
                                        <div style={{
                                          width: '50px',
                                          height: '50px',
                                          backgroundColor: 'var(--overlay)',
                                          borderRadius: '4px',
                                          display: 'flex',
                                          alignItems: 'center',
                                          justifyContent: 'center'
                                        }}>
                                          <HomeOutlined style={{ color: 'var(--text-soft)', fontSize: '18px' }} />
                                        </div>
                                      </Col>
                                      <Col flex="auto">
                                        <Space direction="vertical" size={2} style={{ width: '100%' }}>
                                          <Row justify="space-between" align="middle">
                                            <Col>
                                              <Text strong style={{ fontSize: '13px' }}>{hotel.name || hotel.hotel_name}</Text>
                                            </Col>
                                            <Col>
                                              <Space size={4}>
                                                <Rate disabled defaultValue={hotel.rating || 0} style={{ fontSize: '12px' }} />
                                                {hotel.rating && (
                                                  <Text type="secondary" style={{ fontSize: '12px' }}>
                                                    {hotel.rating.toFixed(1)}
                                                  </Text>
                                                )}
                                              </Space>
                                            </Col>
                                          </Row>
                                          {hotel.address && (
                                            <Text type="secondary" style={{ fontSize: '11px' }}>
                                              <EnvironmentOutlined style={{ marginRight: '4px' }} /> {hotel.address}
                                            </Text>
                                          )}
                                          <Row justify="space-between" align="middle">
                                            <Col>
                                              <Space size={4}>
                                                <DollarOutlined style={{ fontSize: '12px', color: '#52c41a' }} />
                                                <Text style={{ fontSize: '12px', color: '#52c41a' }}>
                                                  {formatPrice(hotel)}
                                                </Text>
                                              </Space>
                                            </Col>
                                            {hotel.phone && (
                                              <Col>
                                                <Space size={4}>
                                                  <PhoneOutlined style={{ fontSize: '12px', color: '#1890ff' }} />
                                                  <Text style={{ fontSize: '11px' }}>
                                                    {hotel.phone}
                                                  </Text>
                                                </Space>
                                              </Col>
                                            )}
                                          </Row>
                                          {ensureArray(hotel.amenities).length > 0 && (
                                            <Space direction="vertical" size={2}>
                                              <Text type="secondary" style={{ fontSize: '11px' }}>设施服务</Text>
                                              <LimitedTagList
                                                items={ensureArray(hotel.amenities)}
                                                color="cyan"
                                                max={6}
                                                tagStyle={{ fontSize: 10 }}
                                              />
                                            </Space>
                                          )}
                                        </Space>
                                      </Col>
                                    </Row>
                                  </Card>
                                </Col>
                              ))}
                            </Row>
                            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '8px' }}>
                              <Button type="link" size="small" onClick={() => setShowAllHotels(!showAllHotels)} style={{ fontSize: '11px', padding: '0' }}>
                                {showAllHotels 
                                  ? '收起酒店选项' 
                                  : `展开查看剩余 ${currentPlan.hotel.available_options.length - 6} 个酒店选项`}
                              </Button>
                            </div>
                          </Card>
                        )}
                      </Card>
                    </TabPane>
                    
                    <TabPane tab="航班" key="flight">
                      <Card title="航班信息" size="small">
                        {currentPlan.flight ? (
                          <Space direction="vertical" size="small" style={{ width: '100%' }}>
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
                            <Row>
                              <Text>
                                <strong>航空公司:</strong> {currentPlan.flight.airline_name || currentPlan.flight.airline || 'N/A'}
                              </Text>
                            </Row>
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
                            <Row style={{ marginTop: '8px' }}>
                              <Col>
                                <Text type="secondary" style={{ fontSize: '12px' }}>
                                  飞行时长：{currentPlan.flight.duration || 'N/A'}
                                </Text>
                              </Col>
                              <Col style={{ marginLeft: '16px' }}>
                                <Text type="secondary" style={{ fontSize: '12px' }}>
                                  {currentPlan.flight.stops === 0 ? '直飞' : 
                                    currentPlan.flight.stops ? `${currentPlan.flight.stops}次中转` : 'N/A'}
                                </Text>
                              </Col>
                            </Row>
                            <Row justify="space-between" align="middle" style={{ 
                              padding: '8px 12px', 
                              backgroundColor: 'rgba(82, 196, 26, 0.12)', 
                              borderRadius: '6px',
                              border: '1px solid var(--border-soft)'
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
                    </TabPane>
                    <TabPane tab="地图" key="map">
                      <MapComponent 
                        destination={currentPlan?.destination || planDetail?.destination}
                        latitude={currentPlan.destination_info?.latitude || 39.9042}
                        longitude={currentPlan.destination_info?.longitude || 116.4074}
                        title="目的地地图"
                      />
                    </TabPane>
                  </Tabs>
                </Card>
              </Col>
              
              <Col xs={24} lg={8}>
                <Space direction="vertical" size="large" style={{ width: '100%' }}>
                  {/* 笔记精选 / 图片速览 */}
                  <Card title="笔记精选 / 图片速览" size="small">
                    {Array.isArray(currentPlan.xiaohongshu_notes) && currentPlan.xiaohongshu_notes.length > 0 ? (
                      <Space direction="vertical" size="small" style={{ width: '100%' }}>
                        <Row gutter={[8, 8]}>
                          {currentPlan.xiaohongshu_notes.slice(0, 8).map((note: any, idx: number) => (
                            <Col xs={12} sm={12} md={12} lg={12} key={idx}>
                              <div style={{ position: 'relative', border: '1px solid var(--border-soft)', borderRadius: 6, overflow: 'hidden', background: 'var(--overlay)' }}>
                                <a href={note.url} target="_blank" rel="noopener noreferrer" style={{ display: 'block' }}>
                                  {note.img_urls && note.img_urls.length > 0 ? (
                                    <img src={buildApiUrl(`/proxy/image?url=${encodeURIComponent(note.img_urls[0])}`)} alt={note.title || '小红书笔记'} style={{ width: '100%', height: 120, objectFit: 'cover', display: 'block' }} />
                                  ) : (
                                    <div style={{ height: 120, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-soft)' }}>无图片</div>
                                  )}
                                </a>
                                <div style={{ padding: '6px 8px' }}>
                                  <Text style={{ fontSize: '12px' }} ellipsis={{ tooltip: note.title }}>{note.title || '无标题'}</Text>
                                  <div style={{ marginTop: 4 }}>
                                    {(note.tag_list || []).slice(0, 2).map((tag: string, tIdx: number) => (
                                      <Tag key={tIdx} color="blue" style={{ fontSize: '10px', marginRight: 4 }}>{tag}</Tag>
                                    ))}
                                  </div>
                                  <div style={{ marginTop: 4, display: 'flex', justifyContent: 'space-between' }}>
                                    <Text style={{ fontSize: '10px', color: '#ffd666' }}>👍 {note.liked_count || 0}</Text>
                                    {note.url && (
                                      <a href={note.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: '10px' }}>打开笔记</a>
                                    )}
                                  </div>
                                </div>
                              </div>
                            </Col>
                          ))}
                        </Row>
                      </Space>
                    ) : (
                      <Text type="secondary" style={{ fontSize: '12px' }}>暂无笔记数据</Text>
                    )}
                  </Card>

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

                  {/* 新增：用户评分 */}
                  <Card title="用户评分" size="small">
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      <Row justify="space-between" align="middle">
                        <Col>
                          <Text>平均分</Text>
                        </Col>
                        <Col>
                          <Space>
                            <Rate disabled value={ratingSummary?.average ? Math.round(ratingSummary.average) : 0} />
                            <Text>{ratingSummary ? ratingSummary.average.toFixed(1) : 'N/A'}</Text>
                            <Text type="secondary">({ratingSummary?.count || 0} 人评分)</Text>
                          </Space>
                        </Col>
                      </Row>
                      <Divider style={{ margin: '8px 0' }} />
                      <Text strong>你的评分</Text>
                      <Rate 
                        disabled={isPublicView}
                        value={myRating.score || 0} 
                        onChange={(value) => setMyRating(prev => ({ ...prev, score: value }))} 
                      />
                      <Input.TextArea 
                        disabled={isPublicView}
                        value={myRating.comment} 
                        onChange={(e) => setMyRating(prev => ({ ...prev, comment: e.target.value }))} 
                        rows={3} 
                        placeholder="写下你的评价（可选）" 
                      />
                      {!isPublicView && (
                        <Button type="primary" onClick={submitRating} loading={submittingRating}>提交评分</Button>
                      )}

                      {recentRatings && recentRatings.length > 0 && (
                        <>
                          <Divider style={{ margin: '8px 0' }} />
                          <List
                            size="small"
                            header={<Text type="secondary">最近评分</Text>}
                            dataSource={recentRatings}
                            renderItem={(rt: any) => (
                              <List.Item>
                                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                                  <Space>
                                    <Rate disabled value={rt.score} style={{ fontSize: 14 }} />
                                    <Text>{rt.score}</Text>
                                    {rt.created_at && (
                                      <Text type="secondary" style={{ fontSize: 12 }}>
                                        {new Date(rt.created_at).toLocaleString()}
                                      </Text>
                                    )}
                                  </Space>
                                  {rt.comment && (
                                    <Text type="secondary" style={{ fontSize: 12 }}>{rt.comment}</Text>
                                  )}
                                </Space>
                              </List.Item>
                            )}
                          />
                        </>
                      )}
                    </Space>
                  </Card>

                  {/* 天气信息 */}
                  {currentPlan.weather_info && (
                    <Card className="glass-card weather-card" title={
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
                            {Array.isArray(currentPlan.weather_info.raw_data.forecast) && currentPlan.weather_info.raw_data.forecast.length > 0 && (
                              <div style={{ marginBottom: '12px' }}>
                                {currentPlan.weather_info.raw_data.forecast.map((day: any, index: number) => (
                                  <div key={index} className={`forecast-item ${getWeatherClass(day.dayweather || '')} ${index === 0 ? 'highlight' : ''}`}>
                                    <Row justify="space-between" align="middle">
                                      <Col span={8}>
                                        <Text strong>
                                          {day.date} {day.week && `周${day.week}`}
                                        </Text>
                                      </Col>
                                      <Col span={8} style={{ textAlign: 'center' }}>
                                        <div>
                                          <Text type="secondary" style={{ fontSize: '12px' }}>
                                            {day.dayweather}
                                          </Text>
                                          {day.nightweather && day.nightweather !== day.dayweather && (
                                            <Text type="secondary" style={{ fontSize: '12px' }}>
                                              转{day.nightweather}
                                            </Text>
                                          )}
                                        </div>
                                      </Col>
                                      <Col span={8} style={{ textAlign: 'right' }}>
                                        <Text strong>
                                          {day.daytemp}°
                                        </Text>
                                        <Text style={{ margin: '0 4px' }}>
                                          /
                                        </Text>
                                        <Text>
                                          {day.nighttemp}°
                                        </Text>
                                      </Col>
                                    </Row>
                                    {(day.daywind || day.daypower) && (
                                      <Row style={{ marginTop: '4px' }}>
                                        <Text type="secondary" style={{ fontSize: '11px' }}>
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
                              <div className={`forecast-item ${getWeatherClass(currentPlan.weather_info.raw_data.weather || '')}`} style={{ marginTop: '8px' }}>
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
                        {Array.isArray(currentPlan.weather_info.travel_recommendations) && currentPlan.weather_info.travel_recommendations.length > 0 && (
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

                  {/* 推荐餐厅（已移至左侧“餐厅”子Tab，这里隐藏） */}
                  {false && (
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
                          <RestaurantCard restaurant={restaurant} />
                        </List.Item>
                      )}

                    />
                  </Card>
                  )}

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

        </Tabs>
      ) : (
        <Card style={{ textAlign: 'center', padding: '60px 20px' }}>
          <Alert
            message="暂无方案数据"
            description="该计划还没有生成方案，或者方案数据尚未加载完成。"
            type="info"
            showIcon
          />
        </Card>
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
            onClick={() => { setExportModalVisible(false); setTimeout(() => window.print(), 300); }}
          >
            打印导出 PDF（浏览器）
          </Button>
          <Button 
            block 
            size="large"
            onClick={() => { window.open(buildApiUrl(`/travel-plans/${id}/export?format=json`), '_blank'); setExportModalVisible(false); }}
          >
            导出为 JSON
          </Button>
        </Space>
      </Modal>

      {/* 分享模态框 */}
      <Modal
        title="分享方案"
        open={shareModalVisible}
        onCancel={() => setShareModalVisible(false)}
        footer={null}
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Text type="secondary">
            当前状态：{planDetail.is_public ? '公开' : '私密'}{planDetail.public_at ? `（公开于 ${new Date(planDetail.public_at).toLocaleString()}）` : ''}
          </Text>
          <Text>分享链接：</Text>
          <Space>
            <Input value={window.location.href} readOnly style={{ width: 360 }} />
            <Button
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(window.location.href);
                  message.success('链接已复制到剪贴板');
                } catch {
                  message.error('复制失败，请手动复制');
                }
              }}
            >
              复制链接
            </Button>
          </Space>

          <Divider style={{ margin: '12px 0' }} />

          <Space wrap>
            <Button
              icon={<ShareAltOutlined />}
              onClick={() => {
                const shareUrl = window.location.href;
                const title = planDetail?.destination ? `${planDetail.destination}旅行方案` : '旅行方案分享';
                try {
                  const canNativeShare = typeof (navigator as any).share === 'function' && (window as any).isSecureContext;
                  if (canNativeShare) {
                    Promise.resolve((navigator as any).share({ title, url: shareUrl }))
                      .catch(() => message.info('系统分享未完成或被取消'));
                  } else {
                    message.info('当前浏览器不支持系统分享，请使用下方方式');
                  }
                } catch {
                  message.info('系统分享不可用，请使用下方方式');
                }
              }}
            >
              系统分享（支持手机）
            </Button>

            <a
              href={`https://connect.qq.com/widget/shareqq/index.html?url=${encodeURIComponent(window.location.href)}&title=${encodeURIComponent(planDetail?.destination ? `${planDetail.destination}旅行方案` : '旅行方案分享')}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button icon={<ShareAltOutlined />}>分享到QQ</Button>
            </a>
          </Space>

          <Divider style={{ margin: '12px 0' }} />

          <Text>微信分享（扫码）：</Text>
          <Image
            width={180}
            height={180}
            src={`https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(window.location.href)}`}
            alt="微信扫码分享二维码"
            preview={false}
          />
        </Space>
      </Modal>
    </div>
  );
};

export default PlanDetailPage;
