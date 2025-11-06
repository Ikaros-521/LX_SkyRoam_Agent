"""
旅行计划API端点
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, date

from app.core.database import get_async_db, AsyncSessionLocal
from app.schemas.travel_plan import (
    TravelPlanCreate, 
    TravelPlanCreateRequest,
    TravelPlanUpdate, 
    TravelPlanResponse,
    TravelPlanGenerateRequest,
    TravelPlanBatchDeleteRequest
)
from app.services.travel_plan_service import TravelPlanService
from app.services.agent_service import AgentService
from loguru import logger
from fastapi.responses import HTMLResponse, JSONResponse, Response, PlainTextResponse
from fastapi.encoders import jsonable_encoder

# 新增导入
from app.core.security import get_current_user, is_admin
from app.models.user import User

router = APIRouter()


async def generate_travel_plans_task(
    plan_id: int,
    preferences: Optional[dict] = None,
    requirements: Optional[dict] = None
):
    """后台任务：生成旅行方案"""
    async with AsyncSessionLocal() as db:
        try:
            logger.info(f"开始后台任务：生成旅行方案 {plan_id}")
            agent_service = AgentService(db)
            success = await agent_service.generate_travel_plans(
                plan_id, preferences, requirements
            )
            if success:
                logger.info(f"后台任务完成：旅行方案 {plan_id} 生成成功")
            else:
                logger.error(f"后台任务失败：旅行方案 {plan_id} 生成失败")
        except Exception as e:
            logger.error(f"后台任务异常：{e}")
            # 确保状态更新为失败
            try:
                from sqlalchemy import update
                from app.models.travel_plan import TravelPlan
                await db.execute(
                    update(TravelPlan)
                    .where(TravelPlan.id == plan_id)
                    .values(status="failed")
                )
                await db.commit()
            except Exception as update_error:
                logger.error(f"更新状态失败: {update_error}")


@router.post("/", response_model=TravelPlanResponse)
async def create_travel_plan(
    plan_data: TravelPlanCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """创建新的旅行计划（绑定到当前用户）"""
    service = TravelPlanService(db)
    data = plan_data.dict()
    data["user_id"] = current_user.id
    return await service.create_travel_plan(TravelPlanCreate(**data))


@router.get("/")
async def get_travel_plans(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    created_from: Optional[datetime] = Query(None, description="创建时间起(ISO8601, 支持Z)"),
    created_to: Optional[datetime] = Query(None, description="创建时间止(ISO8601, 支持Z)"),
    travel_from: Optional[date] = Query(None, description="出行日期起(YYYY-MM-DD)"),
    travel_to: Optional[date] = Query(None, description="出行日期止(YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取旅行计划列表（普通用户仅能查看自己的，管理员可查看所有）"""
    service = TravelPlanService(db)
    # 非管理员强制限定为当前用户
    effective_user_id = user_id if is_admin(current_user) else current_user.id
    plans, total = await service.get_travel_plans_with_total(
        skip=skip,
        limit=limit,
        user_id=effective_user_id,
        status=status,
        keyword=keyword,
        min_score=min_score,
        max_score=max_score,
        created_from=created_from,
        created_to=created_to,
        travel_from=travel_from,
        travel_to=travel_to,
        exclude_public=(not is_admin(current_user)),
    )
    return {
        "plans": plans,
        "total": total,
        "skip": skip,
        "limit": limit,
    }

# =============== 公开访问相关端点 ===============
@router.get("/public")
async def list_public_travel_plans(
    skip: int = 0,
    limit: int = 100,
    destination: Optional[str] = None,
    keyword: Optional[str] = None,
    min_score: Optional[float] = None,
    travel_from: Optional[date] = Query(None, description="出行日期起(YYYY-MM-DD)"),
    travel_to: Optional[date] = Query(None, description="出行日期止(YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_async_db),
):
    """公开列表：无需登录，支持目的地、关键词、评分与出行日期检索"""
    service = TravelPlanService(db)
    plans, total = await service.get_public_travel_plans_with_total(
        skip=skip,
        limit=limit,
        destination=destination,
        keyword=keyword,
        min_score=min_score,
        travel_from=travel_from,
        travel_to=travel_to,
    )
    return {
        "plans": plans,
        "total": total,
        "skip": skip,
        "limit": limit,
    }

@router.get("/public/{plan_id}", response_model=TravelPlanResponse)
async def get_public_travel_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """公开详情：无需登录，仅公开计划可访问"""
    service = TravelPlanService(db)
    plan = await service.get_public_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="公开旅行计划不存在")
    return plan

@router.put("/{plan_id}/publish")
async def publish_travel_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """发布为公开方案（需拥有或管理员）"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权发布该计划")
    await service.set_public_status(plan_id, True)
    plan = await service.get_travel_plan(plan_id)
    return TravelPlanResponse.from_orm(plan)

@router.put("/{plan_id}/unpublish")
async def unpublish_travel_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """取消公开（需拥有或管理员）"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权取消公开该计划")
    await service.set_public_status(plan_id, False)
    plan = await service.get_travel_plan(plan_id)
    return TravelPlanResponse.from_orm(plan)


@router.get("/{plan_id}", response_model=TravelPlanResponse)
async def get_travel_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个旅行计划（需拥有或管理员）"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权访问该计划")
    return plan


@router.put("/{plan_id}", response_model=TravelPlanResponse)
async def update_travel_plan(
    plan_id: int,
    plan_data: TravelPlanUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """更新旅行计划（需拥有或管理员）"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权更新该计划")
    plan = await service.update_travel_plan(plan_id, plan_data)
    return plan


@router.delete("/{plan_id}")
async def delete_travel_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """删除旅行计划（需拥有或管理员）"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权删除该计划")
    success = await service.delete_travel_plan(plan_id)
    if not success:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    return {"message": "旅行计划已删除"}


@router.post("/batch-delete")
async def batch_delete_travel_plans(
    payload: TravelPlanBatchDeleteRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """批量删除旅行计划（仅管理员）"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="仅管理员可批量删除")
    service = TravelPlanService(db)
    deleted_count = await service.delete_travel_plans(payload.ids)
    return {"deleted": deleted_count}


@router.post("/{plan_id}/generate")
async def generate_travel_plans(
    plan_id: int,
    request: TravelPlanGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """生成旅行方案（需拥有或管理员）"""
    service = TravelPlanService(db)
    agent_service = AgentService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权生成该计划")
    background_tasks.add_task(
        generate_travel_plans_task,
        plan_id,
        request.preferences,
        request.requirements,
    )
    return {
        "message": "旅行方案生成任务已启动",
        "plan_id": plan_id,
        "status": "generating",
    }


@router.get("/{plan_id}/status")
async def get_generation_status(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取方案生成状态（需拥有或管理员）"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权查看该计划状态")
    return {
        "plan_id": plan_id,
        "status": plan.status,
        "generated_plans": plan.generated_plans,
        "selected_plan": plan.selected_plan,
    }


@router.post("/{plan_id}/select-plan")
async def select_travel_plan(
    plan_id: int,
    request_data: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """选择最终旅行方案（需拥有或管理员）"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权选择该计划方案")
    plan_index = request_data.get("plan_index")
    if plan_index is None:
        raise HTTPException(status_code=400, detail="缺少plan_index参数")
    success = await service.select_plan(plan_id, plan_index)
    if not success:
        raise HTTPException(status_code=400, detail="选择方案失败")
    return {"message": "方案选择成功"}


@router.post("/{plan_id}/export")
async def export_travel_plan_post(
    plan_id: int,
    format: str = "pdf",  # pdf, json, html
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """导出旅行计划（POST，同步返回，与GET一致）"""
    return await export_travel_plan(plan_id=plan_id, format=format, db=db, current_user=current_user)

# =============== 评分相关端点 ===============
from app.schemas.travel_plan import (
    TravelPlanRatingCreate,
    TravelPlanRatingResponse,
    TravelPlanRatingSummary,
)

@router.post("/{plan_id}/ratings")
async def rate_travel_plan(
    plan_id: int,
    payload: TravelPlanRatingCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """对旅行计划进行评分（任何登录用户可评分）"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    # 允许任意登录用户评分，无需拥有权限
    avg, cnt = await service.upsert_rating(plan_id, current_user.id, payload.score, payload.comment)
    return {"message": "评分已提交", "summary": {"average": avg, "count": cnt}}

@router.get("/{plan_id}/ratings", response_model=List[TravelPlanRatingResponse])
async def list_plan_ratings(
    plan_id: int,
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取旅行计划的评分列表（登录用户可查看）"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    ratings = await service.get_ratings(plan_id, skip=skip, limit=limit)
    return ratings

@router.get("/{plan_id}/ratings/summary", response_model=TravelPlanRatingSummary)
async def get_plan_rating_summary(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取评分汇总（平均分、数量）"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    avg, cnt = await service.get_rating_summary(plan_id)
    return {"average": avg, "count": cnt}

@router.get("/{plan_id}/ratings/me", response_model=Optional[TravelPlanRatingResponse])
async def get_my_plan_rating(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户对该计划的评分（用于前端回填）"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    rating = await service.get_rating_by_user(plan_id, current_user.id)
    return rating

def _render_plan_html(plan_data: dict) -> str:
    title = plan_data.get("title") or f"旅行方案 #{plan_data.get('id', '')}"
    destination = plan_data.get("destination", "")
    description = plan_data.get("description", "")
    score = plan_data.get("score")
    duration_days = plan_data.get("duration_days")
    selected_plan = plan_data.get("selected_plan") or {}
    items = plan_data.get("items") or []
    
    def safe(v):
        return v if v is not None else ""
    
    html = f"""
    <!doctype html>
    <html lang=\"zh\">
    <head>
      <meta charset=\"utf-8\" />
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
      <title>{safe(title)}</title>
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', 'Liberation Sans', sans-serif; margin: 24px; color: #222; }}
        h1 {{ margin: 0 0 8px; font-size: 24px; }}
        .meta {{ color: #666; margin-bottom: 16px; }}
        .section {{ margin: 16px 0; }}
        .item {{ border: 1px solid #eee; border-radius: 6px; padding: 12px; margin: 8px 0; }}
        .item-title {{ font-weight: 600; margin-bottom: 6px; }}
        .item-desc {{ color: #555; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #eee; padding: 8px; text-align: left; }}
      </style>
    </head>
    <body>
      <h1>{safe(title)}</h1>
      <div class=\"meta\">目的地：{safe(destination)} | 天数：{safe(duration_days)} | 评分：{safe(score)}</div>
      <div class=\"section\">
        <h2>方案简介</h2>
        <p class=\"item-desc\">{safe(description)}</p>
      </div>
      <div class=\"section\">
        <h2>最终选择的方案</h2>
        <pre style=\"white-space: pre-wrap; background: #fafafa; border: 1px solid #eee; padding: 12px; border-radius: 6px;\">{safe(str(selected_plan))}</pre>
      </div>
      <div class=\"section\">
        <h2>行程项目</h2>
        {''.join([
          f"<div class='item'><div class='item-title'>{safe(i.get('title'))}</div>"
          f"<div class='item-desc'>{safe(i.get('description'))}</div>"
          f"<div>类型：{safe(i.get('item_type'))}</div>"
          f"<div>位置：{safe(i.get('location'))}</div>"
          f"<div>地址：{safe(i.get('address'))}</div>"
          f"</div>" for i in items
        ])}
      </div>
    </body>
    </html>
    """
    return html

@router.get("/{plan_id}/export")
async def export_travel_plan(
    plan_id: int,
    format: str = "pdf",  # pdf, json, html
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """导出旅行计划（需拥有或管理员）"""
    allowed = {"json", "html", "pdf"}
    if format not in allowed:
        raise HTTPException(status_code=400, detail=f"不支持的导出格式: {format}")
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权导出该计划")
    plan_data = TravelPlanResponse.from_orm(plan).dict()
    if format == "json":
        return JSONResponse(content=jsonable_encoder(plan_data))
    elif format == "html":
        html = _render_plan_html(plan_data)
        return HTMLResponse(content=html)
    else:  # pdf
        return PlainTextResponse(content="PDF 导出暂未实现", status_code=501)

@router.post("/{plan_id}/export")
async def export_travel_plan_post(
    plan_id: int,
    format: str = "pdf",  # pdf, json, html
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """导出旅行计划（POST，同步返回，与GET一致）"""
    return await export_travel_plan(plan_id=plan_id, format=format, db=db, current_user=current_user)
