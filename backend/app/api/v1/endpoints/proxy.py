from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
import httpx
from app.core.config import settings
from urllib.parse import urlparse
from pathlib import Path
import json
from loguru import logger

router = APIRouter()

_ALLOWED_HOSTS = {
    "sns-img-hw.xhscdn.com",
    "sns-img-qc.xhscdn.com",
    "sns-img-bd.xhscdn.com",
    "img.xiaohongshu.com",
    "ci.xiaohongshu.com",
    "pic.qyer.com",
}

def _is_allowed_host(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        host = (parsed.hostname or "").lower()
        if host in _ALLOWED_HOSTS:
            return True
        # 允许子域的通配
        return (
            host.endswith(".xhscdn.com")
            or host.endswith(".xiaohongshu.com")
            or host.endswith(".qyer.com")
        )
    except Exception:
        return False

def _build_cookie_header(url: str) -> str:
    try:
        cookies_dir = Path(__file__).parent.parent.parent.parent / "data" / "cookies"
        candidates = [
            cookies_dir / "xhs_cookies_primary.json",
            cookies_dir / "xhs_cookies_backup.json",
            cookies_dir / "xhs_cookies.json",
        ]
        cookie_file = next((p for p in candidates if p.exists()), None)
        if not cookie_file:
            return ""
        with open(cookie_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        cookies = data.get("cookies", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        if not cookies:
            return ""
        parts = []
        for c in cookies:
            name = c.get("name")
            value = c.get("value")
            if name and value:
                parts.append(f"{name}={value}")
        logger.info(f"[图片代理] 组装Cookie数量: {len(parts)} 来自: {cookie_file}")
        return "; ".join(parts)
    except Exception:
        return ""

@router.get("/image")
async def proxy_image(
    url: str = Query(..., description="图片源URL"),
    referer: str = Query("https://www.xiaohongshu.com/explore", description="来源页面，用于跨域验证")
):
    if not _is_allowed_host(url):
        raise HTTPException(status_code=400, detail="不支持的图片来源")

    parsed = urlparse(url)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": referer,
        "Origin": "https://www.xiaohongshu.com",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Host": parsed.hostname or "",
    }
    cookie_header = _build_cookie_header(url)
    if cookie_header:
        headers["Cookie"] = cookie_header

    logger.debug(f"[图片代理] 请求URL: {url}")
    logger.debug(f"[图片代理] 请求头: {{'User-Agent': headers['User-Agent'], 'Referer': headers['Referer'], 'Host': headers['Host'], 'Cookie': '***' if 'Cookie' in headers else '(none)'}}")

    # 如果是穷游图片，直接走源站，不经过小红书转发
    host = (parsed.hostname or "").lower()
    if host.endswith(".qyer.com") or host == "pic.qyer.com":
        qyer_referer = "https://place.qyer.com"
        qyer_headers = {
            "User-Agent": headers["User-Agent"],
            "Accept": headers["Accept"],
            "Referer": qyer_referer,
            "Origin": qyer_referer,
            "Accept-Language": headers["Accept-Language"],
            "Accept-Encoding": headers["Accept-Encoding"],
            "Connection": headers["Connection"],
            "Host": host,
        }

        async def _fetch_qyer(target_url: str):
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=False, http2=False) as client:
                return await client.get(target_url, headers=qyer_headers)

        try:
            resp = await _fetch_qyer(url)
        except httpx.ConnectError as e:
            # 有些环境对 https 443 连不通，尝试 http 80 回退
            logger.warning(f"[图片代理][qyer] https 连接失败，回退 http: {e!r}")
            if url.startswith("https://"):
                http_url = url.replace("https://", "http://", 1)
                try:
                    resp = await _fetch_qyer(http_url)
                except Exception as e2:
                    logger.error(f"[图片代理][qyer] http 回退也失败: {type(e2).__name__} {e2!r}")
                    raise HTTPException(status_code=502, detail=f"源站请求失败: {type(e2).__name__}: {e2}")
            else:
                raise HTTPException(status_code=502, detail=f"源站请求失败: {type(e).__name__}: {e}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[图片代理][qyer] 请求异常: {type(e).__name__} {e!r}")
            raise HTTPException(status_code=502, detail=f"源站请求失败: {type(e).__name__}: {e}")

        if resp.status_code != 200:
            body = (resp.text or "")[:200]
            logger.error(f"[图片代理][qyer] 非200响应 status={resp.status_code} body={body}")
            raise HTTPException(status_code=resp.status_code, detail="源站返回非200")
        ct = resp.headers.get("content-type", "image/jpeg")
        return StreamingResponse(resp.aiter_bytes(), media_type=ct, headers={"Cache-Control": "public, max-age=86400"})

    api_base = settings.XHS_API_BASE
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        try:
            r1 = await client.get(f"{api_base}/proxy/image", params={"url": url, "referer": referer})
            if r1.status_code == 200:
                ct = r1.headers.get("content-type", "image/jpeg")
                return StreamingResponse(r1.aiter_bytes(), media_type=ct, headers={"Cache-Control": "public, max-age=86400"})
        except Exception as e:
            logger.warning(f"[图片代理] 小红书服务(image)调用失败: {e}")
        try:
            r2 = await client.get(f"{api_base}/proxy/image_browser", params={"url": url, "referer": referer})
            if r2.status_code == 200:
                ct = r2.headers.get("content-type", "image/jpeg")
                return StreamingResponse(r2.aiter_bytes(), media_type=ct, headers={"Cache-Control": "public, max-age=86400"})
        except Exception as e:
            logger.warning(f"[图片代理] 小红书服务(image_browser)调用失败: {e}")

    use_http2 = False
    try:
        import h2  # type: ignore
        use_http2 = True
    except Exception:
        use_http2 = False

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, http2=use_http2) as client:
        try:
            resp = await client.get(url, headers=headers)
            logger.info(f"[图片代理] 源站响应: {resp.status_code} content-type={resp.headers.get('content-type')} length={resp.headers.get('content-length')}")
        except Exception as e:
            logger.error(f"[图片代理] 请求异常: {e}")
            raise HTTPException(status_code=502, detail=f"源站请求失败: {e}")

    if resp.status_code != 200:
        detail = resp.text[:200] if resp.text else "源站返回非200"
        logger.error(f"[图片代理] 非200响应: status={resp.status_code} body={detail}")
        # 尝试备用域名
        host = parsed.hostname or ""
        fallback_hosts = []
        if host.startswith("sns-webpic-") and host.endswith(".xhscdn.com"):
            # 同区域图片域
            region = host.split("sns-webpic-")[-1].replace(".xhscdn.com", "")
            fallback_hosts.append(f"sns-img-{region}.xhscdn.com")
        # 其他区域的通用备选
        for region in ["qc", "hw", "bd"]:
            h = f"sns-img-{region}.xhscdn.com"
            if h not in fallback_hosts:
                fallback_hosts.append(h)
        for fh in fallback_hosts:
            alt = url.replace(host, fh)
            logger.info(f"[图片代理] 尝试备用域名: {alt}")
            try:
                alt_headers = dict(headers)
                alt_headers["Host"] = fh
                alt_resp = await client.get(alt, headers=alt_headers)
                logger.info(f"[图片代理] 备用域响应: {alt_resp.status_code}")
                if alt_resp.status_code == 200:
                    content_type = alt_resp.headers.get("content-type", "image/jpeg")
                    return StreamingResponse(alt_resp.aiter_bytes(), media_type=content_type, headers={"Cache-Control": "public, max-age=86400"})
            except Exception as e:
                logger.warning(f"[图片代理] 备用域请求失败: {e}")
        api_base = settings.XHS_API_BASE
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as c2:
            try:
                r3 = await c2.get(f"{api_base}/proxy/image", params={"url": url, "referer": referer})
                if r3.status_code == 200:
                    ct = r3.headers.get("content-type", "image/jpeg")
                    return StreamingResponse(r3.aiter_bytes(), media_type=ct, headers={"Cache-Control": "public, max-age=86400"})
            except Exception as e:
                logger.warning(f"[图片代理] 小红书服务(image)非200回退失败: {e}")
            try:
                r4 = await c2.get(f"{api_base}/proxy/image_browser", params={"url": url, "referer": referer})
                if r4.status_code == 200:
                    ct = r4.headers.get("content-type", "image/jpeg")
                    return StreamingResponse(r4.aiter_bytes(), media_type=ct, headers={"Cache-Control": "public, max-age=86400"})
            except Exception as e:
                logger.warning(f"[图片代理] 小红书服务(image_browser)非200回退失败: {e}")
        raise HTTPException(status_code=resp.status_code, detail="源站返回非200")

    content_type = resp.headers.get("content-type", "image/jpeg")
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="非图片内容")

    return StreamingResponse(resp.aiter_bytes(), media_type=content_type, headers={"Cache-Control": "public, max-age=86400"})

