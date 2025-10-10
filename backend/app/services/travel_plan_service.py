"""
旅行计划服务
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from app.models.travel_plan import TravelPlan, TravelPlanItem
from app.schemas.travel_plan import TravelPlanCreate, TravelPlanUpdate


class TravelPlanService:
    """旅行计划服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_travel_plan(self, plan_data: TravelPlanCreate) -> TravelPlan:
        """创建旅行计划"""
        plan = TravelPlan(**plan_data.dict())
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        return plan
    
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
