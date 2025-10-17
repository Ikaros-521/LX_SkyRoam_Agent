"""
数据收集API端点
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.tasks.data_collection_tasks import collect_destination_data_task
from loguru import logger

router = APIRouter()


class DataCollectionRequest(BaseModel):
    """数据收集请求模型"""
    origin: str
    destination: str
    departure_date: Optional[str] = None
    return_date: Optional[str] = None
    transportation_type: str = "mixed"


class DataCollectionResponse(BaseModel):
    """数据收集响应模型"""
    task_id: str
    status: str
    message: str


@router.post("/collect", response_model=DataCollectionResponse)
async def start_data_collection(request: DataCollectionRequest):
    """
    启动数据收集任务
    
    Args:
        request: 数据收集请求参数
        
    Returns:
        任务ID和状态信息
    """
    try:
        logger.info(f"收到数据收集请求: {request.origin} -> {request.destination}")
        
        # 验证日期格式
        if request.departure_date:
            try:
                datetime.strptime(request.departure_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail="出发日期格式错误，请使用YYYY-MM-DD格式"
                )
        
        if request.return_date:
            try:
                datetime.strptime(request.return_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail="返回日期格式错误，请使用YYYY-MM-DD格式"
                )
        
        # 验证交通方式
        valid_transportation_types = ["flight", "train", "mixed", "driving"]
        if request.transportation_type not in valid_transportation_types:
            raise HTTPException(
                status_code=400,
                detail=f"交通方式无效，支持的类型: {', '.join(valid_transportation_types)}"
            )
        
        # 启动Celery任务
        task = collect_destination_data_task.delay(
            origin=request.origin,
            destination=request.destination,
            departure_date=request.departure_date,
            return_date=request.return_date,
            transportation_type=request.transportation_type
        )
        
        logger.info(f"数据收集任务已启动，任务ID: {task.id}")
        
        return DataCollectionResponse(
            task_id=task.id,
            status="started",
            message=f"数据收集任务已启动，正在收集 {request.origin} 到 {request.destination} 的数据"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动数据收集任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动数据收集任务失败: {str(e)}")


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    获取数据收集任务状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务状态和结果
    """
    try:
        from celery.result import AsyncResult
        
        task_result = AsyncResult(task_id)
        
        if task_result.state == "PENDING":
            response = {
                "task_id": task_id,
                "status": "pending",
                "message": "任务正在等待执行"
            }
        elif task_result.state == "PROGRESS":
            response = {
                "task_id": task_id,
                "status": "progress",
                "message": "任务正在执行中",
                "current": task_result.info.get("current", 0),
                "total": task_result.info.get("total", 100)
            }
        elif task_result.state == "SUCCESS":
            response = {
                "task_id": task_id,
                "status": "success",
                "message": "任务执行成功",
                "result": task_result.result
            }
        else:
            # 任务失败
            response = {
                "task_id": task_id,
                "status": "failed",
                "message": f"任务执行失败: {str(task_result.info)}"
            }
        
        return response
        
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")


@router.delete("/cancel/{task_id}")
async def cancel_task(task_id: str):
    """
    取消数据收集任务
    
    Args:
        task_id: 任务ID
        
    Returns:
        取消结果
    """
    try:
        from celery.result import AsyncResult
        
        task_result = AsyncResult(task_id)
        task_result.revoke(terminate=True)
        
        logger.info(f"数据收集任务已取消，任务ID: {task_id}")
        
        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": "任务已取消"
        }
        
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")