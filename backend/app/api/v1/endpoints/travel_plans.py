"""
旅行计划API端点
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from app.core.database import get_async_db
from app.schemas.travel_plan import (
    TravelPlanCreate, 
    TravelPlanUpdate, 
    TravelPlanResponse,
    TravelPlanGenerateRequest
)
from app.services.travel_plan_service import TravelPlanService
from app.services.agent_service import AgentService

router = APIRouter()


@router.post("/", response_model=TravelPlanResponse)
async def create_travel_plan(
    plan_data: TravelPlanCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """创建新的旅行计划"""
    service = TravelPlanService(db)
    return await service.create_travel_plan(plan_data)


@router.get("/", response_model=List[TravelPlanResponse])
async def get_travel_plans(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db)
):
    """获取旅行计划列表"""
    service = TravelPlanService(db)
    return await service.get_travel_plans(
        skip=skip, 
        limit=limit, 
        user_id=user_id, 
        status=status
    )


@router.get("/{plan_id}", response_model=TravelPlanResponse)
async def get_travel_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """获取单个旅行计划"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    return plan


@router.put("/{plan_id}", response_model=TravelPlanResponse)
async def update_travel_plan(
    plan_id: int,
    plan_data: TravelPlanUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    """更新旅行计划"""
    service = TravelPlanService(db)
    plan = await service.update_travel_plan(plan_id, plan_data)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    return plan


@router.delete("/{plan_id}")
async def delete_travel_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """删除旅行计划"""
    service = TravelPlanService(db)
    success = await service.delete_travel_plan(plan_id)
    if not success:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    return {"message": "旅行计划已删除"}


@router.post("/{plan_id}/generate")
async def generate_travel_plans(
    plan_id: int,
    request: TravelPlanGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    """生成旅行方案"""
    service = TravelPlanService(db)
    agent_service = AgentService(db)
    
    # 检查计划是否存在
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    
    # 启动后台任务生成方案
    background_tasks.add_task(
        agent_service.generate_travel_plans,
        plan_id,
        request.preferences,
        request.requirements
    )
    
    return {
        "message": "旅行方案生成任务已启动",
        "plan_id": plan_id,
        "status": "generating"
    }


@router.get("/{plan_id}/status")
async def get_generation_status(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """获取方案生成状态"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    
    return {
        "plan_id": plan_id,
        "status": plan.status,
        "generated_plans": plan.generated_plans,
        "selected_plan": plan.selected_plan
    }


@router.post("/{plan_id}/select-plan")
async def select_travel_plan(
    plan_id: int,
    plan_index: int,
    db: AsyncSession = Depends(get_async_db)
):
    """选择最终旅行方案"""
    service = TravelPlanService(db)
    success = await service.select_plan(plan_id, plan_index)
    if not success:
        raise HTTPException(status_code=400, detail="选择方案失败")
    
    return {"message": "方案选择成功"}


@router.post("/{plan_id}/export")
async def export_travel_plan(
    plan_id: int,
    format: str = "pdf",  # pdf, json, html
    db: AsyncSession = Depends(get_async_db)
):
    """导出旅行计划"""
    service = TravelPlanService(db)
    plan = await service.get_travel_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="旅行计划不存在")
    
    # 这里应该调用导出服务
    # export_service = ExportService()
    # return await export_service.export_plan(plan, format)
    
    return {"message": f"导出功能开发中，格式: {format}"}
