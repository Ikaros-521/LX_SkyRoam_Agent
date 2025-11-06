"""
旅行计划服务
"""

from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload

from app.models.travel_plan import TravelPlan, TravelPlanItem, TravelPlanRating
from app.schemas.travel_plan import TravelPlanCreate, TravelPlanUpdate, TravelPlanResponse


class TravelPlanService:
    """旅行计划服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_travel_plan(self, plan_data: TravelPlanCreate) -> TravelPlanResponse:
        """创建旅行计划"""
        plan = TravelPlan(**plan_data.dict())
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        
        # 手动构建响应，避免懒加载问题
        return TravelPlanResponse.from_orm(plan)
    
    async def get_travel_plans(
        self, 
        skip: int = 0, 
        limit: int = 100,
        user_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[TravelPlan]:
        """获取旅行计划列表"""
        query = select(TravelPlan).options(selectinload(TravelPlan.items))
        
        if user_id:
            query = query.where(TravelPlan.user_id == user_id)
        if status:
            query = query.where(TravelPlan.status == status)
        
        query = query.offset(skip).limit(limit).order_by(TravelPlan.created_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_travel_plans_with_total(
        self, 
        skip: int = 0, 
        limit: int = 100,
        user_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> Tuple[List[TravelPlan], int]:
        """获取旅行计划列表和总数"""
        # 构建查询条件
        conditions = []
        if user_id:
            conditions.append(TravelPlan.user_id == user_id)
        if status:
            conditions.append(TravelPlan.status == status)
        
        # 获取总数
        count_query = select(func.count(TravelPlan.id))
        if conditions:
            count_query = count_query.where(*conditions)
        
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()
        
        # 获取数据
        query = select(TravelPlan).options(selectinload(TravelPlan.items))
        if conditions:
            query = query.where(*conditions)
        
        query = query.offset(skip).limit(limit).order_by(TravelPlan.created_at.desc())
        
        result = await self.db.execute(query)
        plans = result.scalars().all()
        
        return plans, total
    
    async def get_travel_plan(self, plan_id: int) -> Optional[TravelPlan]:
        """获取单个旅行计划"""
        result = await self.db.execute(
            select(TravelPlan)
            .options(selectinload(TravelPlan.items))
            .where(TravelPlan.id == plan_id)
        )
        return result.scalar_one_or_none()
    
    async def update_travel_plan(
        self, 
        plan_id: int, 
        plan_data: TravelPlanUpdate
    ) -> Optional[TravelPlan]:
        """更新旅行计划"""
        update_data = plan_data.dict(exclude_unset=True)
        
        if update_data:
            await self.db.execute(
                update(TravelPlan)
                .where(TravelPlan.id == plan_id)
                .values(**update_data)
            )
            await self.db.commit()
        
        return await self.get_travel_plan(plan_id)
    
    async def delete_travel_plan(self, plan_id: int) -> bool:
        """删除旅行计划"""
        result = await self.db.execute(
            delete(TravelPlan).where(TravelPlan.id == plan_id)
        )
        await self.db.commit()
        return result.rowcount > 0
    
    async def select_plan(self, plan_id: int, plan_index: int) -> bool:
        """选择最终方案"""
        plan = await self.get_travel_plan(plan_id)
        if not plan or not plan.generated_plans:
            return False
        
        if plan_index >= len(plan.generated_plans):
            return False
        
        selected_plan = plan.generated_plans[plan_index]
        
        await self.db.execute(
            update(TravelPlan)
            .where(TravelPlan.id == plan_id)
            .values(selected_plan=selected_plan)
        )
        await self.db.commit()
        
        return True

    async def delete_travel_plans(self, ids: List[int]) -> int:
        """批量删除旅行计划，返回删除条数"""
        if not ids:
            return 0
        result = await self.db.execute(
            delete(TravelPlan).where(TravelPlan.id.in_(ids))
        )
        await self.db.commit()
        return result.rowcount or 0

    # =============== 评分相关方法 ===============
    async def upsert_rating(self, plan_id: int, user_id: int, score: int, comment: Optional[str]) -> Tuple[float, int]:
        """新增或更新用户对某方案的评分，并返回最新汇总(平均分, 数量)"""
        # 先查是否已有评分
        existing_q = select(TravelPlanRating).where(
            TravelPlanRating.travel_plan_id == plan_id,
            TravelPlanRating.user_id == user_id
        )
        existing_res = await self.db.execute(existing_q)
        rating = existing_res.scalar_one_or_none()
        if rating:
            rating.score = score
            rating.comment = comment
        else:
            rating = TravelPlanRating(
                travel_plan_id=plan_id,
                user_id=user_id,
                score=score,
                comment=comment
            )
            self.db.add(rating)
        await self.db.commit()

        # 计算汇总
        summary_q = select(func.avg(TravelPlanRating.score), func.count(TravelPlanRating.id)).where(
            TravelPlanRating.travel_plan_id == plan_id
        )
        summary_res = await self.db.execute(summary_q)
        avg, cnt = summary_res.first()
        return float(avg or 0), int(cnt or 0)

    async def get_ratings(self, plan_id: int, skip: int = 0, limit: int = 10) -> List[TravelPlanRating]:
        """获取某方案的评分列表"""
        q = (
            select(TravelPlanRating)
            .where(TravelPlanRating.travel_plan_id == plan_id)
            .order_by(TravelPlanRating.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.db.execute(q)
        return res.scalars().all()

    async def get_rating_summary(self, plan_id: int) -> Tuple[float, int]:
        """获取评分汇总(平均分, 数量)"""
        summary_q = select(func.avg(TravelPlanRating.score), func.count(TravelPlanRating.id)).where(
            TravelPlanRating.travel_plan_id == plan_id
        )
        summary_res = await self.db.execute(summary_q)
        avg, cnt = summary_res.first()
        return float(avg or 0), int(cnt or 0)

    async def get_rating_by_user(self, plan_id: int, user_id: int) -> Optional[TravelPlanRating]:
        """获取当前用户对该方案的评分记录"""
        q = select(TravelPlanRating).where(
            TravelPlanRating.travel_plan_id == plan_id,
            TravelPlanRating.user_id == user_id
        )
        res = await self.db.execute(q)
        return res.scalar_one_or_none()
