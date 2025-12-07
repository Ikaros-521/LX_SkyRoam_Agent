"""
旅行方案生成服务
"""

from typing import List, Dict, Any, Optional, Callable, Set, Tuple
from datetime import datetime, timedelta
from types import SimpleNamespace
from dataclasses import dataclass, field
import copy
from loguru import logger
import random
import json
import asyncio
import time
import traceback
from functools import wraps
from app.tools.openai_client import openai_client
from app.core.config import settings
from app.services.plan_generation import (
    calculate_date,
    extract_price_value,
    generate_daily_entries,
    build_simple_attraction_plan,
    build_simple_dining_plan,
    build_simple_transportation_plan,
    build_simple_accommodation_day,
    get_day_entry_from_list,
)

DOMESTIC_KEYWORDS_CN = {
    "中国",
    "大陆",
    "内地",
    "北京",
    "上海",
    "广州",
    "深圳",
    "杭州",
    "南京",
    "苏州",
    "成都",
    "重庆",
    "西安",
    "武汉",
    "长沙",
    "厦门",
    "青岛",
    "三亚",
    "海口",
    "拉萨",
    "乌鲁木齐",
}

DOMESTIC_KEYWORDS_EN = {
    "beijing",
    "shanghai",
    "guangzhou",
    "shenzhen",
    "hangzhou",
    "suzhou",
    "nanjing",
    "chengdu",
    "chongqing",
    "wuhan",
    "xiamen",
    "sanya",
    "urumqi",
    "xi'an",
    "xian",
    "qingdao",
    "haikou",
    "lhasa",
    "china",
    "prc",
}

try:
    from dateutil import parser as date_parser
except ImportError:  # pragma: no cover
    date_parser = None

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
    """重试装饰器，支持指数退避"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # 检查是否是API限速错误
                    error_msg = str(e).lower()
                    is_rate_limit = any(keyword in error_msg for keyword in [
                        'rate limit', 'too many requests', '429', 'quota exceeded'
                    ])
                    
                    if attempt < max_retries - 1:
                        # 计算退避延迟
                        if is_rate_limit:
                            delay = min(base_delay * (2 ** attempt) * 2, max_delay)  # 限速错误延迟更长
                        else:
                            delay = min(base_delay * (2 ** attempt), max_delay)
                        
                        logger.warning(f"第{attempt + 1}次调用失败: {e}, {delay:.1f}秒后重试")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"重试{max_retries}次后仍然失败: {e}")
            
            raise last_exception
        return wrapper
    return decorator


@dataclass
class PlanSegmentContext:
    total_days: int
    remaining_days: int
    remaining_budget: Optional[float]
    used_attractions: Set[str] = field(default_factory=set)
    used_restaurants: Set[str] = field(default_factory=set)
    used_transport: Set[str] = field(default_factory=set)


class PlanGenerator:
    """方案生成器"""
    
    def __init__(self):
        # 最大可生成的完整方案数量（全局上限）
        self.max_plans = 5
        # 按天的景点数量控制，默认值可通过 settings 覆盖，便于根据业务调节
        self.min_attractions_per_day = int(
            getattr(settings, "PLAN_MIN_ATTRACTIONS_PER_DAY", 2)
        )
        self.max_attractions_per_day = int(
            getattr(settings, "PLAN_MAX_ATTRACTIONS_PER_DAY", 4)
        )
        # 单日用餐次数 / 单次行程的酒店候选数量
        self.min_meals_per_day = int(
            getattr(settings, "PLAN_MIN_MEALS_PER_DAY", 3)
        )
        self.max_hotels_per_trip = int(
            getattr(settings, "PLAN_MAX_HOTELS_PER_TRIP", 5)
        )

        # 是否根据数据丰富度动态调整“备选方案数量”
        self.dynamic_plan_count_enabled: bool = bool(
            getattr(settings, "PLAN_DYNAMIC_PLAN_COUNT_ENABLED", True)
        )
        self.min_attraction_richness_for_multi_plans: float = float(
            getattr(settings, "PLAN_MIN_ATTRACTION_RICHNESS_FOR_MULTI_PLANS", 0.7)
        )

        self.max_segment_days = getattr(settings, "PLAN_MAX_SEGMENT_DAYS", 10)
        # 延迟导入避免循环依赖
        self._data_collector = None
        self._destination_scope_cache: Dict[str, str] = {}
    
    @property
    def data_collector(self):
        """延迟初始化data_collector"""
        if self._data_collector is None:
            from app.services.data_collector import DataCollector
            self._data_collector = DataCollector()
        return self._data_collector
    
    @staticmethod
    def _to_datetime(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                if date_parser:
                    return date_parser.parse(value)
                return datetime.fromisoformat(value)
            except Exception:
                return None
        return None
    
    async def generate_plans(
        self, 
        processed_data: Dict[str, Any], 
        plan: Any,
        preferences: Optional[Dict[str, Any]] = None,
        raw_data: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """生成多个旅行方案"""
        try:
            # logger.warning(f"preferences={preferences}")
            preferences = self._normalize_preferences(preferences)
            # logger.warning(f"_normalize_preferences(preferences)={preferences}")
            logger.info("开始生成旅行方案")

            destination_scope = await self._detect_destination_scope(plan)
            is_international = destination_scope == "international"
            processed_data = self._adjust_processed_data_for_scope(processed_data, is_international)
            if is_international:
                logger.info("目的地判定为海外，将降低高德餐饮/住宿权重，优先使用小红书数据")

            if getattr(plan, "duration_days", 0) > self.max_segment_days:
                logger.info(
                    f"旅行天数 {getattr(plan, 'duration_days', None)} 超过最大连续天数 {self.max_segment_days}，尝试分段生成"
                )
                segmented_plans = await self._generate_segmented_plans(
                    processed_data, plan, preferences, raw_data
                )
                if segmented_plans is not None:
                    return segmented_plans
            
            # 检查是否有多个偏好，决定使用拆分策略还是传统策略
            use_split_strategy = self._should_use_split_strategy(preferences)
            
            # 首先尝试使用LLM生成方案
            try:
                # 检查OpenAI配置
                if not openai_client.api_key:
                    logger.warning("OpenAI API密钥未配置，使用传统方法")
                    raise Exception("OpenAI API密钥未配置")
                
                # 根据偏好情况选择生成策略
                # if use_split_strategy:
                if False:
                    logger.info("使用拆分偏好策略生成方案")
                    # 设置超时
                    llm_plans = await asyncio.wait_for(
                        self._generate_plans_with_split_preferences(processed_data, plan, preferences, raw_data),
                        timeout=900.0  # 900秒超时，因为需要多次LLM调用
                    )
                else:
                    logger.info("使用传统LLM策略生成方案")
                    # 设置超时
                    llm_plans = await asyncio.wait_for(
                        self._generate_plans_with_llm(
                            processed_data,
                            plan,
                            preferences,
                            raw_data,
                            is_international=is_international,
                        ),
                        timeout=600.0  # 600秒超时
                    )
                
                if llm_plans:
                    logger.info(f"使用LLM生成了 {len(llm_plans)} 个旅行方案")
                    return llm_plans
                    
            except asyncio.TimeoutError:
                logger.warning("LLM调用超时，使用传统方法")
            except Exception as e:
                logger.warning(f"LLM生成方案失败，使用传统方法: {e}")
            
            # 降级到传统方法
            return await self._generate_traditional_plans(
                processed_data,
                plan,
                preferences,
                raw_data,
                is_international=is_international,
            )
            
        except Exception as e:
            logger.error(f"生成旅行方案失败: {e}")
            return []

    def _normalize_preferences(self, preferences: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """确保偏好字段存在并格式正确"""
        normalized = dict(preferences or {})

        def _set_default_list(key: str):
            value = normalized.get(key)
            if value is None:
                normalized[key] = []
            elif not isinstance(value, list):
                normalized[key] = [value]

        def _set_default_int(key: str, default: int = 1):
            value = normalized.get(key)
            if value is None:
                normalized[key] = default
                return
            try:
                normalized[key] = int(value)
            except (TypeError, ValueError):
                normalized[key] = default

        _set_default_int("travelers", 1)
        _set_default_list("ageGroups")
        _set_default_list("foodPreferences")
        _set_default_list("dietaryRestrictions")

        return normalized

    async def _detect_destination_scope(self, plan: Any) -> str:
        """通过规则+LLM判断目的地是国内还是国外"""
        destination = str(getattr(plan, "destination", "") or "").strip()
        key = destination.lower()
        if key and key in self._destination_scope_cache:
            return self._destination_scope_cache[key]

        scope = self._infer_scope_from_metadata(plan, destination)
        if scope is None:
            scope = await self._ask_llm_destination_scope(destination)
        if scope is None:
            scope = "unknown"

        if key:
            self._destination_scope_cache[key] = scope
        return scope

    def _infer_scope_from_metadata(self, plan: Any, destination: str) -> Optional[str]:
        """优先依据显式国家字段和关键词判断"""
        country = getattr(plan, "country", None)
        if country:
            normalized_country = str(country).strip().lower()
            if normalized_country in {"china", "cn", "prc", "中华人民共和国", "中国"}:
                return "domestic"
            return "international"

        text_lower = destination.lower()
        if any(keyword in destination for keyword in DOMESTIC_KEYWORDS_CN):
            return "domestic"
        if any(keyword in text_lower for keyword in DOMESTIC_KEYWORDS_EN):
            return "domestic"

        if destination and all(ord(ch) < 128 for ch in destination) and not any(
            keyword in text_lower for keyword in DOMESTIC_KEYWORDS_EN
        ):
            return "international"
        return None

    async def _ask_llm_destination_scope(self, destination: str) -> Optional[str]:
        """使用LLM辅助判定目的地范围"""
        if not destination:
            return None
        try:
            system_prompt = (
                "你是地理助手。请判断给定地点是否位于中国境内。"
                "只输出 'domestic' 或 'international'，不要添加其他文字。"
            )
            user_prompt = (
                f"目的地：{destination}\n"
                "如果该地点在中国境内，输出 domestic；否则输出 international。"
            )
            response = await openai_client.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=5,
                temperature=0.0,
            )
            cleaned = (response or "").strip().lower()
            if "domestic" in cleaned or "国内" in cleaned:
                return "domestic"
            if "international" in cleaned or "国外" in cleaned:
                return "international"
        except Exception as exc:
            logger.warning(f"LLM目的地范围判定失败: {exc}")
        return None

    def _adjust_processed_data_for_scope(
        self, processed_data: Optional[Dict[str, Any]], is_international: bool
    ) -> Dict[str, Any]:
        """根据目的地范围调整数据源，海外目的地不信任高德餐饮/住宿"""
        base = processed_data or {}
        if not is_international:
            return base

        adjusted: Dict[str, Any] = {}
        for key, value in base.items():
            if key in {"restaurants", "hotels", "transportation"}:
                adjusted[key] = []
            else:
                adjusted[key] = value
        data_notes = adjusted.setdefault("_data_notes", {})
        data_notes["geo_scope"] = "international_xiaohongshu_priority"
        return adjusted

    def _extract_origin_city(self, plan: Any) -> str:
        """获取用户出发地"""
        for attr in ("departure", "origin", "departure_city", "origin_city"):
            value = getattr(plan, attr, None)
            if value:
                return str(value)
        return "出发地"

    def _determine_transport_stage(self, day: int, total_days: int) -> str:
        """根据天数判断交通阶段"""
        safe_total = max(int(total_days or 0), 1)
        if safe_total == 1:
            return "full_trip"
        if day <= 1:
            return "departure"
        if day >= safe_total:
            return "return"
        return "local"

    def _build_transport_stage_instruction(
        self,
        stage: str,
        origin_city: str,
        destination_city: str,
    ) -> Dict[str, str]:
        """返回阶段标签和提示"""
        if stage == "departure":
            return {
                "label": "出发前往目的地",
                "prompt": (
                    f"这是行程第一天，请规划从 {origin_city} 前往 {destination_city} 的跨城交通，"
                    "包含出发/到达站点、耗时、费用和注意事项，避免生成目的地内部通勤。"
                ),
                "hint": "跨城出发交通",
            }
        if stage == "return":
            return {
                "label": "返程返回出发地",
                "prompt": (
                    f"这是行程最后一天，请规划从 {destination_city} 返回 {origin_city} 的交通，"
                    "注明出发与抵达站点、耗时与费用，避免再描述目的地内部通勤。"
                ),
                "hint": "返程交通",
            }
        if stage == "full_trip":
            return {
                "label": "往返同日行程",
                "prompt": (
                    f"行程仅有一天，需要同时覆盖 {origin_city} ↔ {destination_city} 的往返交通，"
                    "可在同一日程中拆分去程与返程，确保费用与耗时合理。"
                ),
                "hint": "当日往返交通",
            }
        return {
            "label": "目的地内部通勤",
            "prompt": (
                f"这是行程中间天数，仅规划在 {destination_city} 本地的通勤方式（地铁/公交/打车/步行等），"
                "避免重复描述 {origin_city} ↔ {destination_city} 的长途交通。"
            ),
            "hint": "本地通勤",
        }

    def _normalize_transport_stage_routes(
        self,
        entry: Dict[str, Any],
        stage: str,
        origin_city: str,
        destination_city: str,
    ) -> Dict[str, Any]:
        """根据阶段重写交通路线方向，避免LLM自作主张"""
        if not isinstance(entry, dict):
            return entry

        def _ensure_direction(route: Dict[str, Any], forward: bool):
            if not isinstance(route, dict):
                return
            direction = (
                f"{origin_city}→{destination_city}" if forward else f"{destination_city}→{origin_city}"
            )
            route["route"] = direction
            label = route.get("type") or "交通"
            route["name"] = f"{direction} {label}"

        routes = entry.get("primary_routes")
        if not isinstance(routes, list):
            return entry

        if stage == "departure":
            for route in routes:
                _ensure_direction(route, True)
        elif stage == "return":
            for route in routes:
                _ensure_direction(route, False)
        elif stage == "full_trip":
            if routes:
                _ensure_direction(routes[0], True)
            if len(routes) > 1:
                _ensure_direction(routes[1], False)
        else:
            for route in routes:
                if isinstance(route, dict) and destination_city not in str(route.get("route", "")):
                    route["route"] = f"{destination_city}市内通勤"
        return entry

    async def _request_llm_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int,
        temperature: float,
        log_context: str,
    ) -> Optional[Any]:
        response = await openai_client.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        cleaned_response = self._clean_llm_response(response)
        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            logger.warning(f"{log_context} JSON解析失败，原始返回：{cleaned_response}")
            return None

    async def _generate_traditional_plans(
        self,
        processed_data: Dict[str, Any],
        plan: Any,
        preferences: Optional[Dict[str, Any]],
        raw_data: Optional[Dict[str, Any]],
        *,
        is_international: bool = False,
    ) -> List[Dict[str, Any]]:
        plans: List[Dict[str, Any]] = []
        if is_international:
            logger.info("传统算法：海外目的地仅使用小红书与通用经验，忽略高德餐饮/住宿数据")
        plan_types = self._get_plan_types()
        for i, plan_type in enumerate(plan_types):
            plan_data = await self._generate_single_plan(
                processed_data, plan, preferences, plan_type, i, raw_data
            )
            if plan_data:
                plans.append(plan_data)
        logger.info(f"使用传统算法生成了 {len(plans)} 个方案")
        return plans

    def _get_plan_types(self) -> List[str]:
        return [
            "经济实惠型",
            "舒适享受型",
            "文化深度型",
            "自然风光型",
            "美食体验型",
        ][: self.max_plans]

    def _init_segment_context(self, plan: Any) -> PlanSegmentContext:
        total_days = int(getattr(plan, "duration_days", 0) or 0)
        budget = getattr(plan, "budget", None)
        try:
            budget = float(budget) if budget is not None else None
        except (TypeError, ValueError):
            budget = None
        return PlanSegmentContext(
            total_days=total_days,
            remaining_days=total_days,
            remaining_budget=budget,
        )

    def _compute_segment_budget(self, context: PlanSegmentContext, segment_days: int) -> Optional[float]:
        if context.remaining_budget is None or context.remaining_days <= 0:
            return None
        safe_days = max(context.remaining_days, 1)
        per_day = context.remaining_budget / safe_days
        return max(per_day * segment_days, 0)

    def _filter_processed_data_for_context(
        self, processed_data: Dict[str, Any], context: Optional[PlanSegmentContext]
    ) -> Dict[str, Any]:
        if not context:
            return processed_data
        filtered: Dict[str, Any] = {}
        for key, value in processed_data.items():
            if key not in {"attractions", "restaurants", "transportation"}:
                filtered[key] = value
                continue
            entries = []
            for item in value or []:
                if not isinstance(item, dict):
                    entries.append(item)
                    continue
                name = self._extract_resource_name(item, key)
                normalized = self._normalize_resource_name(name)
                used_set = self._get_used_set(context, key)
                if normalized and normalized in used_set:
                    continue
                entries.append(item)
            filtered[key] = entries
        return filtered

    def _get_used_set(self, context: PlanSegmentContext, key: str):
        if key == "attractions":
            return context.used_attractions
        if key == "restaurants":
            return context.used_restaurants
        if key == "transportation":
            return context.used_transport
        return set()

    def _build_used_prompt(
        self, context: Optional[PlanSegmentContext], key: str, limit: int = 5
    ) -> str:
        if not context:
            return ""
        used = list(self._get_used_set(context, key))
        if not used:
            return ""
        names = "、".join(used[:limit])
        return names

    def _extract_resource_name(self, item: Dict[str, Any], category: str) -> Optional[str]:
        if not isinstance(item, dict):
            return None
        if category == "transportation":
            return item.get("name") or item.get("route")
        return item.get("name")

    def _normalize_resource_name(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        return str(value).strip().lower()

    def _deduplicate_daily_attractions(self, plan_data: Dict[str, Any]) -> None:
        """在同一方案内按天去重景点，避免同一景点出现在多个日期.

        智能去重策略：
        1. 如果景点总数充足，严格去重，确保每个景点只出现一次
        2. 如果景点总数不足，优先保留未使用的景点，但允许重复使用以填满每天的最少景点数
        
        仅依靠景点名称进行去重，名称为空或无法解析的条目原样保留。
        该函数会原地修改 ``plan_data`` 中的 ``daily_itineraries``。
        """
        try:
            daily_itineraries = plan_data.get("daily_itineraries", []) or []
            if not daily_itineraries:
                return
            
            # 第一步：收集所有景点并统计唯一景点总数
            all_attractions: List[Tuple[Any, str]] = []  # (attraction_obj, normalized_name)
            for day in daily_itineraries:
                attractions = day.get("attractions") or []
                if not isinstance(attractions, list):
                    continue
                for attr in attractions:
                    name = None
                    if isinstance(attr, dict):
                        name = attr.get("name")
                    elif isinstance(attr, str):
                        name = attr
                    normalized = self._normalize_resource_name(name)
                    if normalized:  # 只统计有名字的景点
                        all_attractions.append((attr, normalized))
            
            # 统计唯一景点数量
            unique_attraction_names = set(norm for _, norm in all_attractions)
            total_unique = len(unique_attraction_names)
            total_days = len(daily_itineraries)
            min_per_day = self.min_attractions_per_day
            required_total = total_days * min_per_day
            
            # 如果唯一景点数足够，使用严格去重
            if total_unique >= required_total:
                seen: Set[str] = set()
                for day in daily_itineraries:
                    attractions = day.get("attractions") or []
                    if not isinstance(attractions, list):
                        continue
                    unique: List[Any] = []
                    for attr in attractions:
                        name = None
                        if isinstance(attr, dict):
                            name = attr.get("name")
                        elif isinstance(attr, str):
                            name = attr
                        normalized = self._normalize_resource_name(name)
                        # 没有名字的，或者未见过的，直接保留
                        if not normalized or normalized not in seen:
                            unique.append(attr)
                            if normalized:
                                seen.add(normalized)
                    day["attractions"] = unique
                logger.info(f"景点充足({total_unique}个唯一景点，需要{required_total}个)，已严格去重")
            else:
                # 景点不足，使用智能去重策略
                logger.info(f"景点不足({total_unique}个唯一景点，需要{required_total}个)，启用智能去重策略")
                
                # 记录每个景点的使用次数
                usage_count: Dict[str, int] = {}
                # 建立景点对象到名称的映射
                attr_to_name: Dict[int, str] = {}  # 使用id(attr)作为key
                
                # 第一遍：优先保留未使用的景点，统计使用次数
                seen: Set[str] = set()
                for day in daily_itineraries:
                    attractions = day.get("attractions") or []
                    if not isinstance(attractions, list):
                        continue
                    unique: List[Any] = []
                    for attr in attractions:
                        name = None
                        if isinstance(attr, dict):
                            name = attr.get("name")
                        elif isinstance(attr, str):
                            name = attr
                        normalized = self._normalize_resource_name(name)
                        
                        if not normalized:
                            # 没有名字的，直接保留
                            unique.append(attr)
                        elif normalized not in seen:
                            # 未使用过的，优先保留
                            unique.append(attr)
                            seen.add(normalized)
                            usage_count[normalized] = 1
                            attr_to_name[id(attr)] = normalized
                        else:
                            # 已使用过的，记录使用次数，稍后处理
                            usage_count[normalized] = usage_count.get(normalized, 0) + 1
                            attr_to_name[id(attr)] = normalized
                    
                    day["attractions"] = unique
                
                # 第二遍：如果某天景点数不足，从已使用的景点中补充（优先选择使用次数最少的）
                for day in daily_itineraries:
                    attractions = day.get("attractions") or []
                    if not isinstance(attractions, list):
                        continue
                    
                    current_count = len([a for a in attractions if self._normalize_resource_name(
                        a.get("name") if isinstance(a, dict) else (a if isinstance(a, str) else None)
                    )])
                    
                    # 如果当前景点数少于最少要求，需要补充
                    if current_count < min_per_day:
                        needed = min_per_day - current_count
                        
                        # 找出所有已使用的景点，按使用次数排序（使用次数少的优先）
                        available_attrs = [
                            (norm, count) for norm, count in usage_count.items()
                            if norm in seen  # 只考虑已使用过的
                        ]
                        available_attrs.sort(key=lambda x: x[1])  # 按使用次数升序
                        
                        # 从使用次数最少的景点中选择补充
                        for norm, _ in available_attrs[:needed]:
                            # 从原始数据中找到对应的景点对象
                            for orig_attr, orig_norm in all_attractions:
                                if orig_norm == norm:
                                    # 创建副本，避免引用问题
                                    if isinstance(orig_attr, dict):
                                        attr_copy = copy.deepcopy(orig_attr)
                                    else:
                                        attr_copy = orig_attr
                                    attractions.append(attr_copy)
                                    usage_count[norm] = usage_count.get(norm, 0) + 1
                                    break
                        
                        day["attractions"] = attractions
                        logger.debug(f"第{day.get('day', '?')}天补充了{needed}个景点，当前共{len(attractions)}个")
                
                logger.info(f"智能去重完成，部分景点允许重复使用以填满每天最少{min_per_day}个景点的要求")
                
        except Exception as e:  # 防御性，任何异常不影响主流程
            logger.warning(f"去重每日景点失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())

    def _update_segment_context(self, context: PlanSegmentContext, plan_data: Dict[str, Any]) -> None:
        spent = self._coerce_number(plan_data.get("total_cost", {}).get("total", 0))
        if context.remaining_budget is not None:
            context.remaining_budget = max(0.0, context.remaining_budget - spent)
        segment_days = len(plan_data.get("daily_itineraries", []))
        context.remaining_days = max(0, context.remaining_days - segment_days)

        for day in plan_data.get("daily_itineraries", []):
            for attraction in day.get("attractions", []):
                name = None
                if isinstance(attraction, dict):
                    name = attraction.get("name")
                elif isinstance(attraction, str):
                    name = attraction
                normalized = self._normalize_resource_name(name)
                if normalized:
                    context.used_attractions.add(normalized)

        for restaurant in plan_data.get("restaurants", []):
            if isinstance(restaurant, dict):
                normalized = self._normalize_resource_name(restaurant.get("name"))
                if normalized:
                    context.used_restaurants.add(normalized)

        transportation_entries = plan_data.get("transportation", []) or []
        if isinstance(transportation_entries, dict):
            transportation_entries = [transportation_entries]
        for transport in transportation_entries:
            if isinstance(transport, dict):
                normalized = self._normalize_resource_name(
                    transport.get("name") or transport.get("route")
                )
                if normalized:
                    context.used_transport.add(normalized)

    def _split_plan_into_segments(self, plan: Any) -> List[Dict[str, Any]]:
        segments: List[Dict[str, Any]] = []
        total_days = max(int(getattr(plan, "duration_days", 0)), 0)
        start_date = self._to_datetime(getattr(plan, "start_date", None))
        if total_days <= self.max_segment_days:
            logger.debug("计划天数未超过阈值，无需分段")
            return segments
        if not start_date:
            logger.warning("计划开始日期无法解析，分段生成被跳过")
            return segments
        remaining = total_days
        offset = 0
        while remaining > 0:
            days = min(self.max_segment_days, remaining)
            seg_start = start_date + timedelta(days=offset)
            seg_end = seg_start + timedelta(days=days - 1)
            segments.append(
                {
                    "start_date": seg_start,
                    "end_date": seg_end,
                    "days": days,
                    "offset": offset,
                }
            )
            offset += days
            remaining -= days
        logger.info(f"根据 {total_days} 天拆分成 {len(segments)} 段")
        return segments

    def _build_segment_plan(
        self,
        plan: Any,
        segment: Dict[str, Any],
        preferences: Optional[Dict[str, Any]],
        segment_budget: Optional[float],
    ) -> Any:
        base_attrs = {
            "id": getattr(plan, "id", None),
            "title": getattr(plan, "title", None),
            "description": getattr(plan, "description", None),
            "departure": getattr(plan, "departure", None),
            "destination": getattr(plan, "destination", None),
            "transportation": getattr(plan, "transportation", None),
            "requirements": getattr(plan, "requirements", None),
            "num_people": getattr(plan, "num_people", None)
            or (preferences or {}).get("travelers")
            or getattr(plan, "travelers", None),
            "age_group": getattr(plan, "age_group", None),
            "travelers": getattr(plan, "travelers", None)
            or (preferences or {}).get("travelers"),
            "user_id": getattr(plan, "user_id", None),
            "status": getattr(plan, "status", None),
            "score": getattr(plan, "score", None),
            "is_public": getattr(plan, "is_public", None),
            "public_at": getattr(plan, "public_at", None),
        }
        base_attrs.update(
            {
                "duration_days": segment["days"],
                "start_date": segment["start_date"],
                "end_date": segment["end_date"],
                "budget": segment_budget,
            }
        )
        return SimpleNamespace(**base_attrs)

    def _clone_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        return copy.deepcopy(plan)

    def _merge_total_cost(self, base: Dict[str, Any], segment: Dict[str, Any]) -> None:
        base_cost = base.get("total_cost")
        seg_cost = segment.get("total_cost")
        if not isinstance(seg_cost, dict):
            return
        if not isinstance(base_cost, dict):
            base_cost = {}
        for key, value in seg_cost.items():
            if isinstance(value, (int, float)):
                base_cost[key] = base_cost.get(key, 0) + value
            else:
                base_cost[key] = value
        base["total_cost"] = base_cost

    def _append_segment_plan(self, base: Dict[str, Any], segment: Dict[str, Any]) -> Dict[str, Any]:
        base.setdefault("daily_itineraries", [])
        base["daily_itineraries"].extend(segment.get("daily_itineraries", []))
        for key in ["restaurants", "hotels", "flights", "transportation", "attractions"]:
            if segment.get(key):
                base.setdefault(key, [])
                base[key].extend(segment.get(key, []))
        self._merge_total_cost(base, segment)
        if segment.get("summary"):
            base["summary"] = (
                base.get("summary", "") + f"\n{segment.get('summary')}"
            ).strip()
        return base

    def _merge_segment_plans(
        self, existing: List[Dict[str, Any]], segment_plans: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not existing:
            return [self._clone_plan(p) for p in segment_plans]
        max_len = max(len(existing), len(segment_plans))
        merged: List[Dict[str, Any]] = []
        for idx in range(max_len):
            base_plan = self._clone_plan(existing[idx]) if idx < len(existing) else None
            seg_plan = segment_plans[idx] if idx < len(segment_plans) else None
            if base_plan and seg_plan:
                merged.append(self._append_segment_plan(base_plan, seg_plan))
            elif base_plan:
                merged.append(base_plan)
            elif seg_plan:
                merged.append(self._clone_plan(seg_plan))
        return merged

    async def _generate_segmented_plans(
        self,
        processed_data: Dict[str, Any],
        plan: Any,
        preferences: Optional[Dict[str, Any]],
        raw_data: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        segments = self._split_plan_into_segments(plan)
        if not segments:
            logger.debug("未生成任何分段，回退到单段策略")
            return None

        plan_types = self._get_plan_types()
        if not plan_types:
            logger.warning("无可用方案类型，分段生成中断")
            return None

        contexts = [self._init_segment_context(plan) for _ in plan_types]
        aggregated_plans: List[Optional[Dict[str, Any]]] = [None] * len(plan_types)

        for segment in segments:
            logger.info(
                "处理分段 offset=%s, days=%s", segment.get("offset"), segment.get("days")
            )
            for idx, plan_type in enumerate(plan_types):
                context = contexts[idx]
                segment_budget = self._compute_segment_budget(context, segment["days"])
                segment_plan = self._build_segment_plan(plan, segment, preferences, segment_budget)
                filtered_data = self._filter_processed_data_for_context(processed_data, context)

                plan_variant = await self._generate_single_plan(
                    filtered_data, segment_plan, preferences, plan_type, idx, raw_data
                )

                if not plan_variant:
                    logger.warning(
                        "分段方案生成失败，plan_type=%s, offset=%s", plan_type, segment.get("offset")
                    )
                    continue

                if aggregated_plans[idx] is None:
                    aggregated_plans[idx] = plan_variant
                else:
                    aggregated_plans[idx] = self._append_segment_plan(
                        aggregated_plans[idx], plan_variant
                    )

                self._update_segment_context(context, plan_variant)

        final_plans = [plan for plan in aggregated_plans if plan]
        if not final_plans:
            logger.error("所有分段都生成失败，回退到完整方案生成")
            return None

        for final_plan in final_plans:
            final_plan["duration_days"] = getattr(plan, "duration_days", None)
            final_plan["start_date"] = getattr(plan, "start_date", None)
            final_plan["end_date"] = getattr(plan, "end_date", None)
            final_plan["budget"] = getattr(plan, "budget", None)

        logger.info(f"分段生成完成，共合并 {len(final_plans)} 个完整方案")
        return final_plans

    def _should_use_split_strategy(self, preferences: Optional[Dict[str, Any]]) -> bool:
        """判断是否应该使用拆分策略"""
        if not preferences:
            return False
        
        # 检查是否有多个活动偏好
        activity_preferences = preferences.get('activity_preference', [])
        if isinstance(activity_preferences, str):
            activity_preferences = [activity_preferences]
        
        # 如果有2个或以上的活动偏好，使用拆分策略
        if len(activity_preferences) >= 2:
            logger.info(f"检测到多个偏好 {activity_preferences}，使用拆分策略")
            return True
        
        # 检查是否有冲突的偏好组合
        has_culture = 'culture' in activity_preferences
        has_nature = 'nature' in activity_preferences
        has_food = 'food' in activity_preferences
        has_shopping = 'shopping' in activity_preferences
        
        # 如果同时有文化和自然偏好，使用拆分策略
        if has_culture and has_nature:
            logger.info("[计划生成器] 检测到文化和自然偏好冲突，使用拆分策略")
            return True
        
        # 如果同时有美食和购物偏好，使用拆分策略
        if has_food and has_shopping:
            logger.info("[计划生成器] 检测到美食和购物偏好冲突，使用拆分策略")
            return True
        
        return False
    
    def _group_preferences_by_compatibility(self, preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """将偏好按兼容性分组，避免冲突的偏好在同一批次生成"""
        if not preferences:
            return [{}]
        
        # 定义偏好冲突组
        conflict_groups = {
            'budget_vs_luxury': ['budget_priority', 'luxury_preference'],
            'culture_vs_nature': ['culture', 'nature'],
            'food_vs_adventure': ['food', 'adventure'],
            'relaxation_vs_shopping': ['relaxation', 'shopping']
        }
        
        # 提取活动偏好
        activity_preferences = preferences.get('activity_preference', [])
        if isinstance(activity_preferences, str):
            activity_preferences = [activity_preferences]
        
        logger.warning(f"preferences={preferences}")

        # 基础偏好组（所有方案都包含）
        base_preferences = {
            'budget_priority': preferences.get('budget_priority', 'medium'),
            'travelers': preferences.get('travelers', 1),
            'foodPreferences': preferences.get('foodPreferences', []),
            'dietaryRestrictions': preferences.get('dietaryRestrictions', []),
            'ageGroups': preferences.get('ageGroups', [])
        }
        
        # 如果没有活动偏好，返回基础偏好
        if not activity_preferences:
            return [base_preferences]
        
        # 根据活动偏好创建分组
        preference_groups = []
        
        # 文化历史类
        if 'culture' in activity_preferences:
            culture_group = base_preferences.copy()
            culture_group['activity_preference'] = 'culture'
            culture_group['focus'] = 'cultural_depth'
            preference_groups.append(culture_group)
        
        # 自然风光类
        if 'nature' in activity_preferences:
            nature_group = base_preferences.copy()
            nature_group['activity_preference'] = 'nature'
            nature_group['focus'] = 'natural_beauty'
            preference_groups.append(nature_group)
        
        # 美食体验类
        if 'food' in activity_preferences:
            food_group = base_preferences.copy()
            food_group['activity_preference'] = 'food'
            food_group['focus'] = 'culinary_experience'
            preference_groups.append(food_group)
        
        # 购物娱乐类
        if 'shopping' in activity_preferences:
            shopping_group = base_preferences.copy()
            shopping_group['activity_preference'] = 'shopping'
            shopping_group['focus'] = 'entertainment'
            preference_groups.append(shopping_group)
        
        # 冒险刺激类
        if 'adventure' in activity_preferences:
            adventure_group = base_preferences.copy()
            adventure_group['activity_preference'] = 'adventure'
            adventure_group['focus'] = 'thrilling_activities'
            preference_groups.append(adventure_group)
        
        # 休闲放松类
        if 'relaxation' in activity_preferences:
            relaxation_group = base_preferences.copy()
            relaxation_group['activity_preference'] = 'relaxation'
            relaxation_group['focus'] = 'peaceful_experience'
            preference_groups.append(relaxation_group)
        
        # 如果没有匹配的偏好，返回基础偏好
        if not preference_groups:
            return [base_preferences]
        
        # 限制最大分组数量，避免过多的LLM调用
        max_groups = 3
        if len(preference_groups) > max_groups:
            # 优先保留前三个偏好组
            preference_groups = preference_groups[:max_groups]
        
        logger.info(f"[计划生成器] 偏好分组结果: {len(preference_groups)} 个组")
        for i, group in enumerate(preference_groups):
            logger.info(f"[计划生成器] 组 {i+1}: {group.get('focus', 'unknown')} - {group.get('activity_preference', 'none')}")
        
        return preference_groups

    async def _generate_plans_with_split_preferences(
        self,
        processed_data: Dict[str, Any],
        plan: Any,
        preferences: Optional[Dict[str, Any]] = None,
        raw_data: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """使用拆分偏好策略生成方案"""
        try:
            logger.info("[计划生成器] 开始使用拆分偏好策略生成方案")
            
            # 将偏好分组
            preference_groups = self._group_preferences_by_compatibility(preferences)
            
            all_plans = []
            
            # 为每个偏好组生成方案
            for i, pref_group in enumerate(preference_groups):
                logger.info(f"[计划生成器] 为偏好组 {i+1}/{len(preference_groups)} 生成方案: {pref_group.get('focus', 'unknown')}")
                
                try:
                    # 为单个偏好组生成1-2个方案
                    group_plans = await self._generate_plans_for_single_preference(
                        processed_data, plan, pref_group, raw_data, max_plans=1
                    )
                    
                    if group_plans:
                        # 为方案添加偏好标识
                        for plan_data in group_plans:
                            plan_data['preference_focus'] = pref_group.get('focus', 'general')
                            plan_data['preference_group'] = i + 1
                        
                        all_plans.extend(group_plans)
                        logger.info(f"[计划生成器] 偏好组 {i+1} 生成了 {len(group_plans)} 个方案")
                    else:
                        logger.warning(f"[计划生成器] 偏好组 {i+1} 未能生成方案")
                
                except Exception as e:
                    logger.error(f"[计划生成器] 偏好组 {i+1} 生成失败: {e}")
                    continue
            
            # 合并和去重
            merged_plans = self._merge_and_deduplicate_plans(all_plans)
            
            logger.info(f"[计划生成器] 拆分生成完成，总共生成 {len(merged_plans)} 个方案")
            return merged_plans
            
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f"[计划生成器] 拆分偏好生成失败: {e}")
            return []

    async def _generate_plans_for_single_preference(
        self,
        processed_data: Dict[str, Any],
        plan: Any,
        preference: Dict[str, Any],
        raw_data: Optional[Dict[str, Any]] = None,
        max_plans: int = 1
    ) -> List[Dict[str, Any]]:
        """为单个偏好生成方案"""
        try:
            # logger.warning(f"preference={preference}")

            # 构建针对性的系统提示
            focus = preference.get('focus', 'general')
            activity_pref = preference.get('activity_preference', 'culture')
            
            system_prompt = f"""你是一个专业的旅行规划师，专门设计{self._get_focus_description(focus)}的旅行方案。

请根据提供的数据和用户需求，生成{max_plans}个针对{focus}的旅行方案。

在制定方案时，请特别注意以下要求：
1. 重点关注{activity_pref}相关的景点和活动
2. 人数配置：根据旅行人数合理安排住宿、餐厅、交通
3. 年龄群体：针对不同年龄段调整行程强度和活动安排
4. 饮食偏好：根据用户口味偏好推荐合适的餐厅
5. 饮食禁忌：严格避免推荐包含用户饮食禁忌的餐厅和食物

重要：请直接返回一个包含所有方案的数组，不要嵌套在plans对象中。

必须严格按照以下JSON格式返回：

[
  {{
    "id": "plan_1",
    "type": "{self._get_plan_type_by_focus(focus)}",
    "title": "{self._get_plan_title_by_focus(focus, plan.destination)}",
    "description": "详细的方案描述",
    "flight": {{
      "airline": "航空公司",
      "departure_time": "出发时间",
      "arrival_time": "到达时间",
      "price": 价格,
      "rating": 评分
    }},
    "hotel": {{
      "name": "酒店名称",
      "address": "酒店地址",
      "price_per_night": 每晚价格,
      "rating": 评分,
      "amenities": ["设施1", "设施2"]
    }},
    "daily_itineraries": [
      {{
        "day": 1,
        "date": "日期",
        "attractions": [
          {{
            "name": "景点名称",
            "category": "景点类型",
            "description": "景点描述",
            "price": 门票价格,
            "rating": 评分,
            "visit_time": "建议游览时间"
          }}
        ],
        "meals": [
          {{
            "type": "早餐/午餐/晚餐",
            "time": "用餐时间",
            "suggestion": "餐厅建议",
            "estimated_cost": 预估费用
          }}
        ],
        "transportation": {{
          "type": "交通方式",
          "route": "具体路线",
          "duration": "耗时(分钟)",
          "distance": "距离(公里)",
          "cost": "费用(元)",
          "traffic_conditions": "路况信息"
        }},
        "estimated_cost": 当日总费用
      }}
    ],
    "restaurants": [
      {{
        "name": "餐厅名称",
        "cuisine": "菜系",
        "price_range": "参考消费(元)",
        "rating": 评分,
        "address": "地址"
      }}
    ],
    "transportation": [
      {{
        "type": "交通方式",
        "name": "交通名称",
        "description": "简要描述",
        "duration": "耗时(分钟)",
        "distance": "距离(公里)",
        "price": "费用(元)"
      }}
    ],
    "total_cost": {{
      "flight": 航班费用,
      "hotel": 酒店费用,
      "attractions": 景点费用,
      "meals": 餐饮费用,
      "transportation": 交通费用,
      "total": 总费用
    }},
    "weather_info": {{
      "travel_recommendations": ["基于天气的旅游建议1", "建议2"]
    }},
    "duration_days": 天数,
    "generated_at": "生成时间"
  }}
]

请确保返回的JSON格式完全符合上述结构，不要添加任何额外的文本或说明。"""
            
            # 构建用户提示
            user_prompt = f"""
请为以下旅行需求制定{max_plans}个专注于{focus}的方案：

出发地：{plan.departure}
目的地：{plan.destination}
旅行天数：{plan.duration_days}天
出发日期：{plan.start_date}
返回日期：{plan.end_date}
预算：{plan.budget}元
出行方式：{plan.transportation or '未指定'}
旅行人数：{preference.get('travelers', 1)}人
年龄群体：{', '.join(preference.get('ageGroups', [])) if preference.get('ageGroups', None) else '未指定'}
饮食偏好：{', '.join(preference.get('foodPreferences', [])) if preference.get('foodPreferences', None) else '无特殊偏好'}
饮食禁忌：{', '.join(preference.get('dietaryRestrictions', [])) if preference.get('dietaryRestrictions', None) else '无饮食禁忌'}
重点偏好：{activity_pref}
特殊要求：{plan.requirements or '无特殊要求'}

真实可用数据：

航班信息：
{self._format_data_for_llm(processed_data.get('flights', []), 'flight')}

酒店信息：
{self._format_data_for_llm(processed_data.get('hotels', []), 'hotel')}

景点信息（重点关注{activity_pref}相关）：
{self._format_data_for_llm(self._filter_attractions_by_preference(processed_data.get('attractions', []), activity_pref), 'attraction')}

餐厅信息：
{self._format_data_for_llm(processed_data.get('restaurants', []), 'restaurant')}

交通信息：
{self._format_data_for_llm(processed_data.get('transportation', []), 'transportation')}

天气信息：
{processed_data.get('weather', {})}

小红书真实用户分享（重要参考）：
{self._format_xiaohongshu_data_for_prompt(raw_data.get('xiaohongshu_notes', []) if raw_data else [], plan.destination)}

请基于以上真实数据生成{max_plans}个专注于{focus}的旅行方案。

重要提醒：
1. 必须严格按照指定的JSON格式返回
2. 必须使用提供的真实数据，不要虚构信息
3. 重点突出{activity_pref}相关的景点和活动
4. 价格信息要基于真实数据，符合预算
5. 景点安排要优先选择{activity_pref}类型的景点
6. 餐饮建议要考虑与{activity_pref}景点的距离
7. 根据旅行人数合理安排住宿、餐厅、交通
8. 严格遵守饮食禁忌和偏好

请直接返回JSON格式的结果，不要添加任何其他文本。
"""
            
            # 调用LLM生成方案
            response = await openai_client.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=0.7
            )
            
            if not response:
                logger.warning("[计划生成器] LLM返回空响应")
                return []
            
            # 解析JSON响应
            try:
                plans = json.loads(response)
                if not isinstance(plans, list):
                    logger.warning("[计划生成器] LLM返回的不是数组格式")
                    logger.warning(f"[计划生成器] LLM返回: {response}")
                    return []
                
                logger.warning(f"[计划生成器] LLM返回: {plans}")

                logger.info(f"[计划生成器] 单偏好生成成功，解析到 {len(plans)} 个方案")
                return plans
                
            except json.JSONDecodeError as e:
                logger.error(f"[计划生成器] 解析LLM响应JSON失败: {e}")
                logger.error(f"[计划生成器] 响应内容: {response[:500]}...")
                return []
                
        except Exception as e:
            logger.error(f"[计划生成器] 单偏好方案生成失败: {e}")
            return []

    def _get_focus_description(self, focus: str) -> str:
        """获取偏好焦点的描述"""
        descriptions = {
            'cultural_depth': '文化深度体验',
            'natural_beauty': '自然风光欣赏',
            'culinary_experience': '美食文化体验',
            'entertainment': '购物娱乐',
            'thrilling_activities': '冒险刺激体验',
            'peaceful_experience': '休闲放松体验',
            'general': '综合体验'
        }
        return descriptions.get(focus, '综合体验')

    def _get_plan_type_by_focus(self, focus: str) -> str:
        """根据偏好焦点获取方案类型"""
        types = {
            'cultural_depth': '文化深度型',
            'natural_beauty': '自然风光型',
            'culinary_experience': '美食体验型',
            'entertainment': '购物娱乐型',
            'thrilling_activities': '冒险刺激型',
            'peaceful_experience': '休闲放松型',
            'general': '综合体验型'
        }
        return types.get(focus, '综合体验型')

    def _get_plan_title_by_focus(self, focus: str, destination: str) -> str:
        """根据偏好焦点获取方案标题"""
        titles = {
            'cultural_depth': f'深度文化探索{destination}之旅',
            'natural_beauty': f'{destination}自然风光之旅',
            'culinary_experience': f'{destination}美食文化之旅',
            'entertainment': f'{destination}购物娱乐之旅',
            'thrilling_activities': f'{destination}冒险刺激之旅',
            'peaceful_experience': f'{destination}休闲放松之旅',
            'general': f'{destination}综合体验之旅'
        }
        return titles.get(focus, f'{destination}精彩之旅')

    def _filter_attractions_by_preference(self, attractions: List[Dict], preference: str) -> List[Dict]:
        """根据偏好过滤景点"""
        if not attractions or not preference:
            return attractions
        
        # 定义偏好关键词映射
        preference_keywords = {
            'culture': ['博物馆', '文化', '历史', '古迹', '寺庙', '宫殿', '纪念', '遗址', '传统'],
            'nature': ['公园', '山', '湖', '海', '森林', '自然', '风景', '景观', '生态', '户外'],
            'food': ['美食', '小吃', '餐厅', '市场', '夜市', '特色', '当地'],
            'shopping': ['商场', '购物', '市场', '街区', '商业', '店铺'],
            'adventure': ['游乐', '刺激', '冒险', '运动', '极限', '挑战'],
            'relaxation': ['温泉', '度假', '休闲', '放松', '养生', '慢节奏']
        }
        
        keywords = preference_keywords.get(preference, [])
        if not keywords:
            return attractions
        
        # 过滤景点
        filtered = []
        for attraction in attractions:
            name = attraction.get('name', '')
            description = attraction.get('description', '')
            category = attraction.get('category', '')
            
            # 检查是否包含相关关键词
            text_to_check = f"{name} {description} {category}".lower()
            if any(keyword in text_to_check for keyword in keywords):
                filtered.append(attraction)
        
        # 如果过滤后太少，返回原始列表的前部分
        if len(filtered) < 3:
            return attractions[:10]
        
        return filtered

    def _merge_and_deduplicate_plans(self, plans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """合并和去重方案"""
        if not plans:
            return []
        
        # 简单的去重逻辑：基于方案类型和主要景点
        seen_signatures = set()
        unique_plans = []
        
        for plan in plans:
            # 创建方案签名
            plan_type = plan.get('type', '')
            attractions = []
            
            # 提取主要景点
            for day in plan.get('daily_itineraries', []):
                for attraction in day.get('attractions', []):
                    attractions.append(attraction.get('name', ''))
            
            signature = f"{plan_type}_{hash(tuple(sorted(attractions[:3])))}"
            
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_plans.append(plan)
        
        # 限制最终方案数量
        max_final_plans = 5
        if len(unique_plans) > max_final_plans:
            unique_plans = unique_plans[:max_final_plans]
        
        # 重新分配ID
        for i, plan in enumerate(unique_plans):
            plan['id'] = f"plan_{i+1}"
        
        logger.info(f"合并去重完成：{len(plans)} -> {len(unique_plans)} 个方案")
        return unique_plans

    async def _generate_plans_with_llm(
        self,
        processed_data: Dict[str, Any],
        plan: Any,
        preferences: Optional[Dict[str, Any]] = None,
        raw_data: Optional[Dict[str, Any]] = None,
        *,
        is_international: bool = False,
    ) -> List[Dict[str, Any]]:
        """使用模块化LLM生成旅行方案"""
        try:
            logger.info("开始模块化生成旅行方案")
            
            # 异步并发调用各模块生成器，子方案支持失败重试
            logger.info("开始并发生成各模块方案，并启用重试机制...")

            async def run_with_retry(
                coro_fn,
                *args,
                attempts: int = 3,
                delay: float = 1.0,
                module_name: str = "",
                **kwargs,
            ):
                last_error: Optional[Exception] = None
                for i in range(attempts):
                    try:
                        result = await coro_fn(*args, **kwargs)
                        return {"success": True, "data": result or []}
                    except Exception as e:
                        last_error = e
                        logger.error(f"{module_name} 生成失败，第 {i+1}/{attempts} 次: {e}")
                        if i < attempts - 1:
                            await asyncio.sleep(delay)
                logger.error(f"{module_name} 重试耗尽，将返回空结果")
                return {"success": False, "data": [], "error": last_error}

            module_tasks = [
                {
                    "key": "accommodation",
                    "name": "住宿方案",
                    "critical": True,
                    "coro": run_with_retry(
                        self._generate_accommodation_plans,
                        processed_data.get('hotels', []),
                        processed_data.get('flights', []),
                        plan,
                        preferences,
                        raw_data,
                        is_international=is_international,
                        attempts=3,
                        delay=1.0,
                        module_name="住宿方案",
                    ),
                },
                {
                    "key": "dining",
                    "name": "餐饮方案",
                    "critical": False,
                    "coro": run_with_retry(
                        self._generate_dining_plans,
                        processed_data.get('restaurants', []),
                        plan,
                        preferences,
                        raw_data,
                        is_international=is_international,
                        attempts=3,
                        delay=1.0,
                        module_name="餐饮方案",
                    ),
                },
                {
                    "key": "transportation",
                    "name": "交通方案",
                    "critical": False,
                    "coro": run_with_retry(
                        self._generate_transportation_plans,
                        processed_data.get('transportation', []),
                        plan,
                        preferences,
                        raw_data,
                        is_international=is_international,
                        attempts=3,
                        delay=1.0,
                        module_name="交通方案",
                    ),
                },
                {
                    "key": "attraction",
                    "name": "景点方案",
                    "critical": True,
                    "coro": run_with_retry(
                        self._generate_attraction_plans,
                        processed_data.get('attractions', []),
                        plan,
                        preferences,
                        raw_data,
                        is_international=is_international,
                        attempts=3,
                        delay=1.0,
                        module_name="景点方案",
                    ),
                },
            ]

            coro_list = [item["coro"] for item in module_tasks]
            results = await asyncio.gather(*coro_list)
            for item, result in zip(module_tasks, results):
                item["result"] = result
                item["data"] = result.get("data", []) if isinstance(result, dict) else []

            critical_failures = [
                item["name"]
                for item in module_tasks
                if item["critical"] and (not item["data"])
            ]
            optional_failures = [
                item["name"]
                for item in module_tasks
                if not item["critical"] and not item["data"]
            ]

            failed_due_to_error = [
                item["name"]
                for item in module_tasks
                if not item["result"].get("success", False)
            ]

            if optional_failures:
                logger.warning(f"以下模块未生成数据，将以空结果继续: {', '.join(optional_failures)}")
            if failed_due_to_error:
                logger.warning(f"以下模块多次重试仍失败: {', '.join(failed_due_to_error)}")
            
            if critical_failures:
                error_msg = f"关键模块缺失: {', '.join(set(critical_failures))}"
                logger.error(error_msg)
                raise Exception(error_msg)

            accommodation_plans = next(item["data"] for item in module_tasks if item["key"] == "accommodation")
            dining_plans = next(item["data"] for item in module_tasks if item["key"] == "dining")
            transportation_plans = next(item["data"] for item in module_tasks if item["key"] == "transportation")
            attraction_plans = next(item["data"] for item in module_tasks if item["key"] == "attraction")
            
            logger.info(f"模块化生成完成 - 住宿:{len(accommodation_plans)}, 餐饮:{len(dining_plans)}, 交通:{len(transportation_plans)}, 景点:{len(attraction_plans)}")
            
            # 使用组装器整合所有方案
            assembled_plans = await self._assemble_travel_plans(
                accommodation_plans,
                dining_plans,
                transportation_plans,
                attraction_plans,
                processed_data,
                plan,
                is_international=is_international,
            )
            
            if not assembled_plans:
                logger.error("方案组装失败，返回空列表")
                return []
            
            logger.info(f"成功生成 {len(assembled_plans)} 个完整旅行方案")
            return assembled_plans
            
        except Exception as e:
            logger.error(f"模块化生成方案失败: {e}")
            # 如果模块化生成失败，回退到原始方法
            logger.info("回退到原始LLM生成方法")
            return await self._generate_plans_with_llm_fallback(
                processed_data,
                plan,
                preferences,
                raw_data,
                is_international=is_international,
            )


    
    def _validate_plan_data(self, plan_data: Dict[str, Any]) -> bool:
        """验证方案数据"""
        required_fields = ['title', 'description']
        return all(field in plan_data for field in required_fields)

    def _enforce_transportation_from_data(self, plans: List[Dict[str, Any]], processed_data: Dict[str, Any]) -> None:
        """用已收集的真实交通数据覆盖/校准 LLM 的交通字段，避免被编造。
        - 将 processed_data['transportation'] 中的前几条写回到每个方案的 transportation
        - 同时为 daily_itineraries 中缺失或为字符串的 transportation 填入第一条真实交通摘要
        - 记录校准前后的距离/时长，便于排查
        """
        try:
            real_transport = processed_data.get('transportation', []) or []
            if not real_transport:
                logger.info("无可用真实交通数据，跳过交通校准")
                return
            # 生成摘要函数
            def summarize(t: Dict[str, Any]) -> str:
                t_type = t.get('type') or '交通'
                dist = t.get('distance')
                dur = t.get('duration')
                cost = t.get('price', t.get('cost'))
                parts = [t_type]
                if isinstance(dist, (int, float)):
                    parts.append(f"{int(dist)}公里")
                if isinstance(dur, (int, float)):
                    parts.append(f"{int(dur)}分钟")
                if isinstance(cost, (int, float)):
                    parts.append(f"¥{int(cost)}")
                return ' · '.join(parts)

            # 选择用于填充的第一条真实交通
            primary = real_transport[0]

            for idx, p in enumerate(plans):
                before = p.get('transportation')
                p['transportation'] = real_transport[:3]
                after = p['transportation']
                logger.info(f"[Transport Calibrate] plan[{idx}] trans before={type(before).__name__} -> after={len(after)} items")

                # 校准每日行程的 transportation 文本/对象
                daily = p.get('daily_itineraries') or []
                for d in daily:
                    dt = d.get('transportation')
                    if not dt or isinstance(dt, str):
                        d['transportation'] = summarize(primary)
        except Exception as e:
            logger.warning(f"交通数据校准失败: {e}")
    
    def _clean_llm_response(self, response: str) -> str:
        """清理LLM响应，移除markdown标记等"""
        import re
        
        # 移除markdown代码块标记
        cleaned = re.sub(r'```json\s*', '', response)
        cleaned = re.sub(r'```\s*$', '', cleaned)
        cleaned = re.sub(r'```\s*', '', cleaned)  # 移除单独的```
        
        # 移除前后的空白字符
        cleaned = cleaned.strip()
        
        return cleaned
    
    def _extract_json_from_response(self, response: str) -> Optional[str]:
        """从响应中提取JSON"""
        import re
        
        # 首先尝试清理markdown格式
        cleaned = self._clean_llm_response(response)
        
        # 尝试匹配JSON对象（包含plans字段）
        json_pattern = r'\{[^{}]*"plans"[^{}]*\{.*?\}.*?\}'
        match = re.search(json_pattern, cleaned, re.DOTALL)
        
        if match:
            return match.group(0)
        
        # 尝试匹配简单的JSON对象
        simple_json_pattern = r'\{.*?\}'
        match = re.search(simple_json_pattern, cleaned, re.DOTALL)
        
        if match:
            return match.group(0)
        
        # 尝试匹配JSON数组
        array_pattern = r'\[.*?\]'
        match = re.search(array_pattern, cleaned, re.DOTALL)
        
        if match:
            return match.group(0)
        
        return None
    
    def _format_data_for_llm(self, data: List[Dict[str, Any]], data_type: str) -> str:
        """格式化数据供LLM使用"""
        if not data:
            return "暂无数据"
        
        formatted_items = []
        for i, item in enumerate(data[:10]):  # 限制数量，避免prompt过长
            if data_type == 'flight':
                # 格式化时间显示
                departure_time = item.get('departure_time', 'N/A')
                arrival_time = item.get('arrival_time', 'N/A')
                if departure_time != 'N/A' and 'T' in departure_time:
                    departure_time = departure_time.split('T')[1][:5]  # 只显示时间部分 HH:MM
                if arrival_time != 'N/A' and 'T' in arrival_time:
                    arrival_time = arrival_time.split('T')[1][:5]  # 只显示时间部分 HH:MM
                
                # 格式化价格显示
                price_display = "N/A"
                if item.get('price_cny'):
                    price_display = f"{item.get('price_cny')}元"
                elif item.get('price'):
                    currency = item.get('currency', 'CNY')
                    price_display = f"{item.get('price')}{currency}"
                
                # 中转信息
                stops = item.get('stops', 0)
                stops_text = "直飞" if stops == 0 else f"{stops}次中转"
                
                formatted_items.append(f"""
  {i+1}. 航班号: {item.get('flight_number', 'N/A')}
     航空公司: {item.get('airline_name', item.get('airline', 'N/A'))}
     出发时间: {departure_time}
     到达时间: {arrival_time}
     飞行时长: {item.get('duration', 'N/A')}
     价格: {price_display}
     舱位等级: {item.get('cabin_class', 'N/A')}
     中转情况: {stops_text}
     出发机场: {item.get('origin', 'N/A')}
     到达机场: {item.get('destination', 'N/A')}
     行李额度: {item.get('baggage_allowance', 'N/A')}""")
            
            elif data_type == 'hotel':
                formatted_items.append(f"""
  {i+1}. 酒店名称: {item.get('name', 'N/A')}
     地址: {item.get('address', 'N/A')}
     每晚价格: {item.get('price_per_night', 'N/A')}元
     评分: {item.get('rating', 'N/A')}
     设施: {', '.join(item.get('amenities', []))}
     星级: {item.get('star_rating', 'N/A')}""")
            
            elif data_type == 'attraction':
                # 增强景点信息格式化，包含百度地图的详细信息
                formatted_items.append(f"""
  {i+1}. 景点名称: {item.get('name', 'N/A')}
     类型: {item.get('category', 'N/A')}
     描述: {item.get('description', 'N/A')}
     门票价格: {item.get('price', 'N/A')}元
     评分: {item.get('rating', 'N/A')}
     地址: {item.get('address', 'N/A')}
     开放时间: {item.get('opening_hours', 'N/A')}
     建议游览时间: {item.get('visit_duration', 'N/A')}
     特色标签: {', '.join(item.get('tags', []))}
     联系方式: {item.get('phone', 'N/A')}
     官方网站: {item.get('website', 'N/A')}
     交通便利性: {item.get('accessibility', 'N/A')}
     数据来源: {item.get('source', 'N/A')}""")
            
            elif data_type == 'restaurant':
                formatted_items.append(f"""
  {i+1}. 餐厅名称: {item.get('name', 'N/A')}
     菜系: {item.get('cuisine', 'N/A')}
     参考消费: {item.get('price_range', '价格未知')}
     评分: {item.get('rating', 'N/A')}
     地址: {item.get('address', 'N/A')}
     特色菜: {', '.join(item.get('specialties', []))}""")
            
            elif data_type == 'transportation':
                # 增强交通信息格式化，包含百度地图的详细信息
                formatted_items.append(f"""
  {i+1}. 交通方式: {item.get('type', 'N/A')}
     名称: {item.get('name', 'N/A')}
     描述: {item.get('description', 'N/A')}
     距离: {item.get('distance', 'N/A')}公里
     耗时: {item.get('duration', 'N/A')}分钟
     费用: {item.get('price', item.get('cost', 'N/A'))}元
     货币: {item.get('currency', 'CNY')}
     运营时间: {item.get('operating_hours', 'N/A')}
     发车频率: {item.get('frequency', 'N/A')}
     覆盖区域: {', '.join(item.get('coverage', []))}
     特色功能: {', '.join(item.get('features', []))}
     路线: {item.get('route', 'N/A')}
     数据来源: {item.get('source', 'N/A')}
     路况信息: {self._format_traffic_info(item.get('traffic_conditions', {}))}""")
        
        return '\n'.join(formatted_items) if formatted_items else "暂无数据"
    
    def _format_xiaohongshu_data_for_prompt(self, notes_data: List[Dict[str, Any]], destination: str) -> str:
        """
        将小红书数据格式化为适合LLM提示的文本
        
        Args:
            notes_data: 小红书笔记数据列表
            destination: 目的地名称
            
        Returns:
            str: 格式化后的文本
        """
        try:
            if not notes_data:
                return f"暂无{destination}的小红书用户分享数据"
            
            # 使用数据收集器的格式化方法
            return self.data_collector.format_xiaohongshu_data_for_llm(destination, notes_data)
            
        except Exception as e:
            logger.error(f"格式化小红书数据失败: {e}")
            return f"小红书数据格式化失败，但收集到 {len(notes_data)} 条相关笔记"
    
    def _format_traffic_info(self, traffic_conditions: Dict[str, Any]) -> str:
        """格式化路况信息"""
        if not traffic_conditions:
            return "暂无路况信息"
        
        info_parts = []
        
        # 拥堵程度
        congestion_level = traffic_conditions.get('congestion_level', '未知')
        if congestion_level != '未知':
            info_parts.append(f"拥堵程度: {congestion_level}")
        
        # 道路状况
        road_conditions = traffic_conditions.get('road_conditions', [])
        if road_conditions:
            info_parts.append(f"道路状况: {', '.join(road_conditions)}")
        
        # 实时信息
        real_time = traffic_conditions.get('real_time', False)
        if real_time:
            info_parts.append("实时路况: 是")
        
        return ', '.join(info_parts) if info_parts else "暂无路况信息"
    
    def _format_weather_info(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化天气信息"""
        if not weather_data:
            return {
                "raw_data": {},
                "travel_recommendations": ["暂无天气数据，建议出行前查看最新天气预报"]
            }
        
        # 生成基于天气的旅游建议
        recommendations = []
        
        # 检查温度
        temp = weather_data.get('temperature')
        if temp:
            if isinstance(temp, (int, float)):
                if temp < 10:
                    recommendations.append("气温较低，建议穿着保暖衣物，携带外套")
                elif temp > 30:
                    recommendations.append("气温较高，建议穿着轻薄透气衣物，注意防晒")
                else:
                    recommendations.append("气温适宜，建议穿着舒适的休闲服装")
        
        # 检查天气状况
        weather_desc = weather_data.get('weather', '').lower()
        if '雨' in weather_desc or 'rain' in weather_desc:
            recommendations.append("有降雨，建议携带雨具，选择室内景点或有遮蔽的活动")
        elif '雪' in weather_desc or 'snow' in weather_desc:
            recommendations.append("有降雪，注意保暖防滑，选择适合雪天的活动")
        elif '晴' in weather_desc or 'sunny' in weather_desc:
            recommendations.append("天气晴朗，适合户外活动和观光，注意防晒")
        elif '云' in weather_desc or 'cloud' in weather_desc:
            recommendations.append("多云天气，适合各种户外活动，光线柔和适合拍照")
        
        # 检查湿度
        humidity = weather_data.get('humidity')
        if humidity and isinstance(humidity, (int, float)):
            if humidity > 80:
                recommendations.append("湿度较高，建议选择透气性好的衣物")
            elif humidity < 30:
                recommendations.append("湿度较低，注意补水保湿")
        
        # 检查风力
        wind_speed = weather_data.get('wind_speed')
        if wind_speed and isinstance(wind_speed, (int, float)):
            if wind_speed > 20:
                recommendations.append("风力较大，户外活动时注意安全，避免高空项目")
        
        # 如果没有生成任何建议，添加默认建议
        if not recommendations:
            recommendations.append("建议根据当地天气情况合理安排行程")
        
        return {
            "raw_data": weather_data,
            "travel_recommendations": recommendations
        }
    
    async def _generate_single_plan(
        self,
        processed_data: Dict[str, Any],
        plan: Any,
        preferences: Optional[Dict[str, Any]],
        plan_type: str,
        plan_index: int,
        raw_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """生成单个方案"""
        try:
            # 选择最佳航班
            flight = self._select_best_flight(processed_data.get("flights", []), plan_type)
            
            # 选择最佳酒店
            hotel = self._select_best_hotel(processed_data.get("hotels", []), plan_type)
            
            # 生成每日行程（传递小红书数据）
            daily_itineraries = await self._generate_daily_itineraries(
                processed_data, plan, preferences, plan_type, raw_data
            )
            
            # 选择餐厅
            restaurants = self._select_restaurants(
                processed_data.get("restaurants", []), plan_type, len(daily_itineraries)
            )
            
            # 选择交通方式
            transportation = self._select_transportation(
                processed_data.get("transportation", [])
            )
            
            # 构造住宿信息用于费用计算
            accommodation = {
                "total_accommodation_cost": {
                    "flight": flight.get("price", 0) if flight else 0,
                    "hotel": hotel.get("price_per_night", 0) * plan.duration_days if hotel else 0
                }
            }
            
            # 计算总预算
            total_cost = self._calculate_total_cost(
                accommodation, daily_itineraries, plan.duration_days
            )
            
            # 获取天气信息
            weather_info = self._format_weather_info(processed_data.get("weather", {}))
            
            # 获取目的地坐标信息
            destination_info = await self._extract_destination_info(processed_data, plan.destination)
            
            plan_data: Dict[str, Any] = {
                "id": f"plan_{plan_index}",
                "type": plan_type,
                "title": f"{plan.destination} {plan_type}旅行方案",
                "description": f"精心为您打造的{plan_type}旅行方案",
                "flight": flight,
                "hotel": hotel,
                "daily_itineraries": daily_itineraries,
                "restaurants": restaurants,
                "transportation": transportation,
                "total_cost": total_cost,
                "weather_info": weather_info,
                "destination_info": destination_info,
                "duration_days": plan.duration_days,
                "generated_at": datetime.utcnow().isoformat(),
                "xiaohongshu_notes": (raw_data.get("xiaohongshu_notes", []) if raw_data else [])
            }
            
            # 在方案内按天去重景点，避免同一景点多日重复
            self._deduplicate_daily_attractions(plan_data)

            logger.warning(f"生成单个方案成功: {plan_data}")

            return plan_data
            
        except Exception as e:
            logger.error(f"生成单个方案失败: {e}")
            return None
    
    def _select_best_flight(self, flights: List[Dict[str, Any]], plan_type: str) -> Optional[Dict[str, Any]]:
        """选择最佳航班"""
        if not flights:
            return None
        
        # 根据方案类型选择航班
        if plan_type == "经济实惠型":
            # 选择最便宜的航班
            return min(flights, key=lambda x: x.get("price", float('inf')))
        elif plan_type == "舒适享受型":
            # 选择评分最高的航班
            return max(flights, key=lambda x: x.get("rating", 0))
        else:
            # 随机选择
            return random.choice(flights)
    
    def _select_best_hotel(self, hotels: List[Dict[str, Any]], plan_type: str) -> Optional[Dict[str, Any]]:
        """选择最佳酒店"""
        if not hotels:
            return None
        
        # 根据方案类型选择酒店
        if plan_type == "经济实惠型":
            return min(hotels, key=lambda x: x.get("price_per_night", float('inf')))
        elif plan_type == "舒适享受型":
            return max(hotels, key=lambda x: x.get("rating", 0))
        else:
            return random.choice(hotels)
    
    async def _generate_daily_itineraries(
        self,
        processed_data: Dict[str, Any],
        plan: Any,
        preferences: Optional[Dict[str, Any]],
        plan_type: str,
        raw_data: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """使用LLM基于小红书内容生成每日行程"""
        try:
            # 获取小红书笔记数据
            xiaohongshu_notes = raw_data.get('xiaohongshu_notes', []) if raw_data else []
            
            # 如果有小红书数据，使用LLM生成行程
            if xiaohongshu_notes:
                return await self._generate_daily_itineraries_with_llm(
                    processed_data, plan, preferences, plan_type, xiaohongshu_notes
                )
            else:
                # 回退到原有逻辑
                return await self._generate_daily_itineraries_fallback(
                    processed_data, plan, preferences, plan_type
                )
                
        except Exception as e:
            logger.error(f"生成每日行程失败: {e}")
            # 出错时使用回退逻辑
            return await self._generate_daily_itineraries_fallback(
                processed_data, plan, preferences, plan_type
            )

    async def _generate_daily_itineraries_with_llm(
        self,
        processed_data: Dict[str, Any],
        plan: Any,
        preferences: Optional[Dict[str, Any]],
        plan_type: str,
        xiaohongshu_notes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """使用LLM基于小红书内容生成每日行程"""
        try:
            system_prompt = f"""你是一个专业的旅行规划师，需要基于真实的小红书用户分享内容来制定详细的每日旅行行程。

请根据以下信息生成{plan.duration_days}天的详细行程安排：

要求：
1. 每天的行程要合理安排时间，包含上午、下午、晚上的活动，并保证时间段之间没有重叠； 
2. 景点安排要考虑地理位置，优化游览路线，避免在一天内安排相距很远、需要长时间往返通勤的景点；
3. 对于确实相距较远的景点，需要在行程中明确标注通勤耗时，并适当减少当日景点数量；
4. 结合小红书用户的真实体验和建议，优先选择评价好、体验真实的景点和餐厅；
5. 包含具体的时间安排、交通方式、预估费用；
6. 为每个景点/活动提供详细的游览建议和注意事项；
7. 同一景点名称在整个{plan.duration_days}天行程中只能出现一次，不要在不同日期重复安排同一个景点；
8. 根据方案类型({plan_type})调整活动强度和选择，避免对某一天安排过于疲劳的行程。

返回JSON格式，结构如下：
[
  {{
    "day": 1,
    "date": "2024-01-01",
    "theme": "行程主题",
    "activities": [
      {{
        "time": "09:00-11:00",
        "type": "景点",
        "name": "景点名称",
        "description": "详细描述和游览建议",
        "location": "具体地址",
        "transportation": "交通方式",
        "estimated_cost": 50,
        "tips": "实用小贴士"
      }}
    ],
    "meals": [
      {{
        "time": "12:00-13:00",
        "type": "午餐",
        "name": "餐厅名称",
        "description": "推荐菜品和特色",
        "estimated_cost": 80
      }}
    ],
    "total_estimated_cost": 200
  }}
]"""

            num_people = (
                getattr(plan, "num_people", None)
                or getattr(plan, "travelers", None)
                or (preferences or {}).get("travelers")
            )
            age_group = getattr(plan, "age_group", None) or (preferences or {}).get("ageGroups")
            budget_info = getattr(plan, "budget", None) or (preferences or {}).get("budget")
            start_date = getattr(plan, "start_date", None) or "未指定"
            duration_days = getattr(plan, "duration_days", None) or (preferences or {}).get("duration_days")

            user_prompt = f"""旅行信息：
目的地：{plan.destination}
旅行天数：{duration_days or '未指定'}天
开始日期：{start_date}
旅行人数：{num_people or '未指定'}人
年龄群体：{age_group or '未指定'}
预算范围：{budget_info or '未指定'}
方案类型：{plan_type}
特殊要求：{plan.requirements or '无特殊要求'}
用户偏好：{preferences or '无特殊偏好'}

小红书真实用户体验分享：
{self._format_xiaohongshu_data_for_prompt(xiaohongshu_notes, plan.destination)}

可用景点数据（作为参考）：
{self._format_data_for_llm(processed_data.get('attractions', []), 'attraction')}

请基于小红书用户的真实体验和建议，生成详细的每日行程安排。优先采用小红书中提到的景点、餐厅和活动，确保行程的真实性和可操作性。

请直接返回JSON格式结果。"""

            logger.info(f"使用LLM生成每日行程，目的地: {plan.destination}, 天数: {plan.duration_days}")

            response = await openai_client.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=0.7
            )

            cleaned_response = self._clean_llm_response(response)
            try:
                result = json.loads(cleaned_response)
            except json.JSONDecodeError:
                logger.warning(f"LLM生成每日行程失败，返回结果格式不正确，使用回退逻辑")
                return await self._generate_daily_itineraries_fallback(
                    processed_data, plan, preferences, plan_type
                )
            
            if not isinstance(result, list) or len(result) != plan.duration_days:
                logger.warning("每日行程返回格式不正确，使用回退逻辑")
                return await self._generate_daily_itineraries_fallback(
                    processed_data, plan, preferences, plan_type
                )
                
            logger.info(f"成功生成{len(result)}天的LLM行程")
            return result

        except Exception as e:
            logger.error(f"LLM生成每日行程失败: {e}")
            return await self._generate_daily_itineraries_fallback(
                processed_data, plan, preferences, plan_type
            )

    async def _generate_daily_itineraries_fallback(
        self,
        processed_data: Dict[str, Any],
        plan: Any,
        preferences: Optional[Dict[str, Any]],
        plan_type: str
    ) -> List[Dict[str, Any]]:
        """回退的每日行程生成逻辑（原有逻辑）"""
        attractions = processed_data.get("attractions", [])
        daily_itineraries = []
        
        # 根据方案类型筛选景点
        filtered_attractions = self._filter_attractions_by_type(attractions, plan_type)
        
        # 按天数分配景点
        attractions_per_day = len(filtered_attractions) // plan.duration_days
        remaining_attractions = len(filtered_attractions) % plan.duration_days
        
        start_date = plan.start_date
        
        for day in range(plan.duration_days):
            day_attractions = attractions_per_day
            if day < remaining_attractions:
                day_attractions += 1
            
            # 选择当天的景点
            day_attraction_list = filtered_attractions[
                day * attractions_per_day:(day + 1) * attractions_per_day
            ]
            
            if day < remaining_attractions:
                day_attraction_list.append(filtered_attractions[
                    plan.duration_days * attractions_per_day + day
                ])
            
            # 生成当日行程
            daily_itinerary = {
                "day": day + 1,
                "date": (start_date + timedelta(days=day)).isoformat(),
                "attractions": day_attraction_list,
                "meals": self._generate_daily_meals(day),
                "transportation": "地铁/公交",
                "estimated_cost": sum(attr.get("price", 0) for attr in day_attraction_list)
            }
            
            daily_itineraries.append(daily_itinerary)
        
        return daily_itineraries
    
    def _filter_attractions_by_type(
        self, 
        attractions: List[Dict[str, Any]], 
        plan_type: str
    ) -> List[Dict[str, Any]]:
        """根据方案类型筛选景点"""
        type_mapping = {
            "经济实惠型": ["免费", "便宜", "公园", "广场"],
            "舒适享受型": ["豪华", "高端", "度假村", "水疗"],
            "文化深度型": ["博物馆", "历史", "文化", "古迹"],
            "自然风光型": ["自然", "公园", "山", "湖", "海"],
            "美食体验型": ["美食", "餐厅", "市场", "小吃"]
        }
        
        keywords = type_mapping.get(plan_type, [])
        
        if not keywords:
            return attractions
        
        filtered = []
        for attraction in attractions:
            name = attraction.get("name", "").lower()
            category = attraction.get("category", "").lower()
            description = attraction.get("description", "").lower()
            
            if any(keyword in name or keyword in category or keyword in description 
                   for keyword in keywords):
                filtered.append(attraction)
        
        # 如果筛选结果太少，返回原始列表
        return filtered if len(filtered) >= 3 else attractions
    
    def _generate_daily_meals(self, day: int) -> List[Dict[str, Any]]:
        """生成每日餐饮安排"""
        meals = [
            {
                "type": "早餐",
                "time": "08:00",
                "suggestion": "酒店早餐或当地特色早餐"
            },
            {
                "type": "午餐", 
                "time": "12:00",
                "suggestion": "当地特色餐厅"
            },
            {
                "type": "晚餐",
                "time": "18:00", 
                "suggestion": "推荐餐厅或特色小吃"
            }
        ]
        
        return meals
    
    def _select_restaurants(
        self, 
        restaurants: List[Dict[str, Any]], 
        plan_type: str, 
        num_days: int
    ) -> List[Dict[str, Any]]:
        """选择餐厅"""
        if not restaurants:
            return []
        
        # 根据方案类型选择餐厅
        if plan_type == "经济实惠型":
            selected = sorted(restaurants, key=lambda x: extract_price_value(x))[:num_days]
        elif plan_type == "美食体验型":
            selected = sorted(restaurants, key=lambda x: x.get("rating", 0), reverse=True)[:num_days]
        else:
            selected = random.sample(restaurants, min(num_days, len(restaurants)))
        
        return selected
    
    def _select_transportation(self, transportation: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """选择交通方式"""
        if not transportation:
            return []
        
        # 选择最常用的交通方式
        return transportation[:3]  # 返回前3种交通方式
    

    
    async def refine_plan(
        self, 
        current_plan: Dict[str, Any], 
        refinements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """细化方案"""
        try:
            refined_plan = current_plan.copy()
            
            # 应用细化要求
            if "budget_adjustment" in refinements:
                refined_plan = self._adjust_budget(refined_plan, refinements["budget_adjustment"])
            
            if "time_preference" in refinements:
                refined_plan = self._adjust_timing(refined_plan, refinements["time_preference"])
            
            if "activity_preference" in refinements:
                refined_plan = self._adjust_activities(refined_plan, refinements["activity_preference"])
            
            refined_plan["refined_at"] = datetime.utcnow().isoformat()
            refined_plan["refinements"] = refinements
            
            return refined_plan
            
        except Exception as e:
            logger.error(f"细化方案失败: {e}")
            return current_plan
    
    def _adjust_budget(self, plan: Dict[str, Any], adjustment: str) -> Dict[str, Any]:
        """调整预算"""
        # 实现预算调整逻辑
        return plan
    
    def _adjust_timing(self, plan: Dict[str, Any], preference: str) -> Dict[str, Any]:
        """调整时间安排"""
        # 实现时间调整逻辑
        return plan
    
    def _adjust_activities(self, plan: Dict[str, Any], preference: str) -> Dict[str, Any]:
        """调整活动安排"""
        # 实现活动调整逻辑
        return plan
    
    async def generate_recommendations(self, plan: Any) -> List[Dict[str, Any]]:
        """生成推荐"""
        recommendations = [
            {
                "type": "天气提醒",
                "content": "建议关注当地天气预报，合理安排户外活动",
                "priority": "high"
            },
            {
                "type": "交通建议",
                "content": "建议提前预订热门景点门票，避免排队等待",
                "priority": "medium"
            },
            {
                "type": "安全提醒",
                "content": "请保管好个人物品，注意人身安全",
                "priority": "high"
            }
        ]
        
        return recommendations
    
    async def _extract_destination_info(self, processed_data: Dict[str, Any], destination: str) -> Dict[str, Any]:
        """提取目的地坐标信息"""
        try:
            # 优先使用data_collector的统一地理编码函数获取准确坐标
            try:
                geocode_info = await self.data_collector.get_destination_geocode_info(destination)
                if geocode_info:
                    logger.info(f"使用统一地理编码获取目的地坐标: {destination}")
                    return {
                        "name": geocode_info['destination'],
                        "latitude": geocode_info['latitude'],
                        "longitude": geocode_info['longitude'],
                        "source": f"geocode_{geocode_info['provider']}",
                        "formatted_address": geocode_info.get('formatted_address', destination)
                    }
            except Exception as e:
                logger.warning(f"统一地理编码获取失败，回退到从数据中提取: {e}")
            
            # 回退方案：从处理后的数据中提取坐标信息
            # 首先尝试从景点数据中获取坐标（景点通常在目的地附近）
            attractions = processed_data.get("attractions", [])
            if attractions:
                # 使用第一个景点的坐标作为目的地坐标
                first_attraction = attractions[0]
                coordinates = first_attraction.get("coordinates")
                if coordinates and isinstance(coordinates, dict):
                    lat = coordinates.get("lat")
                    lng = coordinates.get("lng")
                    if lat is not None and lng is not None:
                        return {
                            "name": destination,
                            "latitude": lat,
                            "longitude": lng,
                            "source": "attractions"
                        }
                # 兼容直接的latitude/longitude字段
                elif "latitude" in first_attraction and "longitude" in first_attraction:
                    return {
                        "name": destination,
                        "latitude": first_attraction["latitude"],
                        "longitude": first_attraction["longitude"],
                        "source": "attractions"
                    }
            
            # 如果景点数据中没有坐标，尝试从酒店数据中获取
            hotels = processed_data.get("hotels", [])
            if hotels:
                first_hotel = hotels[0]
                coordinates = first_hotel.get("coordinates")
                if coordinates and isinstance(coordinates, dict):
                    lat = coordinates.get("lat")
                    lng = coordinates.get("lng")
                    if lat is not None and lng is not None:
                        return {
                            "name": destination,
                            "latitude": lat,
                            "longitude": lng,
                            "source": "hotels"
                        }
                # 兼容直接的latitude/longitude字段
                elif "latitude" in first_hotel and "longitude" in first_hotel:
                    return {
                        "name": destination,
                        "latitude": first_hotel["latitude"],
                        "longitude": first_hotel["longitude"],
                        "source": "hotels"
                    }
            
            # 如果都没有，尝试从餐厅数据中获取
            restaurants = processed_data.get("restaurants", [])
            if restaurants:
                first_restaurant = restaurants[0]
                coordinates = first_restaurant.get("coordinates")
                if coordinates and isinstance(coordinates, dict):
                    lat = coordinates.get("lat")
                    lng = coordinates.get("lng")
                    if lat is not None and lng is not None:
                        return {
                            "name": destination,
                            "latitude": lat,
                            "longitude": lng,
                            "source": "restaurants"
                        }
                # 兼容直接的latitude/longitude字段
                elif "latitude" in first_restaurant and "longitude" in first_restaurant:
                    return {
                        "name": destination,
                        "latitude": first_restaurant["latitude"],
                        "longitude": first_restaurant["longitude"],
                        "source": "restaurants"
                    }
            
            # 如果所有数据都没有坐标，返回默认坐标（北京）
            logger.warning(f"无法获取目的地 {destination} 的坐标信息，使用默认坐标")
            return {
                "name": destination,
                "latitude": 39.9042,
                "longitude": 116.4074,
                "source": "default"
            }
            
        except Exception as e:
            logger.error(f"提取目的地坐标信息失败: {e}")
            return {
                "name": destination,
                "latitude": 39.9042,
                "longitude": 116.4074,
                "source": "error_fallback"
            }

    # ==================== 模块化LLM生成器方法 ====================
    
    @retry_with_backoff(max_retries=3, base_delay=2.0)
    async def _generate_accommodation_plans(
        self,
        hotels_data: List[Dict[str, Any]],
        flights_data: List[Dict[str, Any]],
        plan: Any,
        preferences: Optional[Dict[str, Any]] = None,
        raw_data: Optional[Dict[str, Any]] = None,
        *,
        is_international: bool = False,
    ) -> List[Dict[str, Any]]:
        """生成住宿方案（按天拆分）"""
        try:
            total_days = max(int(getattr(plan, "duration_days", 0) or 1), 1)
            per_day_budget = self._get_per_day_budget(plan)
            notes_str = self._format_xiaohongshu_data_for_prompt(
                raw_data.get("xiaohongshu_notes", []) if raw_data else [], plan.destination
            )

            def build_prompts(day: int, date_str: str, daily_budget: Optional[float]):
                budget_info = (
                    f"{daily_budget:.0f}元" if isinstance(daily_budget, (int, float)) else "未指定"
                )
                intl_hint = ""
                if is_international:
                    intl_hint = (
                        "\n注意：目的地为海外，如下方航班/酒店数据为空或可能不准确，请重点依据小红书真实体验，并提醒用户抵达后再确认住宿信息。"
                    )
                system_prompt = (
                    "你是一位住宿规划师，请针对某一天给出航班（如有）与酒店安排，"
                    "需结合真实航班/酒店数据输出结构化结果。"
                )
                user_prompt = f"""
请为如下旅行生成第 {day} 天（日期：{date_str or '未提供'}）的住宿安排：
- 目的地：{plan.destination}
- 人数：{(preferences or {}).get('travelers', getattr(plan, 'travelers', 1))}
- 当日预算：{budget_info}
- 年龄群体：{', '.join((preferences or {}).get('ageGroups', [])) if (preferences or {}).get('ageGroups') else '未指定'}
- 饮食偏好：{', '.join((preferences or {}).get('foodPreferences', [])) if (preferences or {}).get('foodPreferences') else '无特殊偏好'}
- 饮食禁忌：{', '.join((preferences or {}).get('dietaryRestrictions', [])) if (preferences or {}).get('dietaryRestrictions') else '无'}
- 活动偏好：{', '.join((preferences or {}).get('activity_preference', [])) if (preferences or {}).get('activity_preference') else '未指定'}
- 特殊要求：{plan.requirements or '无'}

可用航班数据：
{self._format_data_for_llm(flights_data, 'flight')}

可用酒店数据：
{self._format_data_for_llm(hotels_data, 'hotel')}

小红书住宿体验：
{notes_str}

{intl_hint}

请返回JSON对象，包含字段{{
  "day": {day},
  "date": "{date_str}",
  "flight": {{}},
  "hotel": {{}},
  "daily_cost": 参考费用,
  "accommodation_highlights": ["亮点1", "亮点2"],
  "notes": ["提示1", "提示2"]
}}，必须使用提供数据。"""
                return system_prompt, user_prompt, min(settings.OPENAI_MAX_TOKENS, 1100), 0.65

            def post_process(entry: Dict[str, Any], day: int, date_str: str) -> Dict[str, Any]:
                entry.setdefault("flight", {})
                entry.setdefault("hotel", {})
                entry.setdefault("daily_cost", 0)
                entry.setdefault("accommodation_highlights", [])
                entry.setdefault("notes", [])
                return entry

            daily_entries = await generate_daily_entries(
                module_name="住宿方案",
                total_days=total_days,
                start_date=getattr(plan, "start_date", None),
                per_day_budget=per_day_budget,
                build_prompts=build_prompts,
                llm_requester=self._request_llm_json,
                fallback_builder=lambda d, date: build_simple_accommodation_day(
                    d, date, hotels_data
                ),
                post_process=post_process,
            )
            if not daily_entries:
                return []

            total_hotel_cost = sum(
                entry.get("daily_cost", 0) for entry in daily_entries if isinstance(entry, dict)
            )
            first_flight = next(
                (entry.get("flight") for entry in daily_entries if entry.get("flight")), {}
            )
            first_hotel = next(
                (entry.get("hotel") for entry in daily_entries if entry.get("hotel")), {}
            )

            aggregated_plan = {
                "type": "综合住宿方案",
                "flight": first_flight,
                "hotel": first_hotel,
                "daily_accommodation": daily_entries,
                "total_accommodation_cost": {
                    "flight": first_flight.get("price", 0),
                    "hotel": total_hotel_cost,
                    "total": (first_flight.get("price", 0) or 0) + total_hotel_cost,
                },
                "accommodation_highlights": [
                    highlight
                    for entry in daily_entries
                    for highlight in entry.get("accommodation_highlights", [])
                ],
            }
            logger.info(f"生成住宿方案天数: {len(daily_entries)}")
            return [aggregated_plan]

        except Exception as e:
            logger.error(f"生成住宿方案失败: {e}")
            return []

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    async def _generate_dining_plans(
        self,
        restaurants_data: List[Dict[str, Any]],
        plan: Any,
        preferences: Optional[Dict[str, Any]] = None,
        raw_data: Optional[Dict[str, Any]] = None,
        *,
        is_international: bool = False,
    ) -> List[Dict[str, Any]]:
        """生成餐饮方案（按天）"""
        try:
            total_days = max(int(getattr(plan, "duration_days", 0) or 1), 1)
            per_day_budget = self._get_per_day_budget(plan)
            notes_str = self._format_xiaohongshu_data_for_prompt(
                raw_data.get("xiaohongshu_notes", []) if raw_data else [], plan.destination
            )

            def build_prompts(day: int, date_str: str, daily_budget: Optional[float]):
                budget_info = (
                    f"{daily_budget:.0f}元" if isinstance(daily_budget, (int, float)) else "未指定"
                )
                intl_hint = ""
                if is_international:
                    intl_hint = (
                        "\n注意：目的地为海外，小红书美食体验是主要依据。若餐厅数据缺失，请结合笔记与通用经验推荐，并提示用户现场确认具体商家。"
                    )
                system_prompt = (
                    "你是一位美食规划师，请针对某一天制定详细的早餐/午餐/晚餐安排，"
                    "需结合真实餐厅数据与小红书体验，输出结构化结果。"
                )
                user_prompt = f"""
请为如下旅行生成第 {day} 天（日期：{date_str or '未提供'}）的餐饮方案：
- 目的地：{plan.destination}
- 当日预算：{budget_info}
- 人数：{(preferences or {}).get('travelers', getattr(plan, 'travelers', 1))}
- 年龄群体：{', '.join((preferences or {}).get('ageGroups', [])) if (preferences or {}).get('ageGroups') else '未指定'}
- 饮食偏好：{', '.join((preferences or {}).get('foodPreferences', [])) if (preferences or {}).get('foodPreferences') else '无特殊偏好'}
- 饮食禁忌：{', '.join((preferences or {}).get('dietaryRestrictions', [])) if (preferences or {}).get('dietaryRestrictions') else '无'}

可用餐厅数据：
{self._format_data_for_llm(restaurants_data, 'restaurant')}

小红书真实用户美食分享：
{notes_str}

{intl_hint}

请返回JSON对象，字段与示例一致：{{
  "day": {day},
  "meals": [
    {{
      "type": "早餐/午餐/晚餐",
      "time": "08:00-09:00",
      "restaurant_name": "餐厅名称",
      "cuisine": "菜系",
      "recommended_dishes": [...],
      "estimated_cost": 参考费用,
      "booking_tips": "预订建议",
      "address": "地址"
    }}
  ],
  "daily_food_cost": 当日总费用,
  "food_highlights": ["亮点1", "亮点2"]
}}
务必使用提供的数据并包含实用口味描述。"""
                return system_prompt, user_prompt, min(settings.OPENAI_MAX_TOKENS, 1000), 0.65

            def post_process(entry: Dict[str, Any], day: int, date_str: str) -> Dict[str, Any]:
                entry.setdefault("meals", [])
                entry.setdefault("food_highlights", [])
                entry.setdefault("daily_food_cost", 0)
                return entry

            return await generate_daily_entries(
                module_name="餐饮方案",
                total_days=total_days,
                start_date=getattr(plan, "start_date", None),
                per_day_budget=per_day_budget,
                build_prompts=build_prompts,
                llm_requester=self._request_llm_json,
                fallback_builder=lambda d, date: build_simple_dining_plan(
                    d, date, restaurants_data
                ),
                post_process=post_process,
            )

        except Exception as e:
            logger.error(f"生成餐饮方案失败: {e}")
            return []

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    async def _generate_transportation_plans(
        self,
        transportation_data: List[Dict[str, Any]],
        plan: Any,
        preferences: Optional[Dict[str, Any]] = None,
        raw_data: Optional[Dict[str, Any]] = None,
        *,
        is_international: bool = False,
    ) -> List[Dict[str, Any]]:
        """生成交通方案（按天）"""
        try:
            total_days = max(int(getattr(plan, "duration_days", 0) or 1), 1)
            origin_city = self._extract_origin_city(plan)
            destination_city = getattr(plan, "destination", None) or "目的地"
            notes_str = self._format_xiaohongshu_data_for_prompt(
                raw_data.get("xiaohongshu_notes", []) if raw_data else [], plan.destination
            )

            def build_prompts(day: int, date_str: str, daily_budget: Optional[float]):
                stage = self._determine_transport_stage(day, total_days)
                stage_meta = self._build_transport_stage_instruction(
                    stage, origin_city, destination_city
                )
                intl_hint = ""
                if is_international:
                    intl_hint = (
                        "\n注意：目的地为海外，如缺乏可靠交通数据，可根据小红书笔记和常规经验给出交通建议，并提醒用户参考当地最新信息。"
                    )
                system_prompt = (
                    "你是一位交通规划师，请针对某一天提供详细的城市内交通安排，"
                    "包含路线、费用和注意事项。"
                )
                user_prompt = f"""
请为如下旅行生成第 {day} 天（日期：{date_str or '未提供'}）的交通方案：
- 行程阶段：{stage_meta['label']}
- 出发地：{origin_city}
- 目的地：{plan.destination}
- 出行方式偏好：{plan.transportation or '未指定'}
- 预算：{plan.budget or '未指定'}元
- 人数：{(preferences or {}).get('travelers', getattr(plan, 'travelers', 1))}
- 年龄群体：{', '.join((preferences or {}).get('ageGroups', [])) if (preferences or {}).get('ageGroups') else '未指定'}
- 活动偏好：{', '.join((preferences or {}).get('activity_preference', [])) if (preferences or {}).get('activity_preference') else '未指定'}

行程阶段要求：
{stage_meta['prompt']}

{intl_hint}

可用交通数据：
{self._format_data_for_llm(transportation_data, 'transportation')}

小红书真实交通攻略：
{notes_str}

请输出严格的JSON对象（禁止附加说明文字）：{{
  "day": {day},
  "date": "{date_str}",
  "primary_routes": [
    {{
      "type": "交通方式",
      "name": "名称",
      "route": "起点→途经→终点",
      "duration": "耗时(分钟)",
      "distance": "距离(公里)",
      "price": 数字,
      "usage_tips": ["建议1", "注意2"]
    }}
  ],
  "backup_routes": [...],
  "daily_transport_cost": 数字,
  "tips": ["注意事项1", "注意事项2"]
}}

要求：
1. 所有数值字段（如 price、distance、duration、daily_transport_cost）必须是纯数字，单位默认元/公里/分钟。
2. 不得输出注释、额外文字或带单位的字符串；只返回合法JSON。
3. 务必使用提供的交通数据。"""
                return system_prompt, user_prompt, min(settings.OPENAI_MAX_TOKENS, 900), 0.6

            def post_process(entry: Dict[str, Any], day: int, date_str: str) -> Dict[str, Any]:
                entry.setdefault("primary_routes", [])
                entry.setdefault("backup_routes", [])
                entry.setdefault("tips", [])
                entry.setdefault("daily_transport_cost", 0)
                stage = self._determine_transport_stage(day, total_days)
                stage_meta = self._build_transport_stage_instruction(
                    stage, origin_city, destination_city
                )
                entry.setdefault("stage", stage)
                entry.setdefault("stage_label", stage_meta["label"])
                entry.setdefault("stage_hint", stage_meta["hint"])
                return self._normalize_transport_stage_routes(
                    entry, stage, origin_city, destination_city
                )

            return await generate_daily_entries(
                module_name="交通方案",
                total_days=total_days,
                start_date=getattr(plan, "start_date", None),
                per_day_budget=None,
                build_prompts=build_prompts,
                llm_requester=self._request_llm_json,
                fallback_builder=lambda d, date: build_simple_transportation_plan(
                    d,
                    date,
                    transportation_data,
                    stage=self._determine_transport_stage(d, total_days),
                    origin=origin_city,
                    destination=destination_city,
                ),
                post_process=post_process,
            )

        except Exception as e:
            logger.error(f"生成交通方案失败: {e}")
            return []

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    async def _generate_attraction_plans(
        self,
        attractions_data: List[Dict[str, Any]],
        plan: Any,
        preferences: Optional[Dict[str, Any]] = None,
        raw_data: Optional[Dict[str, Any]] = None,
        *,
        is_international: bool = False,
    ) -> List[Dict[str, Any]]:
        """按天生成景点游玩方案"""
        try:
            total_days = max(int(getattr(plan, "duration_days", 0) or len(attractions_data) or 1), 1)
            per_day_budget = self._get_per_day_budget(plan)
            notes_str = self._format_xiaohongshu_data_for_prompt(
                raw_data.get("xiaohongshu_notes", []) if raw_data else [], plan.destination
            )

            def build_prompts(day: int, date_str: str, daily_budget: Optional[float]):
                budget_info = (
                    f"{daily_budget:.0f}元" if isinstance(daily_budget, (int, float)) else "未指定"
                )
                intl_hint = ""
                if is_international:
                    intl_hint = (
                        "\n注意：目的地为海外，请优先结合小红书体验与真实景点数据，若缺少官方数据，请说明信息来源并提示用户现场确认。"
                    )
                system_prompt = (
                    "你是一位资深景点规划师，请针对某一天制定详细的景点游览安排，"
                    "需结合真实景点数据与小红书体验建议，输出结构化结果。\n"
                    "具体要求：\n"
                    "1. 一天内的景点尽量选择地理位置相近、动线顺路的组合，避免在城市中来回折返；\n"
                    "2. 对于相距较远、需要长时间通勤的景点，当天安排的景点数量要减少，并在行程中明确写出长途通勤时间；\n"
                    "3. 在时间轴上合理安排上午、下午和晚上的活动，避免时间重叠或不可能完成的安排；\n"
                    "4. 同一趟旅行中，一个景点不应在不同日期重复安排；\n"
                    "5. 优先使用提供的真实景点数据，不要凭空捏造不存在的地点。"
                )
                user_prompt = f"""
请为如下旅行生成第 {day} 天（日期：{date_str or '未提供'}）的景点游览方案：
- 目的地：{plan.destination}
- 当日预算：{budget_info}
- 人数：{(preferences or {}).get('travelers', getattr(plan, 'travelers', 1))}
- 年龄群体：{', '.join((preferences or {}).get('ageGroups', [])) if (preferences or {}).get('ageGroups') else '未指定'}
- 活动偏好：{', '.join((preferences or {}).get('activity_preference', [])) if (preferences or {}).get('activity_preference') else '未指定'}
- 饮食禁忌：{', '.join((preferences or {}).get('dietaryRestrictions', [])) if (preferences or {}).get('dietaryRestrictions') else '无'}
- 特殊要求：{plan.requirements or '无'}

真实景点数据：
{self._format_data_for_llm(attractions_data, 'attraction')}

小红书体验分享：
{notes_str}

{intl_hint}

请返回JSON对象，字段与示例一致：{{
  "day": {day},
  "date": "{date_str}",
  "schedule": [...],
  "attractions": [...],
  "estimated_cost": 参考费用,
  "daily_tips": [...]
}}
务必使用提供数据中的景点，并给出实用游览建议。"""
                return system_prompt, user_prompt, min(settings.OPENAI_MAX_TOKENS, 1200), 0.6

            def post_process(entry: Dict[str, Any], day: int, date_str: str) -> Dict[str, Any]:
                entry.setdefault("schedule", [])
                entry.setdefault("attractions", [])
                entry.setdefault("daily_tips", [])
                entry.setdefault("estimated_cost", 0)
                return entry

            return await generate_daily_entries(
                module_name="景点方案",
                total_days=total_days,
                start_date=getattr(plan, "start_date", None),
                per_day_budget=per_day_budget,
                build_prompts=build_prompts,
                llm_requester=self._request_llm_json,
                fallback_builder=lambda d, date: build_simple_attraction_plan(
                    d, date, attractions_data
                ),
                post_process=post_process,
            )

        except Exception as e:
            logger.error(f"生成景点方案失败: {e}")
            return []

    async def _assemble_travel_plans(
        self,
        accommodation_plans: List[Dict[str, Any]],
        dining_plans: List[Dict[str, Any]],
        transportation_plans: List[Dict[str, Any]],
        attraction_plans: List[Dict[str, Any]],
        processed_data: Dict[str, Any],
        plan: Any,
        *,
        is_international: bool = False,
    ) -> List[Dict[str, Any]]:
        """组装完整的旅行方案"""
        try:
            assembled_plans = []
            restaurant_lookup = self._build_lookup_map(processed_data.get("restaurants", []))
            hotel_lookup = self._build_lookup_map(processed_data.get("hotels", []))
            
            # 为每个住宿方案创建完整的旅行计划
            for i, accommodation in enumerate(accommodation_plans):
                try:
                    # 基础方案信息
                    travel_plan = {
                        "id": f"modular_plan_{i}",
                        "type": accommodation.get("type", f"方案{i+1}"),
                        "title": f"{accommodation.get('type', f'方案{i+1}')}的{plan.destination}之旅",
                        "description": f"精心规划的{plan.duration_days}天{plan.destination}旅行，包含优质住宿、特色美食、便捷交通和精彩景点。",
                        "duration_days": plan.duration_days,
                        "generated_at": datetime.utcnow().isoformat(),
                        "xiaohongshu_notes": processed_data.get("xiaohongshu_notes", [])
                    }
                    if is_international:
                        travel_plan["data_source_mode"] = "xiaohongshu_priority"
                        notes_list = travel_plan.setdefault("notes", [])
                        notes_list.append("目的地为海外，餐饮与住宿建议以小红书真实体验为主，建议出行前再次确认商家信息。")
                    
                    # 添加航班和酒店信息
                    travel_plan["flight"] = accommodation.get("flight", {})
                    travel_plan["hotel"] = self._merge_hotel_details(
                        accommodation.get("hotel", {}),
                        hotel_lookup
                    )
                    accommodation_daily = accommodation.get("daily_accommodation", [])
                    
                    # 构建每日行程
                    daily_itineraries = []
                    for day in range(1, plan.duration_days + 1):
                        # 确保day是整数
                        day_num = int(day)
                        # 确保日期计算正确
                        calculated_date = calculate_date(getattr(plan, "start_date", None), day_num - 1)
                        
                        daily_plan = {
                            "day": day_num,
                            "date": calculated_date,
                            "schedule": [],
                            "attractions": [],
                            "meals": [],
                            "transportation": {},
                            "estimated_cost": 0,  # 确保是整数
                            "daily_tips": []
                        }
                        
                        # 添加景点安排
                        day_attractions = self._get_day_attractions(attraction_plans, day_num)
                        if day_attractions:
                            # 确保schedule是列表
                            attraction_schedule = day_attractions.get("schedule", [])
                            if isinstance(attraction_schedule, list):
                                daily_plan["schedule"].extend(attraction_schedule)
                            raw_attractions = day_attractions.get("attractions", [])
                            if isinstance(raw_attractions, list):
                                normalized_attractions = []
                                for attr in raw_attractions:
                                    if isinstance(attr, dict):
                                        normalized_attractions.append(attr)
                                    elif attr not in (None, ""):
                                        normalized_attractions.append({"name": attr})
                                daily_plan["attractions"] = normalized_attractions
                            else:
                                daily_plan["attractions"] = []
                            attraction_cost = self._coerce_number(
                                day_attractions.get("estimated_cost", 0)
                            )
                            daily_plan["estimated_cost"] += attraction_cost
                            daily_plan["daily_tips"].extend(day_attractions.get("daily_tips", []))

                        # 添加餐饮安排
                        day_meals = self._get_day_meals(dining_plans, day_num)
                        if day_meals:
                            daily_plan["meals"] = day_meals.get("meals", [])
                            meal_cost = self._coerce_number(day_meals.get("daily_food_cost", 0))
                            daily_plan["estimated_cost"] += meal_cost

                            # 将餐饮安排添加到schedule中
                            for meal in daily_plan["meals"]:
                                meal_cost = self._coerce_number(meal.get("estimated_cost", 0))
                                
                                # 安全构建description
                                cuisine = str(meal.get('cuisine', ''))
                                recommended_dishes = meal.get('recommended_dishes', [])
                                if isinstance(recommended_dishes, list):
                                    dish_names = [str(dish.get('name', '')) for dish in recommended_dishes[:2] if isinstance(dish, dict)]
                                    dish_str = ', '.join(dish_names)
                                else:
                                    dish_str = ""
                                
                                meal_schedule = {
                                    "time": str(meal.get("time", "")),
                                    "activity": str(meal.get("type", "用餐")),
                                    "location": str(meal.get("restaurant_name", "")),
                                    "description": f"{cuisine}料理，推荐{dish_str}",
                                    "cost": meal_cost,
                                    "tips": str(meal.get("booking_tips", ""))
                                }
                                daily_plan["schedule"].append(meal_schedule)
                        
                        # 添加交通信息（使用第一个交通方案）
                        daily_transport = get_day_entry_from_list(transportation_plans, day_num)
                        if daily_transport:
                            daily_plan["transportation"] = daily_transport
                        elif transportation_plans:
                            daily_plan["transportation"] = transportation_plans[0]

                        # 添加住宿信息
                        stay_info = get_day_entry_from_list(accommodation_daily, day_num)
                        if stay_info:
                            if stay_info.get("hotel"):
                                daily_plan["stay"] = self._merge_hotel_details(
                                    stay_info["hotel"],
                                    hotel_lookup
                                )
                        notes = stay_info.get("notes") or stay_info.get("accommodation_highlights") or []
                        if notes:
                            daily_plan["daily_tips"].extend(notes)
                        stay_cost = stay_info.get("daily_cost") or stay_info.get("estimated_cost") or 0
                        if isinstance(stay_cost, str):
                            try:
                                stay_cost = float(stay_cost)
                            except (TypeError, ValueError):
                                stay_cost = 0
                        if isinstance(stay_cost, (int, float)):
                            daily_plan["estimated_cost"] += stay_cost
                        
                        # 按时间排序schedule
                        daily_plan["schedule"] = sorted(
                            daily_plan["schedule"], 
                            key=lambda x: self._parse_time(x.get("time", "00:00"))
                        )
                        
                        daily_itineraries.append(daily_plan)
                    
                    travel_plan["daily_itineraries"] = daily_itineraries
                    
                    # 在最终组装的方案上做一次全局景点去重，避免同一景点出现在多个日期
                    self._deduplicate_daily_attractions(travel_plan)

                    # 添加餐厅总览
                    travel_plan["restaurants"] = self._merge_restaurant_details(
                        self._extract_restaurants_summary(dining_plans),
                        restaurant_lookup
                    )
                    
                    # 添加交通总览
                    travel_plan["transportation"] = transportation_plans
                    
                    # 计算总费用
                    travel_plan["total_cost"] = self._calculate_total_cost(
                        accommodation, daily_itineraries, plan.duration_days
                    )
                    
                    # 添加天气信息
                    weather_data = processed_data.get('weather', {})
                    travel_plan["weather_info"] = {
                        "raw_data": weather_data,
                        "travel_recommendations": self._generate_weather_recommendations(weather_data)
                    }
                    
                    # 添加目的地信息
                    travel_plan["destination_info"] = await self._extract_destination_info(processed_data, plan.destination)
                    
                    assembled_plans.append(travel_plan)
                    
                except Exception as e:
                    logger.error(f"组装方案 {i} 失败: {e}")
                    logger.error(f"详细错误信息: {traceback.format_exc()}")
                    continue
            
            logger.info(f"成功组装 {len(assembled_plans)} 个完整旅行方案")
            return assembled_plans
            
        except Exception as e:
            logger.error(f"组装旅行方案失败: {e}")
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return []

    def _get_per_day_budget(self, plan: Any) -> Optional[float]:
        """计算日均预算"""
        total_budget = getattr(plan, "budget", None)
        total_days = getattr(plan, "duration_days", None)
        if not total_budget or not total_days:
            return None
        try:
            total_budget = float(total_budget)
            total_days = int(total_days)
            if total_days <= 0:
                return None
            return max(total_budget / total_days, 0)
        except (TypeError, ValueError):
            return None

    def _get_day_attractions(self, attraction_plans: List[Dict[str, Any]], day: int) -> Dict[str, Any]:
        """获取指定天数的景点安排"""
        for day_plan in attraction_plans:
            if day_plan.get("day") == day:
                return day_plan
        return {}

    def _get_day_meals(self, dining_plans: List[Dict[str, Any]], day: int) -> Dict[str, Any]:
        """获取指定天数的餐饮安排"""
        for day_plan in dining_plans:
            if day_plan.get("day") == day:
                return day_plan
        return {}

    def _parse_time(self, time_str: str) -> int:
        """解析时间字符串为分钟数，用于排序"""
        try:
            if "-" in time_str:
                time_str = time_str.split("-")[0]
            if ":" in time_str:
                hour, minute = time_str.split(":")
                return int(hour) * 60 + int(minute)
        except:
            pass
        return 0

    def _extract_restaurants_summary(self, dining_plans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从餐饮方案中提取餐厅总览"""
        restaurants = []
        seen_restaurants = set()
        
        for day_plan in dining_plans:
            for meal in day_plan.get("meals", []):
                restaurant_name = meal.get("restaurant_name", "")
                if restaurant_name and restaurant_name not in seen_restaurants:
                    restaurant = {
                        "name": restaurant_name,
                        "cuisine": meal.get("cuisine", ""),
                        "address": meal.get("address", ""),
                        "atmosphere": meal.get("atmosphere", ""),
                        "signature_dishes": meal.get("recommended_dishes", []),
                        "estimated_cost": meal.get("estimated_cost", 0)
                    }
                    restaurants.append(restaurant)
                    seen_restaurants.add(restaurant_name)
        
        return restaurants

    def _merge_restaurant_details(
        self,
        restaurant_summaries: List[Dict[str, Any]],
        lookup: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not restaurant_summaries:
            return []
        merged_list = []
        list_fields = {"photos", "images", "specialties", "signature_dishes", "recommended_dishes", "menu_highlights"}
        for summary in restaurant_summaries:
            detailed = self._find_lookup_match(lookup, summary)
            if detailed:
                merged_list.append(self._combine_detail_dicts(detailed, summary, list_fields))
            else:
                merged_list.append(summary)
        return merged_list

    def _merge_hotel_details(
        self,
        hotel: Optional[Dict[str, Any]],
        lookup: Dict[str, Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if not hotel:
            return hotel
        list_fields = {"amenities", "photos", "images", "room_types", "available_options"}
        detailed = self._find_lookup_match(lookup, hotel)
        if detailed:
            return self._combine_detail_dicts(detailed, hotel, list_fields)
        return hotel

    def _combine_detail_dicts(
        self,
        source: Dict[str, Any],
        override: Dict[str, Any],
        list_fields: Set[str]
    ) -> Dict[str, Any]:
        merged = copy.deepcopy(source) if source else {}
        if not override:
            return merged

        for key, value in override.items():
            if key in list_fields:
                merged[key] = self._merge_list_values(merged.get(key), value)
            else:
                if value not in (None, "", [], {}):
                    merged[key] = value
        return merged

    def _merge_list_values(self, existing: Any, extra: Any) -> List[Any]:
        result = []
        seen = set()

        for collection in (existing, extra):
            for item in self._ensure_list(collection):
                marker = self._make_hashable(item)
                if marker in seen:
                    continue
                seen.add(marker)
                result.append(item)
        return result

    def _ensure_list(self, value: Any) -> List[Any]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return value
        return [value]

    def _make_hashable(self, value: Any) -> str:
        try:
            return json.dumps(value, sort_keys=True, ensure_ascii=False)
        except TypeError:
            return str(value)

    def _build_lookup_map(self, items: Optional[List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
        lookup: Dict[str, Dict[str, Any]] = {}
        if not items:
            return lookup
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = item.get("id")
            if item_id:
                lookup[f"id::{str(item_id).lower()}"] = item
            name_key = self._normalize_name(item.get("name"))
            if name_key:
                lookup[f"name::{name_key}"] = item
        return lookup

    def _find_lookup_match(self, lookup: Dict[str, Dict[str, Any]], target: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not target or not lookup:
            return None
        keys = []
        if target.get("id"):
            keys.append(f"id::{str(target['id']).lower()}")
        name_key = self._normalize_name(target.get("name"))
        if name_key:
            keys.append(f"name::{name_key}")
        for key in keys:
            if key and key in lookup:
                return lookup[key]
        return None

    def _normalize_name(self, name: Optional[str]) -> str:
        if not name:
            return ""
        return "".join(str(name).lower().split())

    def _calculate_total_cost(
        self, 
        accommodation: Dict[str, Any], 
        daily_itineraries: List[Dict[str, Any]], 
        duration_days: int
    ) -> Dict[str, Any]:
        """计算总费用"""
        cost_summary = accommodation.get("total_accommodation_cost", {}) or {}
        flight_cost = self._coerce_number(cost_summary.get("flight", 0))
        hotel_cost = self._coerce_number(cost_summary.get("hotel", 0))

        attractions_cost = 0.0
        for day in daily_itineraries:
            attractions_cost += self._coerce_number(day.get("estimated_cost", 0))

        meals_cost = 0.0
        for day in daily_itineraries:
            for meal in day.get("meals", []):
                meals_cost += self._coerce_number(meal.get("estimated_cost", 0))

        transportation_cost = 100 * duration_days  # 估算每日交通费用

        total = flight_cost + hotel_cost + attractions_cost + meals_cost + transportation_cost
        
        return {
            "flight": flight_cost,
            "hotel": hotel_cost,
            "attractions": attractions_cost,
            "meals": meals_cost,
            "transportation": transportation_cost,
            "total": total
        }

    def _coerce_number(self, value: Any, default: float = 0.0) -> float:
        """Best-effort conversion to float, flattening dict/list containers."""
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        if isinstance(value, dict):
            if "total" in value:
                return self._coerce_number(value.get("total"), default)
            subtotal = 0.0
            for sub in value.values():
                subtotal += self._coerce_number(sub, 0.0)
            return subtotal if subtotal else default
        if isinstance(value, (list, tuple)):
            total = 0.0
            for item in value:
                total += self._coerce_number(item, 0.0)
            return total if total else default
        return default

    def _generate_weather_recommendations(self, weather_data: Dict[str, Any]) -> List[str]:
        """基于天气数据生成旅游建议"""
        recommendations = ["建议根据当地天气情况合理安排行程"]
        
        try:
            if weather_data:
                # 这里可以根据实际天气数据生成更具体的建议
                recommendations.append("请关注天气变化，适时调整户外活动安排")
                recommendations.append("建议携带适合当地气候的衣物")
        except:
            pass
            
        return recommendations

    async def generate_text_plan(
        self,
        plan: Any,
        preferences: Optional[Dict[str, Any]] = None,
        max_chars: int = 2000,
    ) -> str:
        """生成纯文本旅行方案（不依赖爬取数据，直接由LLM生成）
        
        Args:
            plan: 旅行计划对象
            preferences: 用户偏好
            max_chars: 最大字符数限制（避免超token）
            
        Returns:
            纯文本方案字符串
        """
        try:
            system_prompt = f"""你是一位专业的旅行规划师。请根据用户需求生成一份简洁实用的旅行方案文本。

要求：
1. 方案要简洁明了，重点突出主要景点和玩法
2. 总字数控制在{max_chars}字以内
3. 包含目的地概况、主要景点、推荐玩法、注意事项等
4. 基于你的知识库，虽然可能有滞后性，但主要景点信息应该是准确的
5. 使用清晰的分段和标题，便于阅读

请直接返回纯文本，不要使用markdown格式，使用中文标点符号。"""

            destination = getattr(plan, "destination", "目的地")
            duration_days = getattr(plan, "duration_days", 0) or 1
            start_date = getattr(plan, "start_date", None)
            budget = getattr(plan, "budget", None)
            departure = getattr(plan, "departure", None)
            requirements = getattr(plan, "requirements", None)
            
            num_people = (
                getattr(plan, "num_people", None)
                or getattr(plan, "travelers", None)
                or (preferences or {}).get("travelers", 1)
            )
            age_groups = (preferences or {}).get("ageGroups", [])
            food_preferences = (preferences or {}).get("foodPreferences", [])
            activity_preference = (preferences or {}).get("activity_preference", [])

            user_prompt = f"""请为以下旅行需求生成一份简洁的纯文本方案：

目的地：{destination}
旅行天数：{duration_days}天
出发日期：{start_date or '未指定'}
出发地：{departure or '未指定'}
预算：{budget or '未指定'}元
旅行人数：{num_people}人
年龄群体：{', '.join(age_groups) if age_groups else '未指定'}
饮食偏好：{', '.join(food_preferences) if food_preferences else '无特殊偏好'}
活动偏好：{', '.join(activity_preference) if activity_preference else '未指定'}
特殊要求：{requirements or '无特殊要求'}

请生成一份简洁实用的旅行方案，包含：
1. 目的地概况（2-3句话）
2. 主要景点推荐（每天2-3个，按天列出）
3. 推荐玩法（简要说明）
4. 注意事项（简要提醒）

总字数控制在{max_chars}字以内，使用清晰的分段，直接返回纯文本。"""

            response = await openai_client.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=min(settings.OPENAI_MAX_TOKENS, max_chars // 2),  # 保守估计token数
                temperature=0.7
            )
            
            if not response:
                return "生成方案失败，请稍后重试。"
            
            # 清理响应并限制长度
            cleaned = self._clean_llm_response(response).strip()
            
            # 如果超过最大字符数，截断
            if len(cleaned) > max_chars:
                cleaned = cleaned[:max_chars] + "..."
            
            return cleaned
            
        except Exception as e:
            logger.error(f"生成纯文本方案失败: {e}")
            return f"生成方案时出现错误：{str(e)}。请稍后重试。"

    async def _generate_plans_with_llm_fallback(
        self,
        processed_data: Dict[str, Any],
        plan: Any,
        preferences: Optional[Dict[str, Any]] = None,
        raw_data: Optional[Dict[str, Any]] = None,
        *,
        is_international: bool = False,
    ) -> List[Dict[str, Any]]:
        """原始LLM生成方案的回退方法"""
        try:
            # 构建简化的系统提示
            system_prompt = """你是一个专业的旅行规划师，请根据提供的数据生成2-3个旅行方案。
请直接返回JSON格式的方案数组，不要添加任何其他文本。"""
            
            # 构建简化的用户提示
            intl_hint = ""
            if is_international:
                intl_hint = "\n注意：目的地为海外，请优先参考小红书笔记，如本地数据不足，可输出一般建议并提醒用户抵达后确认。"

            user_prompt = f"""
请为以下旅行需求制定方案：

出发地：{plan.departure}
目的地：{plan.destination}
旅行天数：{plan.duration_days}天
预算：{plan.budget}元

基于提供的真实数据生成2个实用的旅行方案。

{intl_hint}

请返回JSON格式：
[
  {{
    "id": "plan_1",
    "type": "标准方案",
    "title": "{plan.destination}之旅",
    "description": "方案描述",
    "flight": {{"airline": "航空公司", "price": 800}},
    "hotel": {{"name": "酒店名称", "price_per_night": 200}},
    "daily_itineraries": [],
    "total_cost": {{"total": 2000}},
    "duration_days": {plan.duration_days}
  }}
]
"""
            
            # 调用LLM
            response = await openai_client.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=0.7
            )
            
            # 尝试解析JSON响应
            try:
                cleaned_response = self._clean_llm_response(response)
                try:    
                    result = json.loads(cleaned_response)
                except json.JSONDecodeError:
                    logger.warning(f"生成方案失败，返回结果格式不正确，原始返回值：{cleaned_response}")
                    return []
                
                if isinstance(result, list):
                    plans = result
                elif isinstance(result, dict) and 'plans' in result:
                    plans = result['plans']
                else:
                    return []
                
                # 简单验证和处理
                validated_plans = []
                for i, plan_data in enumerate(plans):
                    plan_data['id'] = f"fallback_plan_{i}"
                    plan_data['generated_at'] = datetime.utcnow().isoformat()
                    validated_plans.append(plan_data)
                
                return validated_plans
                
            except json.JSONDecodeError:
                logger.error("回退方法JSON解析失败")
                return []
                
        except Exception as e:
            logger.error(f"回退方法失败: {e}")
            return []
