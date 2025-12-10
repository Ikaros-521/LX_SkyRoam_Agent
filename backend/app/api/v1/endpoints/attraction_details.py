"""
景点详细信息管理API端点（超管权限）
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, delete
from typing import List, Optional
from loguru import logger

from app.core.database import get_async_db
from app.models.attraction_detail import AttractionDetail
from app.core.security import get_current_user, is_admin
from app.models.user import User

router = APIRouter()


@router.get("/")
async def list_attraction_details(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    destination: Optional[str] = None,
    city: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取景点详细信息列表（仅超管）"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="仅管理员可访问")
    
    query = select(AttractionDetail)
    
    # 筛选条件
    conditions = []
    if destination:
        conditions.append(AttractionDetail.destination == destination)
    if city:
        conditions.append(AttractionDetail.city == city)
    if search:
        search_pattern = f"%{search}%"
        conditions.append(
            or_(
                AttractionDetail.name.like(search_pattern),
                AttractionDetail.address.like(search_pattern),
                AttractionDetail.phone.like(search_pattern)
            )
        )
    
    if conditions:
        query = query.where(*conditions)
    
    # 排序：按优先级和创建时间
    query = query.order_by(
        AttractionDetail.match_priority.desc(),
        AttractionDetail.created_at.desc()
    )
    
    # 分页
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    details = result.scalars().all()
    
    # 获取总数
    count_query = select(func.count(AttractionDetail.id))
    if conditions:
        count_query = count_query.where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    return {
        "items": [detail.to_dict() for detail in details],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{detail_id}")
async def get_attraction_detail(
    detail_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个景点详细信息（仅超管）"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="仅管理员可访问")
    
    result = await db.execute(
        select(AttractionDetail).where(AttractionDetail.id == detail_id)
    )
    detail = result.scalar_one_or_none()
    
    if not detail:
        raise HTTPException(status_code=404, detail="景点详细信息不存在")
    
    return detail.to_dict()


@router.post("/")
async def create_attraction_detail(
    detail_data: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """创建景点详细信息（仅超管）"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="仅管理员可访问")
    
    try:
        # 创建新记录
        new_detail = AttractionDetail(
            name=detail_data.get("name"),
            destination=detail_data.get("destination"),
            city=detail_data.get("city"),
            phone=detail_data.get("phone"),
            website=detail_data.get("website"),
            email=detail_data.get("email"),
            wechat=detail_data.get("wechat"),
            ticket_price=detail_data.get("ticket_price"),
            ticket_price_child=detail_data.get("ticket_price_child"),
            ticket_price_student=detail_data.get("ticket_price_student"),
            currency=detail_data.get("currency", "CNY"),
            price_note=detail_data.get("price_note"),
            opening_hours=detail_data.get("opening_hours"),
            opening_hours_text=detail_data.get("opening_hours_text"),
            address=detail_data.get("address"),
            latitude=detail_data.get("latitude"),
            longitude=detail_data.get("longitude"),
            image_url=detail_data.get("image_url"),
            extra_info=detail_data.get("extra_info"),
            match_priority=detail_data.get("match_priority", 100),
            source=detail_data.get("source", "manual"),
            verified=detail_data.get("verified", "pending")
        )
        
        db.add(new_detail)
        await db.commit()
        await db.refresh(new_detail)
        
        logger.info(f"管理员 {current_user.username} 创建了景点详细信息: {new_detail.name}")
        return new_detail.to_dict()
        
    except Exception as e:
        await db.rollback()
        logger.error(f"创建景点详细信息失败: {e}")
        raise HTTPException(status_code=400, detail=f"创建失败: {str(e)}")


@router.put("/{detail_id}")
async def update_attraction_detail(
    detail_id: int,
    detail_data: dict,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """更新景点详细信息（仅超管）"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="仅管理员可访问")
    
    result = await db.execute(
        select(AttractionDetail).where(AttractionDetail.id == detail_id)
    )
    detail = result.scalar_one_or_none()
    
    if not detail:
        raise HTTPException(status_code=404, detail="景点详细信息不存在")
    
    try:
        # 更新字段
        if "name" in detail_data:
            detail.name = detail_data["name"]
        if "destination" in detail_data:
            detail.destination = detail_data["destination"]
        if "city" in detail_data:
            detail.city = detail_data["city"]
        if "phone" in detail_data:
            detail.phone = detail_data["phone"]
        if "website" in detail_data:
            detail.website = detail_data["website"]
        if "email" in detail_data:
            detail.email = detail_data["email"]
        if "wechat" in detail_data:
            detail.wechat = detail_data["wechat"]
        if "ticket_price" in detail_data:
            detail.ticket_price = detail_data["ticket_price"]
        if "ticket_price_child" in detail_data:
            detail.ticket_price_child = detail_data["ticket_price_child"]
        if "ticket_price_student" in detail_data:
            detail.ticket_price_student = detail_data["ticket_price_student"]
        if "currency" in detail_data:
            detail.currency = detail_data["currency"]
        if "price_note" in detail_data:
            detail.price_note = detail_data["price_note"]
        if "opening_hours" in detail_data:
            detail.opening_hours = detail_data["opening_hours"]
        if "opening_hours_text" in detail_data:
            detail.opening_hours_text = detail_data["opening_hours_text"]
        if "address" in detail_data:
            detail.address = detail_data["address"]
        if "latitude" in detail_data:
            detail.latitude = detail_data["latitude"]
        if "longitude" in detail_data:
            detail.longitude = detail_data["longitude"]
        if "image_url" in detail_data:
            detail.image_url = detail_data["image_url"]
        if "extra_info" in detail_data:
            detail.extra_info = detail_data["extra_info"]
        if "match_priority" in detail_data:
            detail.match_priority = detail_data["match_priority"]
        if "verified" in detail_data:
            detail.verified = detail_data["verified"]
        
        await db.commit()
        await db.refresh(detail)
        
        logger.info(f"管理员 {current_user.username} 更新了景点详细信息: {detail.name}")
        return detail.to_dict()
        
    except Exception as e:
        await db.rollback()
        logger.error(f"更新景点详细信息失败: {e}")
        raise HTTPException(status_code=400, detail=f"更新失败: {str(e)}")


@router.delete("/{detail_id}")
async def delete_attraction_detail(
    detail_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """删除景点详细信息（仅超管）"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="仅管理员可访问")
    
    result = await db.execute(
        select(AttractionDetail).where(AttractionDetail.id == detail_id)
    )
    detail = result.scalar_one_or_none()
    
    if not detail:
        raise HTTPException(status_code=404, detail="景点详细信息不存在")
    
    try:
        detail_name = detail.name
        await db.execute(delete(AttractionDetail).where(AttractionDetail.id == detail_id))
        await db.commit()
        
        logger.info(f"管理员 {current_user.username} 删除了景点详细信息: {detail_name}")
        return {"message": "删除成功", "id": detail_id}
        
    except Exception as e:
        await db.rollback()
        logger.error(f"删除景点详细信息失败: {e}")
        raise HTTPException(status_code=400, detail=f"删除失败: {str(e)}")


@router.get("/destinations/list")
async def get_destinations_list(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有目的地列表（用于下拉选择）"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="仅管理员可访问")
    
    result = await db.execute(
        select(AttractionDetail.destination).distinct()
    )
    destinations = [row[0] for row in result.all() if row[0]]
    
    return sorted(destinations)


@router.get("/cities/list")
async def get_cities_list(
    destination: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """获取城市列表（用于下拉选择）"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="仅管理员可访问")
    
    query = select(AttractionDetail.city).distinct()
    if destination:
        query = query.where(AttractionDetail.destination == destination)
    
    result = await db.execute(query)
    cities = [row[0] for row in result.all() if row[0]]
    
    return sorted(cities)

