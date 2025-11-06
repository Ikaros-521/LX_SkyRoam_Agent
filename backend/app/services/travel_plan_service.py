"""
旅行计划服务
"""
from datetime import datetime, date, timezone
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, or_
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
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
        travel_from: Optional[date] = None,
        travel_to: Optional[date] = None,
        exclude_public: bool = False,
    ) -> Tuple[List[TravelPlanResponse], int]:
        """获取旅行计划列表和总数，支持筛选；评分使用 travel_plan_ratings 的平均分"""
        conditions = []
        if user_id:
            conditions.append(TravelPlan.user_id == user_id)
        if status:
            conditions.append(TravelPlan.status == status)
        if keyword:
            like = f"%{keyword}%"
            conditions.append(or_(
                TravelPlan.title.ilike(like),
                TravelPlan.destination.ilike(like),
                TravelPlan.description.ilike(like)
            ))
        if exclude_public:
            conditions.append(TravelPlan.is_public == False)
        # 评分过滤将使用评分子查询的平均分，不再使用 TravelPlan.score
        # 统一将有时区的时间转换为UTC再去除时区，与数据库的UTC无时区字段比较
        def _normalize(dt: Optional[datetime]) -> Optional[datetime]:
            if not dt:
                return None
            try:
                if dt.tzinfo is not None:
                    return dt.astimezone(timezone.utc).replace(tzinfo=None)
                return dt
            except Exception:
                return None
        
        # 创建时间过滤（保持原逻辑）
        dt_from = _normalize(created_from)
        dt_to = _normalize(created_to)
        if dt_from:
            conditions.append(TravelPlan.created_at >= dt_from)
        if dt_to:
            conditions.append(TravelPlan.created_at <= dt_to)
        
        # 出行日期过滤：将纯日期转换为整日边界
        def day_start(d: Optional[date]) -> Optional[datetime]:
            if not d:
                return None
            try:
                if isinstance(d, datetime):
                    base = _normalize(d) or d
                    return datetime(base.year, base.month, base.day, 0, 0, 0)
                return datetime(d.year, d.month, d.day, 0, 0, 0)
            except Exception:
                return None
        def day_end(d: Optional[date]) -> Optional[datetime]:
            if not d:
                return None
            try:
                if isinstance(d, datetime):
                    base = _normalize(d) or d
                    return datetime(base.year, base.month, base.day, 23, 59, 59, 999999)
                return datetime(d.year, d.month, d.day, 23, 59, 59, 999999)
            except Exception:
                return None
        
        t_from = day_start(travel_from)
        t_to = day_end(travel_to)
        if t_from:
            conditions.append(TravelPlan.end_date >= t_from)
        if t_to:
            conditions.append(TravelPlan.start_date <= t_to)
        
        # 评分平均分子查询（每个方案一条记录）
        rating_subq = (
            select(
                TravelPlanRating.travel_plan_id.label("tp_id"),
                func.avg(TravelPlanRating.score).label("avg_score")
            )
            .group_by(TravelPlanRating.travel_plan_id)
        ).subquery()
        
        # 统计总数（包含评分过滤）
        count_query = (
            select(func.count(TravelPlan.id))
            .select_from(TravelPlan)
            .outerjoin(rating_subq, TravelPlan.id == rating_subq.c.tp_id)
        )
        if conditions:
            count_query = count_query.where(*conditions)
        if min_score is not None:
            count_query = count_query.where(rating_subq.c.avg_score >= float(min_score))
        if max_score is not None:
            count_query = count_query.where(rating_subq.c.avg_score <= float(max_score))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        # 查询列表并携带平均分
        query = (
            select(TravelPlan, rating_subq.c.avg_score)
            .outerjoin(rating_subq, TravelPlan.id == rating_subq.c.tp_id)
            .options(selectinload(TravelPlan.items))
            .order_by(TravelPlan.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if conditions:
            query = query.where(*conditions)
        if min_score is not None:
            query = query.where(rating_subq.c.avg_score >= float(min_score))
        if max_score is not None:
            query = query.where(rating_subq.c.avg_score <= float(max_score))
        
        result = await self.db.execute(query)
        rows = result.all()
        
        # 构建响应：用平均分填充 score（无评分则为 None）
        responses: List[TravelPlanResponse] = []
        for plan, avg_score in rows:
            resp = TravelPlanResponse.from_orm(plan)
            resp.score = float(avg_score) if avg_score is not None else None
            responses.append(resp)
        
        return responses, total
    
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
            await self.db.execute(
                update(TravelPlanRating)
                .where(TravelPlanRating.id == rating.id)
                .values(score=score, comment=comment)
            )
        else:
            new_rating = TravelPlanRating(
                travel_plan_id=plan_id,
                user_id=user_id,
                score=score,
                comment=comment
            )
            self.db.add(new_rating)
        await self.db.commit()
        
        # 汇总
        summary_q = (
            select(func.avg(TravelPlanRating.score), func.count(TravelPlanRating.id))
            .where(TravelPlanRating.travel_plan_id == plan_id)
        )
        summary_res = await self.db.execute(summary_q)
        avg_score, count = summary_res.first() or (None, 0)
        return float(avg_score) if avg_score is not None else 0.0, int(count or 0)

    async def get_ratings(self, plan_id: int, skip: int = 0, limit: int = 10) -> List[TravelPlanRating]:
        """获取评分列表"""
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
        q = (
            select(func.avg(TravelPlanRating.score), func.count(TravelPlanRating.id))
            .where(TravelPlanRating.travel_plan_id == plan_id)
        )
        res = await self.db.execute(q)
        avg_score, count = res.first() or (None, 0)
        return float(avg_score) if avg_score is not None else 0.0, int(count or 0)

    async def get_rating_by_user(self, plan_id: int, user_id: int) -> Optional[TravelPlanRating]:
        """获取某用户对方案的评分(如无则返回None)"""
        q = (
            select(TravelPlanRating)
            .where(
                TravelPlanRating.travel_plan_id == plan_id,
                TravelPlanRating.user_id == user_id
            )
        )
        res = await self.db.execute(q)
        return res.scalar_one_or_none()

    # =============== 公开相关方法 ===============
    async def set_public_status(self, plan_id: int, is_public: bool) -> bool:
        """设置方案公开状态"""
        values = {"is_public": is_public}
        if is_public:
            values["public_at"] = datetime.utcnow()
        else:
            values["public_at"] = None
        await self.db.execute(
            update(TravelPlan)
            .where(TravelPlan.id == plan_id)
            .values(**values)
        )
        await self.db.commit()
        return True

    async def get_public_travel_plans_with_total(
        self,
        skip: int = 0,
        limit: int = 100,
        destination: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> Tuple[List[TravelPlanResponse], int]:
        """获取公开旅行计划列表及总数，支持目的地和关键词筛选"""
        conditions = [TravelPlan.is_public == True]
        if destination:
            conditions.append(TravelPlan.destination.ilike(f"%{destination}%"))
        if keyword:
            like = f"%{keyword}%"
            conditions.append(or_(
                TravelPlan.title.ilike(like),
                TravelPlan.description.ilike(like)
            ))
        # 评分平均分子查询
        rating_subq = (
            select(
                TravelPlanRating.travel_plan_id.label("tp_id"),
                func.avg(TravelPlanRating.score).label("avg_score")
            )
            .group_by(TravelPlanRating.travel_plan_id)
        ).subquery()

        count_q = (
            select(func.count(TravelPlan.id))
            .select_from(TravelPlan)
            .outerjoin(rating_subq, TravelPlan.id == rating_subq.c.tp_id)
            .where(*conditions)
        )
        count_res = await self.db.execute(count_q)
        total = count_res.scalar() or 0

        q = (
            select(TravelPlan, rating_subq.c.avg_score)
            .outerjoin(rating_subq, TravelPlan.id == rating_subq.c.tp_id)
            .options(selectinload(TravelPlan.items))
            .where(*conditions)
            .order_by(TravelPlan.public_at.desc().nulls_last(), TravelPlan.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.db.execute(q)
        rows = res.all()
        responses: List[TravelPlanResponse] = []
        for plan, avg_score in rows:
            resp = TravelPlanResponse.from_orm(plan)
            resp.score = float(avg_score) if avg_score is not None else None
            responses.append(resp)
        return responses, total

    async def get_public_travel_plan(self, plan_id: int) -> Optional[TravelPlan]:
        """获取公开的旅行计划详情（仅公开）"""
        q = (
            select(TravelPlan)
            .options(selectinload(TravelPlan.items))
            .where(TravelPlan.id == plan_id, TravelPlan.is_public == True)
        )
        res = await self.db.execute(q)
        return res.scalar_one_or_none()
