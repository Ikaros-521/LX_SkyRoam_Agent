import React, { useEffect, useMemo, useState, useCallback, useRef } from 'react';
import { Card, Row, Col, Typography, Input, Space, Tag, Modal, List, Button, Spin, Empty, Carousel, Select, DatePicker, Image } from 'antd';
import { GlobalOutlined, SearchOutlined, EnvironmentOutlined, CalendarOutlined, DollarOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { buildApiUrl, API_ENDPOINTS } from '../../config/api';
import { authFetch } from '../../utils/auth';

// 懒加载图片组件（支持多候选路径）
interface LazyImageProps {
  candidates: string[]; // 图片候选路径列表（按优先级排序）
  fallback: string; // 最终fallback图片
  alt: string;
  height?: number;
  style?: React.CSSProperties;
  onError?: (e: React.SyntheticEvent<HTMLImageElement, Event>) => void;
  enablePreview?: boolean; // 是否启用预览功能
  onImageClick?: (e: React.MouseEvent) => void; // 图片点击事件（用于阻止冒泡）
}

const LazyImage: React.FC<LazyImageProps> = ({ candidates, fallback, alt, height, style, onError, enablePreview = false, onImageClick }) => {
  const [isInView, setIsInView] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [imgSrc, setImgSrc] = useState<string | null>(null);
  const [hasError, setHasError] = useState(false);
  const imgRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsInView(true);
            observer.disconnect();
          }
        });
      },
      {
        rootMargin: '50px', // 提前50px开始加载
      }
    );

    const currentRef = imgRef.current;
    if (currentRef) {
      observer.observe(currentRef);
    }

    return () => {
      if (currentRef) {
        observer.unobserve(currentRef);
      }
      observer.disconnect();
    };
  }, []);

  // 当进入视口时，开始尝试加载图片
  useEffect(() => {
    if (!isInView || imgSrc) return; // 如果已经加载成功，不再尝试

    // 合并所有候选路径和fallback
    const allCandidates = [...candidates, fallback];
    const currentSrc = allCandidates[currentIndex];

    if (!currentSrc) {
      setHasError(true);
      return;
    }

    // 尝试加载当前候选
    const img = new window.Image();
    let cancelled = false;
    
    img.onload = () => {
      if (!cancelled) {
        setImgSrc(currentSrc);
      }
    };
    img.onerror = () => {
      if (!cancelled) {
        // 当前候选失败，尝试下一个
        if (currentIndex < allCandidates.length - 1) {
          setCurrentIndex(currentIndex + 1);
        } else {
          // 所有候选都失败
          setHasError(true);
        }
      }
    };
    img.src = currentSrc;

    return () => {
      cancelled = true;
    };
  }, [isInView, currentIndex, candidates, fallback, imgSrc]);

  const handleImageError = (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
    const allCandidates = [...candidates, fallback];
    // 如果当前图片加载失败，尝试下一个候选
    if (currentIndex < allCandidates.length - 1) {
      setImgSrc(null); // 重置
      setCurrentIndex(currentIndex + 1); // 尝试下一个
    } else {
      // 所有候选都失败
      setHasError(true);
      if (onError) {
        onError(e);
      }
    }
  };

  const allCandidates = [...candidates, fallback];
  const currentSrc = imgSrc || (currentIndex < allCandidates.length ? allCandidates[currentIndex] : null);

  // 分离容器样式和图片样式
  const { objectFit, borderTopLeftRadius, borderTopRightRadius, borderRadius, ...restStyle } = style || {};
  
  const containerStyle: React.CSSProperties = {
    height,
    width: '100%',
    overflow: 'hidden',
    position: 'relative',
    ...restStyle,
  };

  const imageStyle: React.CSSProperties = {
    width: '100%',
    height: '100%',
    objectFit: objectFit || 'cover',
    display: 'block',
    borderTopLeftRadius: borderTopLeftRadius,
    borderTopRightRadius: borderTopRightRadius,
    borderRadius: borderRadius,
  };

  return (
    <div ref={imgRef} style={containerStyle}>
      {hasError ? (
        <div style={{ height, background: '#f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%' }}>
          <Text type="secondary">图片加载失败</Text>
        </div>
      ) : currentSrc && imgSrc ? (
        enablePreview ? (
          <div 
            onClick={(e) => {
              e.stopPropagation(); // 阻止事件冒泡到卡片
            }}
            style={{ 
              width: '100%', 
              height: '100%', 
              display: 'block', 
              position: 'relative',
              overflow: 'hidden'
            }}
            className="destination-image-container"
          >
            <Image
              src={imgSrc}
              alt={alt}
              height={height}
              style={{ 
                width: '100%',
                height: '100%',
                display: 'block',
                ...imageStyle
              }}
              preview={{
                src: imgSrc,
                mask: <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#fff', fontSize: '14px' }}>点击预览</div>
              }}
              onError={handleImageError}
            />
          </div>
        ) : (
          <img
            src={imgSrc}
            alt={alt}
            style={imageStyle}
            onError={handleImageError}
            onClick={(e) => {
              e.stopPropagation(); // 阻止事件冒泡
              if (onImageClick) {
                onImageClick(e);
              }
            }}
          />
        )
      ) : (
        <div style={{ height, background: '#f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%' }}>
          <Spin size="small" />
        </div>
      )}
    </div>
  );
};

const { Title, Paragraph, Text } = Typography;

interface Destination {
  id?: number | null; // 动态生成的目的地可能没有ID
  name: string;
  country?: string | null;
  city?: string | null;
  region?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  timezone?: string | null;
  description?: string | null;
  highlights?: string[] | null;
  best_time_to_visit?: string | null;
  popularity_score?: number;
  cost_level?: string | null; // low, medium, high
  images?: string[] | null;
  continent?: string; // 新增：洲别（亚洲、欧洲、美洲、大洋洲、非洲）
  plan_count?: number; // 来自旅行计划的数量
  source?: 'database' | 'travel_plans'; // 数据来源
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
  source?: 'private' | 'public';
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

// 根据国家推断大洲
const getContinentFromCountry = (country?: string | null): string | undefined => {
  if (!country) return undefined;
  const c = country.toLowerCase();
  // 亚洲
  if (['中国', '日本', '韩国', '印度', '泰国', '新加坡', '马来西亚', '印度尼西亚', '菲律宾', '越南', '缅甸', '柬埔寨', '老挝', '蒙古', '尼泊尔', '不丹', '斯里兰卡', '马尔代夫', '孟加拉国', '巴基斯坦', '阿富汗', '伊朗', '伊拉克', '沙特阿拉伯', '阿联酋', '土耳其', '以色列', '约旦', '黎巴嫩', '叙利亚', '也门', '阿曼', '科威特', '卡塔尔', '巴林'].some(n => c.includes(n.toLowerCase()))) {
    return '亚洲';
  }
  // 欧洲
  if (['英国', '法国', '德国', '意大利', '西班牙', '葡萄牙', '荷兰', '比利时', '瑞士', '奥地利', '希腊', '瑞典', '挪威', '丹麦', '芬兰', '冰岛', '爱尔兰', '波兰', '捷克', '匈牙利', '罗马尼亚', '保加利亚', '克罗地亚', '塞尔维亚', '俄罗斯'].some(n => c.includes(n.toLowerCase()))) {
    return '欧洲';
  }
  // 美洲
  if (['美国', '加拿大', '墨西哥', '巴西', '阿根廷', '智利', '秘鲁', '哥伦比亚', '委内瑞拉', '厄瓜多尔', '玻利维亚', '巴拉圭', '乌拉圭', '古巴', '牙买加', '巴哈马', '哥斯达黎加', '巴拿马'].some(n => c.includes(n.toLowerCase()))) {
    return '美洲';
  }
  // 大洋洲
  if (['澳大利亚', '新西兰', '斐济', '巴布亚新几内亚', '汤加', '萨摩亚'].some(n => c.includes(n.toLowerCase()))) {
    return '大洋洲';
  }
  // 非洲
  if (['南非', '埃及', '肯尼亚', '摩洛哥', '坦桑尼亚', '埃塞俄比亚', '加纳', '尼日利亚', '塞内加尔', '毛里求斯'].some(n => c.includes(n.toLowerCase()))) {
    return '非洲';
  }
  return undefined;
};

const DestinationsPage: React.FC = () => {
  const navigate = useNavigate();
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState<string>('');
  const [filterContinent, setFilterContinent] = useState<string>('全部');
  const regionColor = (region?: string): string => {
    const r = (region || '').toLowerCase();
    if (!r) return 'default';
    if (r.includes('华北') || r.includes('north')) return 'geekblue';
    if (r.includes('华东') || r.includes('east')) return 'blue';
    if (r.includes('华南') || r.includes('south')) return 'cyan';
    if (r.includes('西南') || r.includes('southwest')) return 'green';
    if (r.includes('西北') || r.includes('northwest')) return 'gold';
    if (r.includes('华中') || r.includes('central')) return 'volcano';
    if (r.includes('东北') || r.includes('northeast')) return 'purple';
    return 'default';
  };
  const costLevelColor = (level?: string): string => {
    const v = (level || '').toLowerCase();
    if (!v) return 'default';
    if (v.includes('低') || v.includes('low')) return 'green';
    if (v.includes('高') || v.includes('high')) return 'volcano';
    if (v.includes('中') || v.includes('medium')) return 'gold';
    return 'orange';
  };

  // 相关方案弹窗
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [activeDest, setActiveDest] = useState<Destination | null>(null);
  const [plansLoading, setPlansLoading] = useState<boolean>(false);
  const [plans, setPlans] = useState<TravelPlan[]>([]);
  const [planQ, setPlanQ] = useState<string>('');
  const planQRef = useRef<string>(''); // 使用 ref 存储最新的 planQ，避免闭包问题
  const [planQInput, setPlanQInput] = useState<string>(''); // 本地输入状态，避免输入时触发过滤
  const [planMinScore, setPlanMinScore] = useState<number | undefined>(undefined);
  const [planDateRange, setPlanDateRange] = useState<any[]>([]);
  const [planStatus, setPlanStatus] = useState<string>('全部');
  const [planSource, setPlanSource] = useState<'全部' | 'private' | 'public'>('全部');
  
  // 同步 planQ 到 ref
  useEffect(() => {
    planQRef.current = planQ;
  }, [planQ]);

  useEffect(() => {
    const fetchDestinations = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await authFetch(buildApiUrl(`${API_ENDPOINTS.DESTINATIONS}?include_from_plans=true&limit=200`));
      if (!res.ok) throw new Error(`加载目的地失败 (${res.status})`);
      const data = await res.json();
      const list = Array.isArray(data) ? data : [];
      // 为没有 continent 的目的地推断大洲
      const enrichedList = list.map((d: Destination) => ({
        ...d,
        continent: d.continent || getContinentFromCountry(d.country),
        // 为动态生成的目的地生成一个临时ID（基于名称的哈希）
        id: d.id || (d.name ? Math.abs(d.name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)) : 0)
      }));
      // 合并默认目的地（如果数据库中没有）
      const missingDefaults = DEFAULT_DESTINATIONS.filter(d => 
        !enrichedList.some(ed => ed.name.toLowerCase() === d.name.toLowerCase())
      );
      setDestinations(enrichedList.length ? [...enrichedList, ...missingDefaults] : DEFAULT_DESTINATIONS);
    } catch (e: any) {
      setError(e.message || '加载目的地失败，显示默认热门目的地');
      setDestinations(DEFAULT_DESTINATIONS);
    } finally {
      setLoading(false);
    }
    };
    fetchDestinations();
  }, []);

  // 获取方案列表的函数
  const fetchPlansData = useCallback(async (keywordOverride?: string) => {
    if (!activeDest) return;
    const d = activeDest;
    setPlansLoading(true);
    try {
      let listPrivate: TravelPlan[] = [];
      let listPublic: TravelPlan[] = [];

      // 优先使用传入的 keyword，如果没有传入则使用 ref 中的最新值，避免闭包问题
      const keywordToUse = keywordOverride !== undefined ? keywordOverride : planQRef.current;
      
      // 构建查询参数（私有方案）
      const buildPrivateParams = (baseParams: string) => {
        const params = new URLSearchParams(baseParams);
        if (keywordToUse && keywordToUse.trim()) {
          params.set('keyword', keywordToUse.trim());
        }
        if (typeof planMinScore === 'number') {
          params.set('min_score', String(planMinScore));
        }
        if (Array.isArray(planDateRange) && planDateRange.length === 2 && planDateRange[0] && planDateRange[1]) {
          const fromStr = dayjs(planDateRange[0]).format('YYYY-MM-DD');
          const toStr = dayjs(planDateRange[1]).format('YYYY-MM-DD');
          if (fromStr) params.set('travel_from', fromStr);
          if (toStr) params.set('travel_to', toStr);
        }
        if (planStatus && planStatus !== '全部') {
          params.set('status', planStatus);
        }
        return params.toString();
      };

      // 构建查询参数（公开方案，支持 destination 参数）
      const buildPublicParams = (baseParams: string) => {
        const params = new URLSearchParams(baseParams);
        const destName = (d.name || '').trim();
        if (destName) {
          params.set('destination', destName);
        }
        if (keywordToUse && keywordToUse.trim()) {
          params.set('keyword', keywordToUse.trim());
        }
        if (typeof planMinScore === 'number') {
          params.set('min_score', String(planMinScore));
        }
        if (Array.isArray(planDateRange) && planDateRange.length === 2 && planDateRange[0] && planDateRange[1]) {
          const fromStr = dayjs(planDateRange[0]).format('YYYY-MM-DD');
          const toStr = dayjs(planDateRange[1]).format('YYYY-MM-DD');
          if (fromStr) params.set('travel_from', fromStr);
          if (toStr) params.set('travel_to', toStr);
        }
        return params.toString();
      };

      if (planSource === 'private' || planSource === '全部') {
        const resPrivate = await authFetch(buildApiUrl(`${API_ENDPOINTS.TRAVEL_PLANS}?${buildPrivateParams('skip=0&limit=100')}`));
        if (!resPrivate.ok) throw new Error(`加载个人方案失败 (${resPrivate.status})`);
        const dataPrivate = await resPrivate.json();
        listPrivate = Array.isArray(dataPrivate?.plans) ? dataPrivate.plans : (Array.isArray(dataPrivate) ? dataPrivate : []);
      }

      if (planSource === 'public' || planSource === '全部') {
        const resPublic = await fetch(buildApiUrl(`${API_ENDPOINTS.TRAVEL_PLANS_PUBLIC}?${buildPublicParams('skip=0&limit=100')}`));
        if (!resPublic.ok) throw new Error(`加载公开方案失败 (${resPublic.status})`);
        const dataPublic = await resPublic.json();
        listPublic = Array.isArray(dataPublic?.plans) ? dataPublic.plans : (Array.isArray(dataPublic) ? dataPublic : []);
      }

      // 过滤逻辑：
      // 1. 公开方案：后端已经根据 destination 和 keyword 进行了过滤，前端不需要再次过滤
      // 2. 私有方案：
      //    - 如果有关键词搜索：后端已经根据关键词过滤，前端不再进行目的地过滤（避免过度过滤）
      //    - 如果没有关键词搜索：前端需要根据目的地名称进行过滤
      const targetName = (d.name || '').trim().toLowerCase();
      const cityName = (d.city || '').trim().toLowerCase();
      const matchByDestination = (p: TravelPlan) => {
        const dest = (p.destination || '').toLowerCase();
        return dest.includes(targetName) || (!!cityName && dest.includes(cityName));
      };

      // 私有方案：有关键词搜索时不进行目的地过滤，没有关键词搜索时才过滤
      const matchedPrivate = (keywordToUse && keywordToUse.trim()) 
        ? listPrivate.map((p) => ({ ...p, source: 'private' as const }))
        : listPrivate.filter(matchByDestination).map((p) => ({ ...p, source: 'private' as const }));
      
      // 公开方案不需要过滤（后端已经根据 destination 参数过滤了）
      const matchedPublic = listPublic.map((p) => ({ ...p, source: 'public' as const }));
      
      // 合并并去重
      const mergedMap = new Map<number, TravelPlan>();
      [...matchedPublic, ...matchedPrivate].forEach((p) => mergedMap.set(p.id, p));
      setPlans(Array.from(mergedMap.values()));
    } catch (e) {
      setPlans([]);
    } finally {
      setPlansLoading(false);
    }
  }, [activeDest, planMinScore, planDateRange, planStatus, planSource]);

  // 根据来源和当前目的地重新获取方案列表（组件内部）
  useEffect(() => {
    if (!modalOpen || !activeDest) {
      // 弹窗关闭时重置搜索状态
      if (!modalOpen) {
        setPlanQ('');
        setPlanQInput('');
      }
      return;
    }
    // 初始加载和筛选条件变化时自动获取（使用当前的 planQ）
    // 注意：关键词搜索通过 onSearch 手动触发，不在这里自动触发
    fetchPlansData();
  }, [modalOpen, activeDest, planSource, planMinScore, planDateRange, planStatus, fetchPlansData]);

  const filteredDestinations = useMemo(() => {
    const keyword = q.trim().toLowerCase();
    
    let results = destinations;

    // 1. 按大洲筛选
    if (filterContinent !== '全部') {
      results = results.filter(d => {
        const continent = d.continent || getContinentFromCountry(d.country);
        return continent === filterContinent;
      });
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

  const openPlansModal = async (d: Destination) => {
    setActiveDest(d);
    setModalOpen(true);
    setPlansLoading(true);
    const destName = d.name || '';
    setPlanQ(destName);
    setPlanQInput(destName);
    setPlanMinScore(undefined);
    setPlanDateRange([]);
    setPlanStatus('全部');
    // 移除这里的请求，改为在 useEffect 中根据来源实时获取
  };

  // 不再需要客户端过滤，所有过滤都在后端完成
  const filteredPlans = plans;

  return (
    <div className="destinations-page" style={{ maxWidth: '1200px', margin: '0 auto' }}>
      <style>{`
        .destination-image-container .ant-image {
          width: 100% !important;
          height: 100% !important;
          display: block !important;
        }
        .destination-image-container .ant-image-img {
          width: 100% !important;
          min-width: 100% !important;
          height: 100% !important;
          object-fit: cover !important;
          display: block !important;
        }
      `}</style>
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
            return (
              <div key={d.id}>
                <Row gutter={16} align="middle">
                  <Col xs={24} md={10}>
                    <LazyImage
                       candidates={getAllImageCandidates(d)}
                       fallback={getFallbackImage(d)}
                       alt={d.name}
                       height={220}
                       style={{ objectFit: 'cover' }}
                     />
                  </Col>
                  <Col xs={24} md={14}>
                    <Space direction="vertical" size={6} style={{ width: '100%' }}>
                      <Title level={4} style={{ margin: 0 }}>{d.name}</Title>
                      <Text type="secondary"><EnvironmentOutlined /> {d.country || '未知'}{d.city ? ` · ${d.city}` : ''}</Text>
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
                        <Button onClick={() => {
                          const continent = d.continent || getContinentFromCountry(d.country) || '全部';
                          setFilterContinent(continent);
                        }}>同洲筛选</Button>
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
            return (
              <Col xs={24} sm={12} md={8} lg={6} key={d.id}>
                <Card
                  hoverable
                  className="glass-card"
                  style={{ borderRadius: 12, overflow: 'hidden' }}
                  cover={(
                    <LazyImage
                      candidates={getAllImageCandidates(d)}
                      fallback={getFallbackImage(d)}
                      alt={d.name}
                      height={160}
                      style={{ objectFit: 'cover', borderTopLeftRadius: 12, borderTopRightRadius: 12, borderRadius: 0 }}
                      enablePreview={true}
                    />
                  )}
                >
                  <Space 
                    direction="vertical" 
                    size={6} 
                    style={{ width: '100%', cursor: 'pointer' }}
                    onClick={() => openPlansModal(d)}
                  >
                    <Title level={4} style={{ margin: 0 }}>{d.name}</Title>
                    <Text>
                      <EnvironmentOutlined /> {d.country || '未知'}{d.city ? ` · ${d.city}` : ''}
                    </Text>
                    <Space wrap>
                      {d.region && <Tag color={regionColor(d.region)}>{d.region}</Tag>}
                      {d.cost_level && <Tag color={costLevelColor(d.cost_level)}>消费：{d.cost_level}</Tag>}
                      {typeof d.popularity_score === 'number' && <Tag color="blue">热度：{Math.round(d.popularity_score)}</Tag>}
                      {d.plan_count && d.plan_count > 0 && <Tag color="green">{d.plan_count} 个方案</Tag>}
                      {d.source === 'travel_plans' && <Tag color="orange">热门</Tag>}
                    </Space>
                    {d.best_time_to_visit && (
                      <Text><CalendarOutlined /> 最佳旅行时间：{d.best_time_to_visit}</Text>
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
              value={planQInput}
              onChange={(e) => setPlanQInput(e.target.value)}
              onSearch={(v) => {
                const trimmed = (v || planQInput).trim();
                setPlanQ(trimmed);
                setPlanQInput(trimmed);
                // 点击搜索时调用后端接口
                fetchPlansData(trimmed);
              }}
              enterButton
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
            <Select
              placeholder="来源"
              allowClear
              style={{ width: 140 }}
              value={planSource === '全部' ? undefined : planSource}
              onChange={(v) => setPlanSource((v as 'private' | 'public') || '全部')}
              options={[
                { value: 'private', label: '仅自己' },
                { value: 'public', label: '仅公开' },
              ]}
            />
            <Button onClick={() => { 
              setPlanQ(''); 
              setPlanQInput(''); 
              setPlanMinScore(undefined); 
              setPlanDateRange([]); 
              setPlanStatus('全部'); 
              setPlanSource('全部'); 
            }}>
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
                <Card className="glass-card">
                  <Space direction="vertical" size={6} style={{ width: '100%' }}>
                    <Title level={5} style={{ margin: 0 }}>目的地概览</Title>
                    {activeDest.description && (
                      <Paragraph>{activeDest.description}</Paragraph>
                    )}
                    {Array.isArray(activeDest.highlights) && activeDest.highlights.length > 0 && (
                      <>
                        <Text>热门景点：</Text>
                        <Space wrap>
                          {activeDest.highlights.map((h) => (
                            <Tag key={h}>{h}</Tag>
                          ))}
                        </Space>
                      </>
                    )}
                    <Space>
                      <Button type="primary" onClick={() => navigate('/plan')}>去创建方案</Button>
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
                  <Card hoverable className="glass-card dest-plan-card" style={{ width: '100%' }} bodyStyle={{ padding: 12 }}>
                    <Row gutter={12} align="middle">
                      <Col flex="auto">
                        <Space direction="vertical" size={4}>
                          <Text strong ellipsis style={{ fontSize: 16 }}>{p.title}</Text>
                          <Text ellipsis>
                            <EnvironmentOutlined /> {p.destination} · {dayjs(p.start_date).format('YYYY-MM-DD')} ~ {dayjs(p.end_date).format('YYYY-MM-DD')}
                          </Text>
                          <Space wrap>
                              {(() => {
                                const statusMap = {
                                  draft: { color: 'default', text: '草稿' },
                                  generating: { color: 'processing', text: '生成中' },
                                  completed: { color: 'success', text: '已完成' },
                                  failed: { color: 'error', text: '失败' },
                                  archived: { color: 'default', text: '已归档' },
                                } as Record<string, { color: string; text: string }>;
                                const cfg = statusMap[p.status] || { color: 'default', text: p.status };
                                return <Tag color={cfg.color}>状态：{cfg.text}</Tag>;
                              })()}
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

// 将目的地名称转换为文件名（支持中文）
const toImageFileName = (name: string): string => {
  return name.trim();
};

// 生成图片匹配候选列表（支持部分匹配）
// 例如："杭州西湖" -> ["杭州西湖", "杭州", "西湖"]
const generateImageCandidates = (name: string, city?: string | null): string[] => {
  const candidates: string[] = [];
  const trimmed = name.trim();
  
  if (!trimmed) return candidates;
  
  // 1. 完整名称（最高优先级）
  candidates.push(trimmed);
  
  // 2. 如果名称长度大于2，尝试提取关键词
  if (trimmed.length > 2) {
    // 2.1 提取前2个字符（常见城市名，如"杭州"、"北京"）
    const firstTwo = trimmed.substring(0, 2);
    if (firstTwo.length === 2 && !candidates.includes(firstTwo)) {
      candidates.push(firstTwo);
    }
    
    // 2.2 如果名称长度>=4，尝试提取后2个字符（如"西湖"）
    if (trimmed.length >= 4) {
      const lastTwo = trimmed.substring(trimmed.length - 2);
      if (lastTwo.length === 2 && !candidates.includes(lastTwo)) {
        candidates.push(lastTwo);
      }
    }
    
    // 2.3 如果名称包含常见分隔符或关键词，尝试提取
    // 例如："杭州西湖" 可以提取 "杭州" 和 "西湖"
    // 这里我们优先使用前2个字符，因为城市名通常在前面
  }
  
  // 3. 如果提供了城市名，且与名称不同，也加入候选
  if (city && city.trim()) {
    const cityTrimmed = city.trim();
    if (cityTrimmed !== trimmed && !candidates.includes(cityTrimmed)) {
      candidates.push(cityTrimmed);
    }
  }
  
  return candidates;
};

// 获取所有候选图片路径（用于按顺序尝试加载）
const getAllImageCandidates = (d: Destination): string[] => {
  const candidates = generateImageCandidates(d.name, d.city);
  return candidates.map(candidate => 
    `/static/images/destinations/${encodeURIComponent(candidate)}.jpg`
  );
};

// 获取备用图片（优先级：API返回的图片 > 部分匹配的图片 > 随机图片）
const getFallbackImage = (d: Destination): string => {
  // 优先使用 API 返回的图片
  const imgs = Array.isArray(d.images) ? d.images : [];
  const first = imgs.find((u) => typeof u === 'string' && u.length > 0);
  if (first) {
    return first;
  }
  
  // 尝试部分匹配的图片（跳过第一个，因为第一个已经在主路径中尝试过了）
  const candidates = generateImageCandidates(d.name, d.city);
  if (candidates.length > 1) {
    // 这里返回第二个候选，实际加载时会通过 onError 依次尝试
    return `/static/images/destinations/${encodeURIComponent(candidates[1])}.jpg`;
  }
  
  // 最后使用随机图片作为兜底
  const fileName = toImageFileName(d.name);
  return `https://picsum.photos/seed/${encodeURIComponent(fileName)}/800/600`;
};
