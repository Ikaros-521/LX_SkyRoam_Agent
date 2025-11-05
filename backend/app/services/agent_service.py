"""
AI Agent核心服务
负责数据收集、处理、方案生成
"""

import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import json
from datetime import datetime

from app.core.config import settings
from app.models.travel_plan import TravelPlan
from app.services.data_collector import DataCollector
from app.services.data_processor import DataProcessor
from app.services.plan_generator import PlanGenerator
from app.services.plan_scorer import PlanScorer
from app.tools.mcp_client import MCPClient
from app.tools.openai_client import openai_client


class AgentService:
    """AI Agent服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.data_collector = DataCollector()
        self.data_processor = DataProcessor()
        self.plan_generator = PlanGenerator()
        self.plan_scorer = PlanScorer()
        self.mcp_client = MCPClient()
        self.openai_client = openai_client
    
    async def generate_travel_plans(
        self, 
        plan_id: int, 
        preferences: Optional[Dict[str, Any]] = None,
        requirements: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        生成旅行方案的主流程
        
        Args:
            plan_id: 旅行计划ID
            preferences: 用户偏好
            requirements: 特殊要求
            
        Returns:
            bool: 是否成功生成
        """
        try:
            logger.info(f"开始生成旅行方案，计划ID: {plan_id}")
            
            # 1. 获取旅行计划信息
            plan = await self._get_travel_plan(plan_id)
            if not plan:
                logger.error(f"旅行计划不存在: {plan_id}")
                return False
            
            # 2. 更新状态为生成中
            await self._update_plan_status(plan_id, "generating")
            
            # 3. 数据收集阶段
            logger.info("开始数据收集...")
            raw_data = await self._collect_data(plan, preferences, requirements)
            logger.info("保存原始数据预览并提前展示...")
            await self._save_raw_preview(plan_id, raw_data, plan)
            # 4. 数据清洗和评分
            logger.info("开始数据清洗和评分...")
            processed_data = await self._process_data(raw_data, plan)
            
            # 5. 生成多个方案
            logger.info("开始生成旅行方案...")
            generated_plans = await self._generate_plans(processed_data, plan, preferences, raw_data)
            
            # 6. 方案评分和排序
            logger.info("开始方案评分和排序...")
            scored_plans = await self._score_plans(generated_plans, plan, preferences)
            
            # 7. 保存结果
            await self._save_generated_plans(plan_id, scored_plans)
            
            # 8. 更新状态为完成
            await self._update_plan_status(plan_id, "completed")
            
            logger.info(f"旅行方案生成完成，计划ID: {plan_id}")
            return True
            
        except Exception as e:
            logger.error(f"生成旅行方案失败: {e}")
            await self._update_plan_status(plan_id, "failed")
            return False
    
    async def _get_travel_plan(self, plan_id: int) -> Optional[TravelPlan]:
        """获取旅行计划"""
        from sqlalchemy import select
        from app.models.travel_plan import TravelPlan
        
        result = await self.db.execute(select(TravelPlan).where(TravelPlan.id == plan_id))
        return result.scalar_one_or_none()
    
    async def _update_plan_status(self, plan_id: int, status: str):
        """更新计划状态"""
        from sqlalchemy import update
        from app.models.travel_plan import TravelPlan
        
        await self.db.execute(
            update(TravelPlan)
            .where(TravelPlan.id == plan_id)
            .values(status=status)
        )
        await self.db.commit()
    
    async def _collect_data(
        self, 
        plan, 
        preferences: Optional[Dict[str, Any]] = None,
        requirements: Optional[Dict[str, Any]] = None,
        interval_seconds: float = 1.0  # 每个任务启动之间的时间间隔
    ) -> Dict[str, Any]:
        """数据收集阶段：在任务之间增加启动间隔"""
        
        logger.info(f"开始收集 {plan.destination} 的各类数据（每个任务间隔 {interval_seconds}s 启动）")

        # 延迟创建任务的方式（保证延迟生效）
        coro_factories = [
            lambda: self.data_collector.collect_flight_data(plan.departure, plan.destination, plan.start_date, plan.end_date),
            lambda: self.data_collector.collect_hotel_data(plan.destination, plan.start_date, plan.end_date),
            lambda: self.data_collector.collect_attraction_data(plan.destination),
            lambda: self.data_collector.collect_weather_data(plan.destination, plan.start_date, plan.end_date),
            lambda: self.data_collector.collect_restaurant_data(plan.destination),
            lambda: self.data_collector.collect_transportation_data(plan.departure, plan.destination, plan.transportation),
            lambda: self.data_collector.collect_xiaohongshu_data(plan.destination),
        ]

        tasks = []
        for i, factory in enumerate(coro_factories):
            if i > 0 and interval_seconds > 0:
                logger.debug(f"等待 {interval_seconds}s 后启动下一个任务 ({i+1}/{len(coro_factories)})")
                await asyncio.sleep(interval_seconds)
            # 延迟创建 + 调度任务
            task = asyncio.create_task(factory())
            tasks.append(task)
            logger.debug(f"已启动任务 {i+1}/{len(coro_factories)}")

        # 并行等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 构造结果字典
        return {
            "flights": results[0] if not isinstance(results[0], Exception) else [],
            "hotels": results[1] if not isinstance(results[1], Exception) else [],
            "attractions": results[2] if not isinstance(results[2], Exception) else [],
            "weather": results[3] if not isinstance(results[3], Exception) else {},
            "restaurants": results[4] if not isinstance(results[4], Exception) else [],
            "transportation": results[5] if not isinstance(results[5], Exception) else [],
            "xiaohongshu_notes": results[6] if not isinstance(results[6], Exception) else []
        }
    
    async def _process_data(
        self, 
        raw_data: Dict[str, Any], 
        plan: TravelPlan
    ) -> Dict[str, Any]:
        """数据清洗和评分"""
        
        processed_data = {}
        
        for data_type, data in raw_data.items():
            if data_type == "weather":
                # 天气数据不需要清洗
                processed_data[data_type] = data
            else:
                # 其他数据需要清洗和评分
                processed_data[data_type] = await self.data_processor.process_data(
                    data, data_type, plan
                )
        
        return processed_data
    
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
    
    async def _generate_plans(
        self, 
        processed_data: Dict[str, Any], 
        plan: TravelPlan,
        preferences: Optional[Dict[str, Any]] = None,
        raw_data: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """生成多个旅行方案"""
        
        # 使用LLM增强的方案生成
        try:
            # 首先尝试使用LLM分析数据并生成方案
            if self.openai_client.api_key:
                return await self.plan_generator.generate_plans(
                    processed_data, plan, preferences, raw_data
                )
            else:
                logger.info("OpenAI API密钥未配置，直接使用原始数据")
                return await self.plan_generator.generate_plans(
                    processed_data, plan, preferences, raw_data
                )
        except asyncio.TimeoutError:
            logger.warning("LLM数据增强超时，使用原始数据")
            return await self.plan_generator.generate_plans(
                processed_data, plan, preferences, raw_data
            )
        except Exception as e:
            logger.warning(f"LLM增强数据失败，使用原始数据: {e}")
            return await self.plan_generator.generate_plans(
                processed_data, plan, preferences, raw_data
            )
    
    async def _score_plans(
        self, 
        plans: List[Dict[str, Any]], 
        plan: TravelPlan,
        preferences: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """方案评分和排序"""
        
        scored_plans = []
        
        for plan_data in plans:
            score = await self.plan_scorer.score_plan(plan_data, plan, preferences)
            plan_data["score"] = score
            scored_plans.append(plan_data)
        
        # 按评分排序
        scored_plans.sort(key=lambda x: x["score"], reverse=True)
        
        return scored_plans
    
    def _serialize_for_json(self, obj):
        """递归处理对象，将datetime对象转换为字符串"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._serialize_for_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_for_json(item) for item in obj]
        else:
            return obj

    async def _save_generated_plans(
        self, 
        plan_id: int, 
        plans: List[Dict[str, Any]]
    ):
        """保存生成的方案"""
        from sqlalchemy import update
        from app.models.travel_plan import TravelPlan
        
        # 序列化处理，确保没有datetime对象
        serialized_plans = self._serialize_for_json(plans)
        
        await self.db.execute(
            update(TravelPlan)
            .where(TravelPlan.id == plan_id)
            .values(generated_plans=serialized_plans)
        )
        await self.db.commit()
    
    async def refine_plan(
        self, 
        plan_id: int, 
        plan_index: int,
        refinements: Dict[str, Any]
    ) -> bool:
        """细化旅行方案"""
        try:
            # 获取当前方案
            plan = await self._get_travel_plan(plan_id)
            if not plan or not plan.generated_plans:
                return False
            
            current_plan = plan.generated_plans[plan_index]
            
            # 应用细化
            refined_plan = await self.plan_generator.refine_plan(
                current_plan, refinements
            )
            
            # 更新方案
            plan.generated_plans[plan_index] = refined_plan
            await self._save_generated_plans(plan_id, plan.generated_plans)
            
            return True
            
        except Exception as e:
            logger.error(f"细化方案失败: {e}")
            return False
    
    async def get_plan_recommendations(
        self, 
        plan_id: int
    ) -> List[Dict[str, Any]]:
        """获取方案推荐"""
        try:
            plan = await self._get_travel_plan(plan_id)
            if not plan:
                return []
            
            # 基于用户偏好和历史数据生成推荐
            recommendations = await self.plan_generator.generate_recommendations(plan)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"获取推荐失败: {e}")
            return []

    async def _save_preview_plan(self, plan_id: int, preview_plan: Dict[str, Any]):
        """保存快速预览方案到 generated_plans 以便前端提前展示"""
        from sqlalchemy import update
        from app.models.travel_plan import TravelPlan
        # 将预览方案放入列表，并做序列化处理
        serialized_preview = self._serialize_for_json([preview_plan])
        await self.db.execute(
            update(TravelPlan)
            .where(TravelPlan.id == plan_id)
            .values(generated_plans=serialized_preview)
        )
        await self.db.commit()

    async def _save_raw_preview(self, plan_id: int, raw_data: Dict[str, Any], plan: TravelPlan):
        """将数据收集阶段的原始数据保存为预览，供前端提前展示"""
        from sqlalchemy import update
        from app.models.travel_plan import TravelPlan
        # 选择展示数量
        MAX_XHS = 8
        MAX_FLIGHTS = 3
        MAX_HOTELS = 3
        MAX_ATTRACTIONS = 6
        MAX_RESTAURANTS = 6
    
        def top_n(items, n, key=None, reverse=True):
            try:
                if not isinstance(items, list):
                    return []
                if key:
                    items = sorted(items, key=lambda x: x.get(key, 0), reverse=reverse)
                return items[:n]
            except Exception:
                return items[:n] if isinstance(items, list) else []
    
        sections = {
            "xiaohongshu_notes": top_n(raw_data.get("xiaohongshu_notes", []), MAX_XHS, key="likes"),
            "flights": top_n(raw_data.get("flights", []), MAX_FLIGHTS, key="price", reverse=False),
            "hotels": top_n(raw_data.get("hotels", []), MAX_HOTELS, key="rating"),
            "attractions": top_n(raw_data.get("attractions", []), MAX_ATTRACTIONS, key="rating"),
            "restaurants": top_n(raw_data.get("restaurants", []), MAX_RESTAURANTS, key="rating"),
            "weather": raw_data.get("weather", {}),
        }
    
        preview = {
            "id": "preview_raw_1",
            "is_preview": True,
            "preview_type": "raw_data_preview",
            "title": f"{getattr(plan, 'destination', '')} 数据预览",
            "sections": sections,
            "generated_at": datetime.utcnow().isoformat(),
        }
    
        serialized_preview = self._serialize_for_json([preview])
        await self.db.execute(
            update(TravelPlan)
            .where(TravelPlan.id == plan_id)
            .values(generated_plans=serialized_preview)
        )
        await self.db.commit()
