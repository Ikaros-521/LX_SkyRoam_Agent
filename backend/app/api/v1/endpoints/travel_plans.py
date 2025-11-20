"""
旅行计划API端点
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, date

from app.core.database import get_async_db
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
from fastapi.responses import HTMLResponse, JSONResponse, Response, PlainTextResponse, StreamingResponse
import asyncio, time, json
from app.core.config import settings
from fastapi.encoders import jsonable_encoder

# 新增导入
from app.core.security import get_current_user, is_admin
from app.models.user import User
from app.tasks.travel_plan_tasks import (
    generate_travel_plans_task as celery_generate_travel_plans_task,
    refine_travel_plan_task as celery_refine_travel_plan_task,
    export_travel_plan_task as celery_export_travel_plan_task,
)
from celery.result import AsyncResult

router = APIRouter()


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
    plan_source: Optional[str] = Query(
        None,
        description="方案来源过滤: private(仅私有)、public(仅公开)、未传表示全部",
        regex="^(private|public)$"
    ),
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
        plan_source=plan_source,
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
    return TravelPlanResponse.from_orm(plan)

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
    return TravelPlanResponse.from_orm(plan)


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
    # 防止重复触发生成任务
    if plan.status == "generating":
        raise HTTPException(status_code=409, detail="该计划正在生成中，请稍候")
    # 先更新状态为生成中并加锁，避免并发竞争
    await agent_service._update_plan_status(plan_id, "generating")
    async_result = celery_generate_travel_plans_task.delay(
        plan_id,
        request.preferences,
        request.requirements,
    )
    return {
        "message": "旅行方案生成任务已启动",
        "plan_id": plan_id,
        "status": "generating",
        "task_id": async_result.id,
    }


@router.post("/{plan_id}/refine")
async def refine_travel_plan_async(
    plan_id: int,
    request_data: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """细化旅行方案（Celery异步，需拥有或管理员）"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权细化该计划")
    plan_index = request_data.get("plan_index")
    refinements = request_data.get("refinements") or {}
    if plan_index is None:
        raise HTTPException(status_code=400, detail="缺少plan_index参数")
    async_result = celery_refine_travel_plan_task.delay(plan_id, plan_index, refinements)
    return {
        "message": "方案细化任务已启动",
        "plan_id": plan_id,
        "task_id": async_result.id,
    }


@router.get("/tasks/status/{task_id}")
async def get_task_status(task_id: str, current_user: User = Depends(get_current_user)):
    """查询Celery任务状态（需登录）"""
    try:
        task_result = AsyncResult(task_id)
        state = task_result.state
        if state == "PENDING":
            return {"task_id": task_id, "status": "pending", "message": "任务等待执行"}
        if state == "PROGRESS":
            info = task_result.info or {}
            return {
                "task_id": task_id,
                "status": "progress",
                "current": info.get("current", 0),
                "total": info.get("total", 100),
                "message": info.get("status", "执行中"),
            }
        if state == "SUCCESS":
            return {"task_id": task_id, "status": "success", "result": task_result.result}
        # FAILURE 或其他状态
        return {"task_id": task_id, "status": "failed", "message": str(task_result.info)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")


@router.delete("/tasks/cancel/{task_id}")
async def cancel_task(task_id: str, current_user: User = Depends(get_current_user)):
    """取消Celery任务（需登录）"""
    try:
        task_result = AsyncResult(task_id)
        task_result.revoke(terminate=True)
        return {"task_id": task_id, "status": "cancelled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")


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


@router.get("/{plan_id}/status/stream")
async def stream_generation_status(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """SSE流式返回方案生成状态（需拥有或管理员）"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权查看该计划状态")

    start_ts = time.time()
    max_seconds = settings.PLAN_STATUS_STREAM_MAX_SECONDS

    async def event_generator():
        last_status = None
        while True:
            try:
                current_plan = await service.get_travel_plan(plan_id)
                if current_plan is not None:
                    await db.refresh(current_plan)
                status = current_plan.status
                elapsed = time.time() - start_ts
                base_progress = min(90, 10 + (elapsed / max_seconds) * 80)
                progress = 100 if status == "completed" else (0 if status == "failed" else round(base_progress, 2))

                payload = {
                    "plan_id": plan_id,
                    "status": status,
                    "progress": progress,
                    "preview": None,
                }

                try:
                    gp = current_plan.generated_plans or []
                    if isinstance(gp, list):
                        for p in gp:
                            if p and p.get("is_preview") and p.get("preview_type") == "raw_data_preview":
                                payload["preview"] = p
                                break
                except Exception:
                    payload["preview"] = None

                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                if status in ("completed", "failed"):
                    break
                if elapsed >= max_seconds:
                    timeout_payload = {
                        "plan_id": plan_id,
                        "status": "timeout",
                        "progress": round(base_progress, 2),
                    }
                    yield f"data: {json.dumps(timeout_payload, ensure_ascii=False)}\n\n"
                    break

                await asyncio.sleep(settings.PLAN_STATUS_STREAM_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                err_payload = {"plan_id": plan_id, "status": "error", "message": str(e)}
                yield f"data: {json.dumps(err_payload, ensure_ascii=False)}\n\n"
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


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


@router.post("/{plan_id}/export-async")
async def export_travel_plan_async(
    plan_id: int,
    format: str = "pdf",  # pdf, json, html
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """导出旅行计划（Celery异步，需拥有或管理员）"""
    allowed = {"json", "html", "pdf"}
    if format not in allowed:
        raise HTTPException(status_code=400, detail=f"不支持的导出格式: {format}")
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    if not (is_admin(current_user) or plan.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="无权导出该计划")
    async_result = celery_export_travel_plan_task.delay(plan_id, format)
    return {
        "message": "导出任务已启动",
        "plan_id": plan_id,
        "format": format,
        "task_id": async_result.id,
    }

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
