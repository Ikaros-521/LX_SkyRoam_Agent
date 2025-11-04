"""
旅行方案生成服务
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import random
import json
import asyncio
import time
import traceback
from functools import wraps
from app.tools.openai_client import openai_client
from app.core.config import settings


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


class PlanGenerator:
    """方案生成器"""
    
    def __init__(self):
        self.max_plans = 5
        self.min_attractions_per_day = 2
        self.max_attractions_per_day = 4
        # 延迟导入避免循环依赖
        self._data_collector = None
    
    @property
    def data_collector(self):
        """延迟初始化data_collector"""
        if self._data_collector is None:
            from app.services.data_collector import DataCollector
            self._data_collector = DataCollector()
        return self._data_collector
    
    async def generate_plans(
        self, 
        processed_data: Dict[str, Any], 
        plan: Any,
        preferences: Optional[Dict[str, Any]] = None,
        raw_data: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """生成多个旅行方案"""
        try:
            logger.info("开始生成旅行方案")
            
            # 检查是否有多个偏好，决定使用拆分策略还是传统策略
            use_split_strategy = self._should_use_split_strategy(preferences)
            
            # 首先尝试使用LLM生成方案
            try:
                # 检查OpenAI配置
                if not openai_client.api_key:
                    logger.warning("OpenAI API密钥未配置，使用传统方法")
                    raise Exception("OpenAI API密钥未配置")
                
                # 根据偏好情况选择生成策略
                if use_split_strategy:
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
                        self._generate_plans_with_llm(processed_data, plan, preferences, raw_data),
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
            plans = []
            
            # 生成不同风格的方案
            plan_types = [
                "经济实惠型",
                "舒适享受型", 
                "文化深度型",
                "自然风光型",
                "美食体验型"
            ]
            
            for i, plan_type in enumerate(plan_types[:self.max_plans]):
                plan_data = await self._generate_single_plan(
                    processed_data, plan, preferences, plan_type, i, raw_data
                )
                if plan_data:
                    plans.append(plan_data)
            
            logger.info(f"生成了 {len(plans)} 个旅行方案")
            return plans
            
        except Exception as e:
            logger.error(f"生成旅行方案失败: {e}")
            return []

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
        
        # 基础偏好组（所有方案都包含）
        base_preferences = {
            'budget_priority': preferences.get('budget_priority', 'medium'),
            'travelers_count': preferences.get('travelers_count', 1),
            'food_preferences': preferences.get('food_preferences', []),
            'dietary_restrictions': preferences.get('dietary_restrictions', []),
            'age_groups': preferences.get('age_groups', [])
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
        "price_range": "价格区间",
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
旅行人数：{getattr(plan, 'travelers', 1)}人
年龄群体：{', '.join(getattr(plan, 'ageGroups', [])) if getattr(plan, 'ageGroups', None) else '未指定'}
饮食偏好：{', '.join(getattr(plan, 'foodPreferences', [])) if getattr(plan, 'foodPreferences', None) else '无特殊偏好'}
饮食禁忌：{', '.join(getattr(plan, 'dietaryRestrictions', [])) if getattr(plan, 'dietaryRestrictions', None) else '无饮食禁忌'}
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
        raw_data: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """使用模块化LLM生成旅行方案"""
        try:
            logger.info("开始模块化生成旅行方案")
            
            # 串行调用各个模块化生成器，避免API限速
            logger.info("开始串行生成各模块方案...")
            
            # 住宿方案
            try:
                accommodation_plans = await self._generate_accommodation_plans(
                    processed_data.get('hotels', []),
                    processed_data.get('flights', []),
                    plan,
                    preferences,
                    raw_data
                )
            except Exception as e:
                logger.error(f"住宿方案生成失败: {e}")
                accommodation_plans = []
            
            # 添加延迟避免API限速
            await asyncio.sleep(1)
            
            # 餐饮方案
            try:
                dining_plans = await self._generate_dining_plans(
                    processed_data.get('restaurants', []),
                    plan,
                    preferences,
                    raw_data
                )
            except Exception as e:
                logger.error(f"餐饮方案生成失败: {e}")
                dining_plans = []
            
            # 添加延迟避免API限速
            await asyncio.sleep(1)
            
            # 交通方案
            try:
                transportation_plans = await self._generate_transportation_plans(
                    processed_data.get('transportation', []),
                    plan,
                    preferences
                )
            except Exception as e:
                logger.error(f"交通方案生成失败: {e}")
                transportation_plans = []
            
            # 添加延迟避免API限速
            await asyncio.sleep(1)
            
            # 景点方案
            try:
                attraction_plans = await self._generate_attraction_plans(
                    processed_data.get('attractions', []),
                    plan,
                    preferences,
                    raw_data
                )
            except Exception as e:
                logger.error(f"景点方案生成失败: {e}")
                attraction_plans = []
            
            # 检查是否有足够的数据进行组装
            failed_modules = []
            if not accommodation_plans:
                failed_modules.append("住宿方案")
            if not dining_plans:
                failed_modules.append("餐饮方案")
            if not transportation_plans:
                failed_modules.append("交通方案")
            if not attraction_plans:
                failed_modules.append("景点方案")
            
            if failed_modules:
                error_msg = f"以下模块生成失败: {', '.join(failed_modules)}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"模块化生成完成 - 住宿:{len(accommodation_plans)}, 餐饮:{len(dining_plans)}, 交通:{len(transportation_plans)}, 景点:{len(attraction_plans)}")
            
            # 使用组装器整合所有方案
            assembled_plans = await self._assemble_travel_plans(
                accommodation_plans,
                dining_plans,
                transportation_plans,
                attraction_plans,
                processed_data,
                plan
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
            return await self._generate_plans_with_llm_fallback(processed_data, plan, preferences, raw_data)


    
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
     价格区间: {item.get('price_range', 'N/A')}
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
            
            plan_data = {
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
                "generated_at": datetime.utcnow().isoformat()
            }
            
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
1. 每天的行程要合理安排时间，包含上午、下午、晚上的活动
2. 景点安排要考虑地理位置，优化游览路线
3. 结合小红书用户的真实体验和建议
4. 包含具体的时间安排、交通方式、预估费用
5. 为每个景点/活动提供详细的游览建议和注意事项
6. 根据方案类型({plan_type})调整活动强度和选择

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

            user_prompt = f"""旅行信息：
目的地：{plan.destination}
旅行天数：{plan.duration_days}天
开始日期：{plan.start_date}
旅行人数：{plan.num_people}人
年龄群体：{plan.age_group}
预算范围：{plan.budget}
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
            selected = sorted(restaurants, key=lambda x: x.get("price_range", "$$$$"))[:num_days]
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
        raw_data: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """生成住宿方案（包含航班信息）"""
        try:
            system_prompt = """你是一个专业的住宿规划师，专门为游客推荐合适的酒店和航班组合。
请根据提供的真实酒店和航班数据，为用户生成2-3个不同价位的住宿方案。

每个方案应该包含：
1. 航班选择（考虑价格、时间、航空公司）
2. 酒店选择（考虑位置、价格、设施、评分）
3. 住宿总费用计算

请严格按照以下JSON格式返回：
[
  {
    "type": "经济型",
    "flight": {
      "airline": "航空公司",
      "departure_time": "出发时间",
      "arrival_time": "到达时间", 
      "price": 价格,
      "rating": 评分,
      "flight_number": "航班号"
    },
    "hotel": {
      "name": "酒店名称",
      "address": "酒店地址",
      "price_per_night": 每晚价格,
      "rating": 评分,
      "amenities": ["设施1", "设施2"],
      "location_advantage": "位置优势",
      "room_type": "房间类型"
    },
    "total_accommodation_cost": {
      "flight": 航班费用,
      "hotel": 酒店总费用,
      "total": 住宿总费用
    },
    "accommodation_highlights": ["亮点1", "亮点2"]
  }
]"""

            user_prompt = f"""
请为以下旅行需求推荐住宿方案：

出发地：{plan.departure}
目的地：{plan.destination}
旅行天数：{plan.duration_days}天
出发日期：{plan.start_date}
返回日期：{plan.end_date}
预算：{plan.budget}元
旅行人数：{getattr(plan, 'travelers', 1)}人
年龄群体：{', '.join(getattr(plan, 'ageGroups', [])) if getattr(plan, 'ageGroups', None) else '未指定'}
用户偏好：{preferences or '无特殊偏好'}

可用航班数据：
{self._format_data_for_llm(flights_data, 'flight')}

可用酒店数据：
{self._format_data_for_llm(hotels_data, 'hotel')}

小红书真实用户住宿体验分享：
{self._format_xiaohongshu_data_for_prompt(raw_data.get('xiaohongshu_notes', []) if raw_data else [], plan.destination)}

要求：
1. 根据旅行人数({getattr(plan, 'travelers', 1)}人)合理安排房间数量和床位类型
2. 考虑年龄群体({', '.join(getattr(plan, 'ageGroups', [])) if getattr(plan, 'ageGroups', None) else '未指定'})的住宿需求
3. 航班时间要合理，避免红眼航班（除非预算紧张）
4. 酒店位置要便于游览，交通便利
5. 总费用要在预算范围内
6. 必须使用提供的真实数据，不要虚构

请直接返回JSON格式结果。
"""

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
                logger.warning(f"生成住宿方案失败，返回结果格式不正确，原始返回值：{cleaned_response}")
                return []
            
            if not isinstance(result, list):
                logger.warning("住宿方案返回格式不正确")
                return []
                
            logger.info(f"生成住宿方案数量: {len(result)}")
            return result

        except Exception as e:
            logger.error(f"生成住宿方案失败: {e}")
            return []

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    async def _generate_dining_plans(
        self,
        restaurants_data: List[Dict[str, Any]],
        plan: Any,
        preferences: Optional[Dict[str, Any]] = None,
        raw_data: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """生成餐饮方案"""
        try:
            system_prompt = """你是一个专业的美食规划师，专门为游客推荐当地特色餐厅和美食。
请根据提供的真实餐厅数据，为用户的每一天生成详细的用餐安排。

每天的用餐安排应该包含：
1. 早餐、午餐、晚餐的具体餐厅推荐
2. 每个餐厅的招牌菜品和口味描述
3. 用餐时间安排和预订建议
4. 餐饮费用预估

请严格按照以下JSON格式返回：
[
  {
    "day": 1,
    "meals": [
      {
        "type": "早餐",
        "time": "08:00-09:00",
        "restaurant_name": "餐厅名称",
        "cuisine": "菜系类型",
        "recommended_dishes": [
          {
            "name": "菜品名称",
            "description": "菜品描述和特色",
            "price": "价格区间",
            "taste": "口味特点"
          }
        ],
        "atmosphere": "用餐环境描述",
        "estimated_cost": 预估费用,
        "booking_tips": "预订建议",
        "address": "餐厅地址"
      }
    ],
    "daily_food_cost": 当日餐饮总费用,
    "food_highlights": ["美食亮点1", "特色推荐2"]
  }
]"""

            user_prompt = f"""
请为以下旅行需求制定餐饮方案：

目的地：{plan.destination}
旅行天数：{plan.duration_days}天
旅行人数：{getattr(plan, 'travelers', 1)}人
饮食偏好：{', '.join(getattr(plan, 'foodPreferences', [])) if getattr(plan, 'foodPreferences', None) else '无特殊偏好'}
饮食禁忌：{', '.join(getattr(plan, 'dietaryRestrictions', [])) if getattr(plan, 'dietaryRestrictions', None) else '无饮食禁忌'}
预算：{plan.budget}元
用户偏好：{preferences or '无特殊偏好'}

可用餐厅数据：
{self._format_data_for_llm(restaurants_data, 'restaurant')}

小红书真实用户美食分享：
{self._format_xiaohongshu_data_for_prompt(raw_data.get('xiaohongshu_notes', []) if raw_data else [], plan.destination)}

要求：
1. 根据用户饮食偏好推荐合适菜系
2. 严格避免推荐含有饮食禁忌的食物
3. 为每餐推荐具体的菜品名称和特色描述
4. 考虑用餐人数安排合适的餐厅
5. 提供详细的口味描述和用餐建议
6. 必须使用提供的真实餐厅数据

请直接返回JSON格式结果。
"""

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
                logger.warning(f"生成餐饮方案失败，返回结果格式不正确，原始返回值：{cleaned_response}")
                return []
            
            if not isinstance(result, list):
                logger.warning("餐饮方案返回格式不正确")
                return []
                
            logger.info(f"生成餐饮方案天数: {len(result)}")
            return result

        except Exception as e:
            logger.error(f"生成餐饮方案失败: {e}")
            return []

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    async def _generate_transportation_plans(
        self,
        transportation_data: List[Dict[str, Any]],
        plan: Any,
        preferences: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """生成交通方案"""
        try:
            system_prompt = """你是一个专业的交通规划师，专门为游客规划当地交通出行方案。
请根据提供的真实交通数据，为用户生成详细的交通出行建议。

交通方案应该包含：
1. 主要交通方式推荐（地铁、公交、出租车、步行等）
2. 详细的路线规划和换乘信息
3. 交通费用预估和时间安排
4. 实用的出行建议和注意事项

请严格按照以下JSON格式返回：
[
  {
    "type": "交通方式",
    "name": "交通名称",
    "description": "简要描述",
    "route": "详细路线（起点→途经→终点）",
    "duration": "耗时(分钟)",
    "distance": "距离(公里)",
    "price": "费用(元)",
    "operating_hours": "运营时间",
    "frequency": "发车频率",
    "transfer_points": ["换乘点1", "换乘点2"],
    "walking_distance": "步行距离",
    "accessibility": "无障碍设施情况",
    "peak_hours": "高峰时段",
    "alternative_routes": "备选路线",
    "comfort_level": "舒适度评价",
    "convenience_score": "便利性评分",
    "usage_tips": ["使用建议1", "注意事项2"]
  }
]"""

            user_prompt = f"""
请为以下旅行需求制定交通方案：

目的地：{plan.destination}
旅行天数：{plan.duration_days}天
旅行人数：{getattr(plan, 'travelers', 1)}人
出行方式偏好：{plan.transportation or '未指定'}
预算：{plan.budget}元
用户偏好：{preferences or '无特殊偏好'}

可用交通数据：
{self._format_data_for_llm(transportation_data, 'transportation')}

要求：
1. 优先考虑用户指定的出行方式：{plan.transportation or '未指定'}
2. 提供详细的交通路线和换乘信息
3. 包含准确的时间、费用、距离信息
4. 考虑高峰时段和备选路线
5. 根据旅行人数推荐合适的交通工具
6. 必须使用提供的真实交通数据

请直接返回JSON格式结果。
"""

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
                logger.warning(f"生成交通方案失败，返回结果格式不正确，原始返回值：{cleaned_response}")
                return []
            
            if not isinstance(result, list):
                logger.warning("交通方案返回格式不正确")
                return []
                
            logger.info(f"生成交通方案数量: {len(result)}")
            return result

        except Exception as e:
            logger.error(f"生成交通方案失败: {e}")
            return []

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    async def _generate_attraction_plans(
        self,
        attractions_data: List[Dict[str, Any]],
        plan: Any,
        preferences: Optional[Dict[str, Any]] = None,
        raw_data: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """生成景点游玩方案"""
        try:
            system_prompt = """你是一个专业的景点规划师，专门为游客规划景点游览行程。
请根据提供的真实景点数据和小红书用户的实际体验分享，为用户的每一天生成详细的景点游览安排。

重要指导原则：
1. 充分利用小红书攻略中的实用建议，如最佳游览时间、推荐路线、避坑指南等
2. 提取攻略中的具体细节，如"早上8点半开门就进去人少"、"午门进神武门出"等实用信息
3. 结合攻略中的个人体验，提供更贴近实际的游览建议
4. 参考攻略中提到的必看亮点、拍照位置、省钱技巧等
5. 注意攻略中的时间安排建议和注意事项

每天的游览安排应该包含：
1. 基于攻略经验的景点选择和最优游览顺序
2. 参考真实用户体验的详细时间安排
3. 攻略中提到的景点亮点和必看内容
4. 实用的游览技巧和避坑建议
5. 门票费用和开放时间信息

请严格按照以下JSON格式返回：
[
  {
    "day": 1,
    "date": "日期",
    "schedule": [
      {
        "time": "09:00-12:00",
        "activity": "景点游览",
        "location": "具体景点名称",
        "description": "结合攻略经验的详细游览内容，包含必看亮点和推荐体验",
        "cost": 门票价格,
        "tips": "基于真实用户体验的游览建议，包含时间安排、路线选择、避坑指南等实用信息"
      }
    ],
    "attractions": [
      {
        "name": "景点名称",
        "category": "景点类型",
        "description": "景点描述",
        "price": 门票价格,
        "rating": 评分,
        "visit_time": "建议游览时间",
        "opening_hours": "开放时间",
        "best_visit_time": "基于攻略经验的最佳游览时段",
        "highlights": ["攻略中提到的亮点1", "必看内容2", "特色体验3"],
        "photography_spots": ["攻略推荐的拍照点1", "网红打卡地2"],
        "address": "景点地址",
        "route_tips": "攻略中的路线建议和游览顺序",
        "experience_tips": ["基于真实体验的实用建议1", "省钱技巧2", "避坑指南3"]
      }
    ],
    "estimated_cost": 当日景点费用,
    "daily_tips": ["基于攻略的当日游览建议", "真实用户的注意事项", "实用的省钱和避坑小贴士"]
  }
]"""

            user_prompt = f"""
请为以下旅行需求制定景点游览方案：

目的地：{plan.destination}
旅行天数：{plan.duration_days}天
旅行人数：{getattr(plan, 'travelers', 1)}人
年龄群体：{', '.join(getattr(plan, 'ageGroups', [])) if getattr(plan, 'ageGroups', None) else '未指定'}
预算：{plan.budget}元
特殊要求：{plan.requirements or '无特殊要求'}
用户偏好：{preferences or '无特殊偏好'}

可用景点数据：
{self._format_data_for_llm(attractions_data, 'attraction')}

小红书真实用户景点体验分享：
{self._format_xiaohongshu_data_for_prompt(raw_data.get('xiaohongshu_notes', []) if raw_data else [], plan.destination)}

重要要求：
1. **深度利用小红书攻略**：仔细分析每条攻略中的具体建议，如游览路线、时间安排、必看亮点等
2. **提取实用细节**：将攻略中的具体操作建议融入到游览安排中，如"早上8点半开门就进去"、"午门进神武门出"等
3. **结合真实体验**：基于攻略中的个人体验和感受，提供更贴近实际的游览建议
4. **优化时间安排**：参考攻略中的时间建议，合理安排每个景点的游览时长和最佳时段
5. **包含避坑指南**：整合攻略中的注意事项和避坑建议，帮助用户避免常见问题
6. **路线优化**：根据攻略中的路线建议和地理位置，优化景点游览顺序
7. **必须使用提供的真实景点数据**：确保所有推荐的景点都在提供的数据范围内

请特别注意：
- 将小红书攻略中的具体建议转化为可操作的游览安排
- 结合攻略中的个人感受和推荐，提供更有温度的旅行建议
- 利用攻略中的省钱技巧和实用信息，为用户提供更好的旅行体验

请直接返回JSON格式结果。
"""
            logger.warning(f"User prompt: {user_prompt}")

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
                logger.warning(f"生成景点方案失败，返回结果格式不正确，原始返回值：{cleaned_response}")
                return []
            
            if not isinstance(result, list):
                logger.warning("景点方案返回格式不正确")
                return []
                
            logger.info(f"生成景点方案天数: {len(result)}")
            return result

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
        plan: Any
    ) -> List[Dict[str, Any]]:
        """组装完整的旅行方案"""
        try:
            assembled_plans = []
            
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
                        "generated_at": datetime.utcnow().isoformat()
                    }
                    
                    # 添加航班和酒店信息
                    travel_plan["flight"] = accommodation.get("flight", {})
                    travel_plan["hotel"] = accommodation.get("hotel", {})
                    
                    # 构建每日行程
                    daily_itineraries = []
                    for day in range(1, plan.duration_days + 1):
                        # 确保day是整数
                        day_num = int(day)
                        # 确保日期计算正确
                        calculated_date = self._calculate_date(plan.start_date, day_num - 1)
                        
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
                            daily_plan["attractions"] = day_attractions.get("attractions", [])
                            # 确保费用是数字类型
                            attraction_cost = day_attractions.get("estimated_cost", 0)
                            if isinstance(attraction_cost, str):
                                try:
                                    attraction_cost = float(attraction_cost)
                                except (ValueError, TypeError):
                                    attraction_cost = 0
                            daily_plan["estimated_cost"] += attraction_cost
                            daily_plan["daily_tips"].extend(day_attractions.get("daily_tips", []))
                        
                        # 添加餐饮安排
                        day_meals = self._get_day_meals(dining_plans, day_num)
                        if day_meals:
                            daily_plan["meals"] = day_meals.get("meals", [])
                            # 确保费用是数字类型
                            meal_cost = day_meals.get("daily_food_cost", 0)
                            if isinstance(meal_cost, str):
                                try:
                                    meal_cost = float(meal_cost)
                                except (ValueError, TypeError):
                                    meal_cost = 0
                            daily_plan["estimated_cost"] += meal_cost
                            
                            # 将餐饮安排添加到schedule中
                            for meal in daily_plan["meals"]:
                                # 确保cost是数字类型
                                meal_cost = meal.get("estimated_cost", 0)
                                if isinstance(meal_cost, str):
                                    try:
                                        meal_cost = float(meal_cost)
                                    except (ValueError, TypeError):
                                        meal_cost = 0
                                
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
                        if transportation_plans:
                            daily_plan["transportation"] = transportation_plans[0]
                        
                        # 按时间排序schedule
                        daily_plan["schedule"] = sorted(
                            daily_plan["schedule"], 
                            key=lambda x: self._parse_time(x.get("time", "00:00"))
                        )
                        
                        daily_itineraries.append(daily_plan)
                    
                    travel_plan["daily_itineraries"] = daily_itineraries
                    
                    # 添加餐厅总览
                    travel_plan["restaurants"] = self._extract_restaurants_summary(dining_plans)
                    
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

    def _calculate_date(self, start_date: str, days_offset: int) -> str:
        """计算指定天数后的日期"""
        try:
            from datetime import datetime, timedelta
            start = datetime.strptime(start_date, "%Y-%m-%d")
            target_date = start + timedelta(days=days_offset)
            return target_date.strftime("%Y-%m-%d")
        except:
            return start_date

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

    def _calculate_total_cost(
        self, 
        accommodation: Dict[str, Any], 
        daily_itineraries: List[Dict[str, Any]], 
        duration_days: int
    ) -> Dict[str, Any]:
        """计算总费用"""
        # 确保住宿费用是数字类型
        flight_cost = accommodation.get("total_accommodation_cost", {}).get("flight", 0)
        if isinstance(flight_cost, str):
            try:
                flight_cost = float(flight_cost)
            except (ValueError, TypeError):
                flight_cost = 0
        
        hotel_cost = accommodation.get("total_accommodation_cost", {}).get("hotel", 0)
        if isinstance(hotel_cost, str):
            try:
                hotel_cost = float(hotel_cost)
            except (ValueError, TypeError):
                hotel_cost = 0
        
        # 确保景点费用是数字类型
        attractions_cost = 0
        for day in daily_itineraries:
            day_cost = day.get("estimated_cost", 0)
            if isinstance(day_cost, str):
                try:
                    day_cost = float(day_cost)
                except (ValueError, TypeError):
                    day_cost = 0
            attractions_cost += day_cost
        
        # 确保餐饮费用是数字类型
        meals_cost = 0
        for day in daily_itineraries:
            for meal in day.get("meals", []):
                meal_cost = meal.get("estimated_cost", 0)
                if isinstance(meal_cost, str):
                    try:
                        meal_cost = float(meal_cost)
                    except (ValueError, TypeError):
                        meal_cost = 0
                meals_cost += meal_cost
        
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

    async def _generate_plans_with_llm_fallback(
        self,
        processed_data: Dict[str, Any],
        plan: Any,
        preferences: Optional[Dict[str, Any]] = None,
        raw_data: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """原始LLM生成方案的回退方法"""
        try:
            # 构建简化的系统提示
            system_prompt = """你是一个专业的旅行规划师，请根据提供的数据生成2-3个旅行方案。
请直接返回JSON格式的方案数组，不要添加任何其他文本。"""
            
            # 构建简化的用户提示
            user_prompt = f"""
请为以下旅行需求制定方案：

出发地：{plan.departure}
目的地：{plan.destination}
旅行天数：{plan.duration_days}天
预算：{plan.budget}元

基于提供的真实数据生成2个实用的旅行方案。

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
