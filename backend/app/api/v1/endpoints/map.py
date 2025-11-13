"""
地图API端点
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
import httpx
from typing import Optional
from loguru import logger
from app.core.config import settings

router = APIRouter()

AMAP_API_KEY = settings.AMAP_API_KEY
BAIDU_API_KEY = settings.BAIDU_MAPS_API_KEY


@router.get("/static")
async def get_static_map(
    provider: str = Query(..., description="地图提供商: amap 或 baidu"),
    longitude: float = Query(..., description="经度"),
    latitude: float = Query(..., description="纬度"),
    zoom: int = Query(13, description="缩放级别"),
    width: int = Query(400, description="图片宽度"),
    height: int = Query(300, description="图片高度"),
    title: Optional[str] = Query(None, description="标记标题")
):
    """
    获取静态地图图片（代理服务）
    """
    try:
        if provider == "amap":
            if not AMAP_API_KEY or AMAP_API_KEY == "your-amap-api-key-here":
                raise HTTPException(status_code=500, detail="高德地图API密钥未配置")
            
            # 构建高德静态地图URL - 使用正确的参数格式
            url = "https://restapi.amap.com/v3/staticmap"
            
            params = {
                "key": AMAP_API_KEY,
                "location": f"{longitude},{latitude}",
                "zoom": zoom,
                "size": f"{width}*{height}",
                "traffic": 0,
                "scale": 1
            }
            
            # 添加标记点，格式：经度,纬度
            if title:
                # 使用markers参数添加标记点
                params["markers"] = f"mid,,A:{longitude},{latitude}"
                # 使用labels参数添加标签，格式：内容,字体,字体颜色,背景颜色:经度,纬度
                params["labels"] = f"{title},1,0,16,0xFFFFFF,0x008000:{longitude},{latitude}"
            else:
                # 即使没有标题也添加一个简单的标记点
                params["markers"] = f"mid,,A:{longitude},{latitude}"
            
        elif provider == "baidu":
            if not BAIDU_API_KEY:
                raise HTTPException(status_code=500, detail="百度地图API密钥未配置")
            
            # 构建百度静态地图URL
            url = "https://api.map.baidu.com/staticimage/v2"
            params = {
                "ak": BAIDU_API_KEY,
                "center": f"{longitude},{latitude}",
                "zoom": zoom,
                "width": width,
                "height": height
            }
            
            if title:
                params["markers"] = f"{longitude},{latitude}"
                params["markerStyles"] = "m,A"
            
        else:
            raise HTTPException(status_code=400, detail="不支持的地图提供商")
        
        # 请求静态地图
        logger.info(f"请求地图API: {url}")
        logger.info(f"请求参数: {params}")
        
        async with httpx.AsyncClient(timeout=30.0, proxies=None) as client:
            response = await client.get(url, params=params)
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应头: {response.headers}")
            
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"地图API返回错误状态码 {response.status_code}: {error_text}")
                raise HTTPException(status_code=500, detail=f"地图API返回错误: {error_text}")
            
            response.raise_for_status()
            
            # 检查响应内容类型
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                # 如果不是图片，可能是错误响应
                error_text = response.text
                logger.error(f"地图API返回非图片内容: {error_text}")
                raise HTTPException(status_code=500, detail="地图服务返回错误")
            
            # 返回图片
            return Response(
                content=response.content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=3600",  # 缓存1小时
                    "Access-Control-Allow-Origin": "*"
                }
            )
            
    except httpx.HTTPError as e:
        logger.error(f"请求地图API失败: {str(e)}")
        raise HTTPException(status_code=500, detail="地图服务请求失败")
    except Exception as e:
        logger.error(f"获取静态地图失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取地图失败")


@router.get("/health")
async def map_health():
    """
    地图服务健康检查
    """
    return {
        "status": "ok",
        "amap_configured": bool(AMAP_API_KEY),
        "baidu_configured": bool(BAIDU_API_KEY),
        "input_tips_enabled": bool(settings.MAP_INPUT_TIPS_ENABLED),
        "map_provider": settings.MAP_PROVIDER
    }


@router.get("/tips")
async def input_tips(
    q: str = Query(..., min_length=1, description="输入关键字"),
    city: Optional[str] = Query(None, description="指定城市，提高准确性"),
    datatype: str = Query("all", description="返回数据类型: all|poi|bus|busline"),
    citylimit: bool = Query(False, description="是否限制在指定城市内"),
    provider: Optional[str] = Query(None, description="输入提示数据源: amap 或 osm")
):
    """
    输入提示代理，支持高德(amap)与 OpenStreetMap(osm)
    """
    if not settings.MAP_INPUT_TIPS_ENABLED:
        logger.info("输入提示功能已关闭，返回空结果")
        return {"options": []}
    source = (provider or settings.MAP_PROVIDER or 'amap').lower()

    try:
        if source == 'amap':
            if not AMAP_API_KEY or AMAP_API_KEY == "your-amap-api-key-here":
                raise HTTPException(status_code=500, detail="高德地图API密钥未配置")

            url = "https://restapi.amap.com/v3/assistant/inputtips"
            params = {
                "key": AMAP_API_KEY,
                "keywords": q,
                "datatype": datatype,
                "citylimit": 'true' if citylimit else 'false'
            }
            if city:
                params["city"] = city

            async with httpx.AsyncClient(timeout=20.0, proxies=None) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    raise HTTPException(status_code=500, detail=f"高德输入提示服务错误: {resp.text}")
                data = resp.json()
                if data.get("status") != "1":
                    raise HTTPException(status_code=500, detail=f"高德返回错误: {data.get('info')}")

                tips = data.get("tips", [])
                options = []
                for item in tips:
                    name = item.get("name") or ""
                    district = item.get("district") or ""
                    adcode = item.get("adcode") or ""
                    location = item.get("location") or ""
                    label = name if not district else f"{name}（{district}）"
                    options.append({
                        "value": name,
                        "label": label,
                        "district": district,
                        "adcode": adcode,
                        "location": location
                    })

                return {"options": options}

        elif source == 'osm':
            # OpenStreetMap Nominatim 输入提示（搜索）
            url = "https://nominatim.openstreetmap.org/search"
            # 将城市拼接到查询中以提高准确度（如果提供）
            query = f"{city} {q}" if city else q
            params = {
                "q": query,
                "format": "json",
                "limit": 10,
                "addressdetails": 1,
                "accept-language": "zh-CN"
            }

            headers = {
                "User-Agent": settings.SCRAPY_USER_AGENT or "LX-SkyRoam-Agent/1.0"
            }

            async with httpx.AsyncClient(timeout=20.0, headers=headers, proxies=None) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    raise HTTPException(status_code=500, detail=f"OSM 输入提示服务错误: {resp.text}")
                data = resp.json()
                items = data if isinstance(data, list) else []

                def pick_district(addr: dict) -> str:
                    return (
                        addr.get('city') or addr.get('town') or addr.get('village') or addr.get('county') or addr.get('state') or addr.get('country') or ''
                    )

                options = []
                for it in items:
                    display_name = it.get('display_name') or ''
                    name_main = display_name.split(',')[0].strip()
                    district = pick_district(it.get('address', {}))
                    lat = it.get('lat') or ''
                    lon = it.get('lon') or ''
                    location = f"{lon},{lat}" if lat and lon else ""
                    label = name_main if not district else f"{name_main}（{district}）"
                    options.append({
                        "value": name_main or display_name,
                        "label": label,
                        "district": district,
                        "adcode": "",
                        "location": location
                    })

                return {"options": options}

        else:
            if source == 'baidu':
                if not BAIDU_API_KEY:
                    raise HTTPException(status_code=500, detail="百度地图API密钥未配置")

                url = "https://api.map.baidu.com/place/v2/suggestion"
                params = {
                    "query": q,
                    "region": city or "全国",
                    "city_limit": 'true' if citylimit else 'false',
                    "output": "json",
                    "ak": BAIDU_API_KEY
                }

                async with httpx.AsyncClient(timeout=20.0, proxies=None) as client:
                    resp = await client.get(url, params=params)
                    if resp.status_code != 200:
                        raise HTTPException(status_code=500, detail=f"百度输入提示服务错误: {resp.text}")
                    data = resp.json()
                    results = data.get("result", []) if isinstance(data, dict) else []

                    def coord_to_str(loc: dict) -> str:
                        if not isinstance(loc, dict):
                            return ""
                        lat = loc.get("lat")
                        lng = loc.get("lng")
                        if lat is None or lng is None:
                            return ""
                        return f"{lng},{lat}"

                    options = []
                    for item in results:
                        name = item.get("name") or ""
                        district = item.get("city") or item.get("district") or item.get("province") or ""
                        uid = item.get("uid") or ""
                        location = coord_to_str(item.get("location", {}))
                        label = name if not district else f"{name}（{district}）"
                        options.append({
                            "value": name,
                            "label": label,
                            "district": district,
                            "adcode": uid,
                            "location": location
                        })

                    return {"options": options}
            raise HTTPException(status_code=400, detail="不支持的输入提示提供商")
    except httpx.HTTPError as e:
        logger.error(f"请求输入提示失败: {str(e)}")
        raise HTTPException(status_code=500, detail="地图服务请求失败")
