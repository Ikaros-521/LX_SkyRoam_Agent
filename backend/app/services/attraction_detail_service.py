"""
景点详细信息服务
用于匹配和合并手动维护的景点详细信息到收集的景点数据中
"""

from typing import List, Dict, Any, Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from app.models.attraction_detail import AttractionDetail


class AttractionDetailService:
    """景点详细信息服务"""
    
    @staticmethod
    async def find_matching_detail(
        db: AsyncSession,
        attraction_name: str,
        destination: str,
        city: Optional[str] = None,
        coordinates: Optional[Dict[str, float]] = None
    ) -> Optional[AttractionDetail]:
        """
        查找匹配的景点详细信息
        
        Args:
            db: 数据库会话
            attraction_name: 景点名称
            destination: 目的地
            city: 城市（可选）
            coordinates: 坐标信息 {"lat": x, "lng": y}（可选）
            
        Returns:
            匹配的 AttractionDetail 对象，如果未找到返回 None
        """
        try:
            # 1. 精确匹配：名称和目的地完全一致
            query = select(AttractionDetail).where(
                and_(
                    func.lower(AttractionDetail.name) == attraction_name.lower().strip(),
                    AttractionDetail.destination == destination
                )
            ).order_by(AttractionDetail.match_priority.desc())
            
            result = await db.execute(query)
            detail = result.scalar_one_or_none()
            
            if detail:
                logger.debug(f"精确匹配到景点详情: {attraction_name} in {destination}")
                return detail
            
            # 2. 模糊匹配：名称包含关键词，且目的地匹配
            if city:
                query = select(AttractionDetail).where(
                    and_(
                        AttractionDetail.name.contains(attraction_name),
                        or_(
                            AttractionDetail.destination == destination,
                            AttractionDetail.city == city
                        )
                    )
                ).order_by(AttractionDetail.match_priority.desc())
                
                result = await db.execute(query)
                detail = result.scalar_one_or_none()
                
                if detail:
                    logger.debug(f"模糊匹配到景点详情: {attraction_name} in {destination}/{city}")
                    return detail
            
            # 3. 坐标匹配（如果提供了坐标）
            if coordinates and coordinates.get("lat") and coordinates.get("lng"):
                lat = coordinates["lat"]
                lng = coordinates["lng"]
                
                # 查找距离在1公里内的景点（约0.01度）
                threshold = 0.01
                query = select(AttractionDetail).where(
                    and_(
                        AttractionDetail.latitude.isnot(None),
                        AttractionDetail.longitude.isnot(None),
                        AttractionDetail.latitude.between(lat - threshold, lat + threshold),
                        AttractionDetail.longitude.between(lng - threshold, lng + threshold)
                    )
                ).order_by(AttractionDetail.match_priority.desc())
                
                result = await db.execute(query)
                detail = result.scalar_one_or_none()
                
                if detail:
                    logger.debug(f"坐标匹配到景点详情: {attraction_name} near ({lat}, {lng})")
                    return detail
            
            logger.debug(f"未找到匹配的景点详情: {attraction_name} in {destination}")
            return None
            
        except Exception as e:
            logger.warning(f"查找景点详情时出错: {e}")
            return None
    
    @staticmethod
    def merge_detail_into_attraction(
        attraction: Dict[str, Any],
        detail: AttractionDetail
    ) -> Dict[str, Any]:
        """
        将详细信息合并到景点数据中
        
        Args:
            attraction: 原始景点数据字典
            detail: 景点详细信息对象
            
        Returns:
            合并后的景点数据字典
        """
        try:
            # 合并联系方式
            if detail.phone:
                attraction["phone"] = detail.phone
            if detail.website:
                attraction["website"] = detail.website
            if detail.email:
                attraction["email"] = detail.email
            if detail.wechat:
                attraction["wechat"] = detail.wechat
            
            # 合并价格信息（优先级：详细信息 > 原始数据）
            if detail.ticket_price is not None:
                attraction["ticket_price"] = detail.ticket_price
                attraction["price"] = detail.ticket_price  # 兼容字段
                
                # 添加不同票种价格
                if detail.ticket_price_child is not None:
                    attraction["ticket_price_child"] = detail.ticket_price_child
                if detail.ticket_price_student is not None:
                    attraction["ticket_price_student"] = detail.ticket_price_student
                
                # 添加价格备注（用于展示价格说明）
                if detail.price_note:
                    attraction["price_note"] = detail.price_note
                
                attraction["currency"] = detail.currency
            
            # 合并营业时间（详细信息优先）
            if detail.opening_hours:
                attraction["opening_hours"] = detail.opening_hours
            elif detail.opening_hours_text:
                # 如果没有JSON格式的营业时间，使用文本格式
                attraction["opening_hours"] = detail.opening_hours_text
                attraction["opening_hours_text"] = detail.opening_hours_text
            
            # 合并地址和坐标（详细信息优先，但保留原始数据作为备选）
            if detail.address:
                attraction["address"] = detail.address
            if detail.latitude and detail.longitude:
                if "coordinates" not in attraction or not attraction["coordinates"]:
                    attraction["coordinates"] = {
                        "lat": detail.latitude,
                        "lng": detail.longitude
                    }
            
            # 合并额外信息
            if detail.extra_info:
                # 将额外信息合并到景点数据中
                for key, value in detail.extra_info.items():
                    if key not in attraction or not attraction[key]:
                        attraction[key] = value
            
            # 添加数据来源标记
            attraction["detail_source"] = "manual"
            attraction["detail_verified"] = detail.verified
            attraction["detail_id"] = detail.id
            
            logger.debug(f"成功合并景点详情到: {attraction.get('name')}")
            return attraction
            
        except Exception as e:
            logger.warning(f"合并景点详情时出错: {e}")
            return attraction
    
    @staticmethod
    async def enrich_attractions_with_details(
        db: AsyncSession,
        attractions: List[Dict[str, Any]],
        destination: str,
        city: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        批量为景点数据补充详细信息
        
        Args:
            db: 数据库会话
            attractions: 景点数据列表
            destination: 目的地
            city: 城市（可选）
            
        Returns:
            补充了详细信息的景点数据列表
        """
        enriched_attractions = []
        
        for attraction in attractions:
            attraction_name = attraction.get("name", "")
            coordinates = attraction.get("coordinates")
            
            # 查找匹配的详细信息
            detail = await AttractionDetailService.find_matching_detail(
                db=db,
                attraction_name=attraction_name,
                destination=destination,
                city=city,
                coordinates=coordinates
            )
            
            # 如果找到详细信息，合并到景点数据中
            if detail:
                enriched_attraction = AttractionDetailService.merge_detail_into_attraction(
                    attraction.copy(),
                    detail
                )
                enriched_attractions.append(enriched_attraction)
            else:
                # 未找到匹配的详细信息，保留原始数据
                enriched_attractions.append(attraction)
        
        matched_count = len([a for a in enriched_attractions if a.get("detail_id")])
        logger.info(f"为 {matched_count}/{len(attractions)} 个景点补充了详细信息")
        
        return enriched_attractions

