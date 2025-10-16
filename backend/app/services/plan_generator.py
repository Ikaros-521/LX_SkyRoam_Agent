"""
旅行方案生成服务
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import random
import json
import asyncio
from app.tools.openai_client import openai_client
from app.core.config import settings


class PlanGenerator:
    """方案生成器"""
    
    def __init__(self):
        self.max_plans = 5
        self.min_attractions_per_day = 2
        self.max_attractions_per_day = 4
    
    async def generate_plans(
        self, 
        processed_data: Dict[str, Any], 
        plan: Any,
        preferences: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """生成多个旅行方案"""
        try:
            logger.info("开始生成旅行方案")
            
            # 首先尝试使用LLM生成方案
            try:
                # 检查OpenAI配置
                if not openai_client.api_key:
                    logger.warning("OpenAI API密钥未配置，使用传统方法")
                    raise Exception("OpenAI API密钥未配置")
                
                # 设置超时
                llm_plans = await asyncio.wait_for(
                    self._generate_plans_with_llm(processed_data, plan, preferences),
                    timeout=300.0  # 300秒超时
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
                    processed_data, plan, preferences, plan_type, i
                )
                if plan_data:
                    plans.append(plan_data)
            
            logger.info(f"生成了 {len(plans)} 个旅行方案")
            return plans
            
        except Exception as e:
            logger.error(f"生成旅行方案失败: {e}")
            return []
    
    async def _generate_plans_with_llm(
        self,
        processed_data: Dict[str, Any],
        plan: Any,
        preferences: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """使用LLM生成旅行方案"""
        try:
            # 构建系统提示
            system_prompt = """你是一个专业的旅行规划师，擅长为游客制定详细的旅行计划。
请根据提供的数据和用户需求，生成3-5个不同风格的旅行方案。

重要：请直接返回一个包含所有方案的数组，不要嵌套在plans对象中。

必须严格按照以下JSON格式返回：

[
  {
    "id": "plan_1",
    "type": "经济实惠型",
    "title": "经济实惠的{目的地}之旅",
      "description": "详细的方案描述",
      "flight": {
        "airline": "航空公司",
        "departure_time": "出发时间",
        "arrival_time": "到达时间",
        "price": 价格,
        "rating": 评分
      },
      "hotel": {
        "name": "酒店名称",
        "address": "酒店地址",
        "price_per_night": 每晚价格,
        "rating": 评分,
        "amenities": ["设施1", "设施2"]
      },
      "daily_itineraries": [
        {
          "day": 1,
          "date": "日期",
          "attractions": [
            {
              "name": "景点名称",
              "category": "景点类型",
              "description": "景点描述",
              "price": 门票价格,
              "rating": 评分,
              "visit_time": "建议游览时间"
            }
          ],
          "meals": [
            {
              "type": "早餐/午餐/晚餐",
              "time": "用餐时间",
              "suggestion": "餐厅建议",
              "estimated_cost": 预估费用
            }
          ],
          "transportation": {
            "type": "交通方式",
            "route": "具体路线",
            "duration": "耗时(分钟)",
            "distance": "距离(公里)",
            "cost": "费用(元)",
            "traffic_conditions": "路况信息",
            "operating_hours": "运营时间",
            "frequency": "发车频率"
          },
          "estimated_cost": 当日总费用
        }
      ],
      "restaurants": [
        {
          "name": "餐厅名称",
          "cuisine": "菜系",
          "price_range": "价格区间",
          "rating": 评分,
          "address": "地址"
        }
      ],
      "transportation": [
        {
          "type": "交通方式",
          "name": "交通名称",
          "description": "简要描述",
          "duration": "耗时(分钟)",
          "distance": "距离(公里)",
          "price": "费用(元)",
          "operating_hours": "运营时间"
        }
      ],
      "total_cost": {
        "flight": 航班费用,
        "hotel": 酒店费用,
        "attractions": 景点费用,
        "meals": 餐饮费用,
        "transportation": 交通费用,
        "total": 总费用
      },
      "weather_info": {
        "travel_recommendations": ["基于天气的旅游建议1", "建议2"]
      },
      "duration_days": 天数,
      "generated_at": "生成时间"
    }
  ]

请确保返回的JSON格式完全符合上述结构，不要添加任何额外的文本或说明。"""
            
            # 构建用户提示
            user_prompt = f"""
请为以下旅行需求制定多个方案：

出发地：{plan.departure}
目的地：{plan.destination}
旅行天数：{plan.duration_days}天
出发日期：{plan.start_date}
返回日期：{plan.end_date}
预算：{plan.budget}元
出行方式：{plan.transportation or '未指定'}
用户偏好：{preferences or '无特殊偏好'}
特殊要求：{plan.requirements or '无特殊要求'}

真实可用数据：

航班信息：
{self._format_data_for_llm(processed_data.get('flights', []), 'flight')}

酒店信息：
{self._format_data_for_llm(processed_data.get('hotels', []), 'hotel')}

景点信息：
{self._format_data_for_llm(processed_data.get('attractions', []), 'attraction')}

餐厅信息：
{self._format_data_for_llm(processed_data.get('restaurants', []), 'restaurant')}

交通信息：
{self._format_data_for_llm(processed_data.get('transportation', []), 'transportation')}

天气信息：
{processed_data.get('weather', {})}

请基于以上真实数据生成3-5个不同风格的旅行方案，每个方案都要实用且详细。

重要提醒：
1. 必须严格按照指定的JSON格式返回
2. 必须使用提供的真实数据，不要虚构信息
3. 每个方案都要包含完整的daily_itineraries数组
4. 价格信息要基于真实数据，符合预算
5. 景点安排要考虑地理位置和游览时间，优先选择交通便利的景点
6. 餐饮建议要基于真实餐厅信息，考虑与景点的距离
7. 交通方式要基于真实交通数据，包括耗时、费用、路况信息
8. 优先考虑用户指定的出行方式：{plan.transportation or '未指定'}
9. 在交通安排中要包含实时路况、拥堵情况、道路状况等详细信息
10. 使用地图数据时，要充分利用距离、耗时、发车频率、路况等详细信息
11. 景点选择要考虑交通便利性，优先推荐公共交通可达的景点
12. 在daily_itineraries中要合理安排景点间的交通时间和方式
13. 考虑不同交通方式的运营时间，避免安排超出运营时间的行程
14. 基于天气情况在weather_info中生成实用的旅游建议
15. 旅游建议要具体实用，如穿衣建议、活动安排、注意事项等

请直接返回JSON格式的结果，不要添加任何其他文本。
"""
            
            logger.info(f"LLM用户提示: {user_prompt}")

            # 调用LLM
            response = await openai_client.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=0.7
            )
            
            # 尝试解析JSON响应
            try:
                # 清理响应文本，移除可能的markdown标记
                cleaned_response = self._clean_llm_response(response)
                
                result = json.loads(cleaned_response)
                if isinstance(result, dict) and 'plans' in result:
                    plans = result['plans']
                    # 处理嵌套的plans结构
                    if plans and isinstance(plans[0], dict) and 'plans' in plans[0]:
                        # 扁平化嵌套的plans数组
                        flattened_plans = []
                        for plan_group in plans:
                            if isinstance(plan_group.get('plans'), list):
                                flattened_plans.extend(plan_group['plans'])
                        plans = flattened_plans
                elif isinstance(result, list):
                    plans = result
                else:
                    logger.warning("LLM返回的JSON格式不符合预期")
                    return []
                
                # 验证和清理方案数据
                validated_plans = []
                for i, plan_data in enumerate(plans):
                    if self._validate_plan_data(plan_data):
                        plan_data['id'] = f"llm_plan_{i}"
                        plan_data['generated_at'] = datetime.utcnow().isoformat()
                        validated_plans.append(plan_data)
                    else:
                        logger.warning(f"方案 {i} 数据验证失败")
                
                if not validated_plans:
                    logger.error("所有LLM生成的方案都未通过验证")
                    return []
                
                # 关键：用真实交通数据校准LLM输出，避免距离/时长被编造
                self._enforce_transportation_from_data(validated_plans, processed_data)
                
                # 为每个方案添加原始天气数据
                weather_data = processed_data.get('weather', {})
                for plan_data in validated_plans:
                    if 'weather_info' in plan_data:
                        # 保留LLM生成的旅游建议，添加原始天气数据
                        plan_data['weather_info']['raw_data'] = weather_data
                    else:
                        # 如果LLM没有生成weather_info，创建一个
                        plan_data['weather_info'] = {
                            'raw_data': weather_data,
                            'travel_recommendations': ["建议根据当地天气情况合理安排行程"]
                        }
                
                # 为每个方案添加原始酒店数据
                hotel_data = processed_data.get('hotels', [])
                for plan_data in validated_plans:
                    if 'hotel' in plan_data:
                        # 保留LLM生成的酒店信息，添加原始酒店数据
                        plan_data['hotel']['raw_data'] = hotel_data
                        plan_data['hotel']['available_options'] = hotel_data[:10]  # 提供前10个酒店选项
                    else:
                        # 如果LLM没有生成hotel，创建一个默认的
                        if hotel_data:
                            # 使用第一个酒店作为默认选择
                            default_hotel = hotel_data[0]
                            plan_data['hotel'] = {
                                'name': default_hotel.get('name', '推荐酒店'),
                                'address': default_hotel.get('address', ''),
                                'price_per_night': default_hotel.get('price_per_night', 200),
                                'rating': default_hotel.get('rating', 4.0),
                                'amenities': default_hotel.get('amenities', []),
                                'raw_data': hotel_data,
                                'available_options': hotel_data[:10]
                            }
                        else:
                            # 没有酒店数据时的默认处理
                            plan_data['hotel'] = {
                                'name': '待选择酒店',
                                'address': '请根据实际需求选择',
                                'price_per_night': 200,
                                'rating': 4.0,
                                'amenities': [],
                                'raw_data': [],
                                'available_options': []
                            }
                
                return validated_plans
                
            except json.JSONDecodeError as e:
                logger.error(f"解析LLM返回的JSON失败: {e}")
                logger.debug(f"LLM原始响应: {response}")
                
                # 尝试从响应中提取JSON
                extracted_json = self._extract_json_from_response(response)
                if extracted_json:
                    try:
                        result = json.loads(extracted_json)
                        if isinstance(result, dict) and 'plans' in result:
                            plans = result['plans']
                        elif isinstance(result, list):
                            plans = result
                        else:
                            return []
                        
                        validated_plans = []
                        for i, plan_data in enumerate(plans):
                            if self._validate_plan_data(plan_data):
                                plan_data['id'] = f"llm_plan_{i}"
                                plan_data['generated_at'] = datetime.utcnow().isoformat()
                                validated_plans.append(plan_data)
                        
                        self._enforce_transportation_from_data(validated_plans, processed_data)
                        
                        # 为每个方案添加原始天气数据
                        weather_data = processed_data.get('weather', {})
                        for plan_data in validated_plans:
                            if 'weather_info' in plan_data:
                                # 保留LLM生成的旅游建议，添加原始天气数据
                                plan_data['weather_info']['raw_data'] = weather_data
                            else:
                                # 如果LLM没有生成weather_info，创建一个
                                plan_data['weather_info'] = {
                                    'raw_data': weather_data,
                                    'travel_recommendations': ["建议根据当地天气情况合理安排行程"]
                                }
                        
                        return validated_plans
                    except json.JSONDecodeError:
                        pass
                
                return []
                
        except Exception as e:
            logger.error(f"LLM生成方案失败: {e}")
            raise
    
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
                formatted_items.append(f"""
  {i+1}. 航空公司: {item.get('airline', 'N/A')}
     出发时间: {item.get('departure_time', 'N/A')}
     到达时间: {item.get('arrival_time', 'N/A')}
     价格: {item.get('price', 'N/A')}元
     评分: {item.get('rating', 'N/A')}
     出发地: {item.get('departure_city', 'N/A')}
     目的地: {item.get('arrival_city', 'N/A')}""")
            
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
        plan_index: int
    ) -> Optional[Dict[str, Any]]:
        """生成单个方案"""
        try:
            # 选择最佳航班
            flight = self._select_best_flight(processed_data.get("flights", []), plan_type)
            
            # 选择最佳酒店
            hotel = self._select_best_hotel(processed_data.get("hotels", []), plan_type)
            
            # 生成每日行程
            daily_itineraries = await self._generate_daily_itineraries(
                processed_data, plan, preferences, plan_type
            )
            
            # 选择餐厅
            restaurants = self._select_restaurants(
                processed_data.get("restaurants", []), plan_type, len(daily_itineraries)
            )
            
            # 选择交通方式
            transportation = self._select_transportation(
                processed_data.get("transportation", [])
            )
            
            # 计算总预算
            total_cost = self._calculate_total_cost(
                flight, hotel, daily_itineraries, restaurants
            )
            
            # 获取天气信息
            weather_info = self._format_weather_info(processed_data.get("weather", {}))
            
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
        plan_type: str
    ) -> List[Dict[str, Any]]:
        """生成每日行程"""
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
    
    def _calculate_total_cost(
        self,
        flight: Optional[Dict[str, Any]],
        hotel: Optional[Dict[str, Any]],
        daily_itineraries: List[Dict[str, Any]],
        restaurants: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """计算总预算"""
        costs = {
            "flight": flight.get("price", 0) if flight else 0,
            "hotel": 0,
            "attractions": 0,
            "meals": 0,
            "transportation": 0,
            "total": 0
        }
        
        # 酒店费用
        if hotel:
            costs["hotel"] = hotel.get("price_per_night", 0) * len(daily_itineraries)
        
        # 景点费用
        for day in daily_itineraries:
            costs["attractions"] += day.get("estimated_cost", 0)
        
        # 餐饮费用（估算）
        costs["meals"] = len(daily_itineraries) * 3 * 50  # 每天3餐，每餐50元
        
        # 交通费用（估算）
        costs["transportation"] = len(daily_itineraries) * 20  # 每天20元交通费
        
        costs["total"] = sum(costs.values())
        
        return costs
    
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
