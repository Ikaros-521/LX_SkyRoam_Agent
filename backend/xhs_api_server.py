#!/usr/bin/env python3
"""
小红书 API 服务器
独立的FastAPI服务，提供小红书爬虫功能
避免主程序的异步事件循环问题
"""

import asyncio
import sys
import os
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, Set
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from loguru import logger
from dotenv import load_dotenv
from asyncio import Queue, QueueEmpty

# 必须在所有其他导入之前设置事件循环策略 - 使用ProactorEventLoop解决Playwright问题
if sys.platform == "win32":
    # 尝试使用ProactorEventLoop，这对Playwright更友好
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except AttributeError:
        # 如果不支持ProactorEventLoop，回退到SelectorEventLoop
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 添加项目路径
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

# 加载环境变量
load_dotenv()

# 导入小红书相关模块
from app.platforms.xhs.playwright_crawler import PlaywrightXHSCrawler
from app.platforms.xhs.real_crawler import XiaoHongShuRealCrawler, XiaoHongShuLoginCrawler
from app.services.enhanced_cookie_manager import enhanced_cookie_manager

# 请求模型
class LoginRequest(BaseModel):
    """登录请求模型"""
    timeout: Optional[int] = 300

class SearchRequest(BaseModel):
    """搜索请求模型"""
    keyword: str
    limit: Optional[int] = 10
    sort_type: Optional[str] = "general"

class CookieStatusResponse(BaseModel):
    """Cookie状态响应模型"""
    primary_exists: bool
    backup_exists: bool
    session_exists: bool
    cookie_count: int
    save_time: Optional[str]
    remaining_days: Optional[int]
    is_valid: bool

class XHSCrawlerPool:
    """简单的爬虫实例池，用于支撑并发搜索请求"""

    def __init__(self, max_crawlers: int = 2):
        self.max_crawlers = max(1, max_crawlers)
        self.available: Queue = Queue()
        self.create_lock = asyncio.Lock()
        self.all_crawlers: Set[XiaoHongShuRealCrawler] = set()
        self.in_use: set[XiaoHongShuRealCrawler] = set()

    async def acquire(self) -> XiaoHongShuRealCrawler:
        """获取可用的爬虫实例，没有可用实例时按需创建或等待"""
        try:
            crawler = self.available.get_nowait()
            logger.debug("从池中复用爬虫实例")
        except QueueEmpty:
            crawler = await self._create_or_wait()

        self.in_use.add(crawler)
        return crawler

    async def _create_or_wait(self) -> XiaoHongShuRealCrawler:
        async with self.create_lock:
            if len(self.all_crawlers) < self.max_crawlers:
                logger.info("创建新的小红书爬虫实例以支撑并发请求")
                crawler = XiaoHongShuRealCrawler()
                await crawler.start()
                self.all_crawlers.add(crawler)
                return crawler

        logger.debug("爬虫池已满，等待空闲实例")
        crawler = await self.available.get()
        return crawler

    async def release(self, crawler: Optional[XiaoHongShuRealCrawler], recycle: bool = True):
        if crawler is None:
            return

        self.in_use.discard(crawler)

        if not recycle:
            await self._dispose_crawler(crawler)
            return

        if not crawler.is_started:
            try:
                await crawler.start()
            except Exception as e:
                logger.error(f"重启爬虫实例失败，执行销毁: {e}")
                await self._dispose_crawler(crawler)
                return

        await self.available.put(crawler)

    async def ensure_min_crawlers(self, count: int = 1):
        target = min(max(0, count), self.max_crawlers)
        async with self.create_lock:
            while len(self.all_crawlers) < target:
                crawler = XiaoHongShuRealCrawler()
                await crawler.start()
                self.all_crawlers.add(crawler)
                await self.available.put(crawler)
                logger.info("预热小红书爬虫实例")

    async def shutdown(self):
        logger.info("正在关闭所有小红书爬虫实例")
        # 先等待池中实例关闭
        while not self.available.empty():
            try:
                crawler = self.available.get_nowait()
            except QueueEmpty:
                break
            await crawler.close()
            self.all_crawlers.discard(crawler)

        # 再关闭仍在使用中的实例
        for crawler in list(self.in_use):
            try:
                await crawler.close()
            finally:
                self.in_use.discard(crawler)
                self.all_crawlers.discard(crawler)

    async def _dispose_crawler(self, crawler: XiaoHongShuRealCrawler):
        try:
            await crawler.close()
        finally:
            self.all_crawlers.discard(crawler)


class XHSAPIServer:
    """小红书API服务器"""
    
    def __init__(self):
        self.app = FastAPI(
            title="小红书API服务",
            description="独立的小红书爬虫API服务",
            version="1.0.0"
        )
        max_crawlers = int(os.getenv("XHS_MAX_CONCURRENT_CRAWLERS", "2"))
        self.crawler_pool = XHSCrawlerPool(max_crawlers=max_crawlers)
        self.login_crawler: Optional[XiaoHongShuLoginCrawler] = None
        self.setup_middleware()
        self.setup_routes()
    
    def setup_middleware(self):
        """设置中间件"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_routes(self):
        """设置路由"""
        
        @self.app.get("/health")
        async def health_check():
            """健康检查"""
            return {
                "status": "ok",
                "service": "xhs-api-server",
                "version": "1.0.0"
            }
        
        @self.app.get("/cookie/status", response_model=CookieStatusResponse)
        async def get_cookie_status():
            """获取Cookie状态"""
            try:
                status = enhanced_cookie_manager.get_cookie_status()
                return CookieStatusResponse(
                    primary_exists=status.get('primary_exists', False),
                    backup_exists=status.get('backup_exists', False),
                    session_exists=status.get('session_exists', False),
                    cookie_count=status.get('cookie_count', 0),
                    save_time=status.get('save_time'),
                    remaining_days=status.get('remaining_days'),
                    is_valid=status.get('is_valid', False)
                )
            except Exception as e:
                logger.error(f"获取Cookie状态失败: {e}")
                raise HTTPException(status_code=500, detail=f"获取Cookie状态失败: {str(e)}")
        
        @self.app.post("/login")
        async def interactive_login(request: LoginRequest, background_tasks: BackgroundTasks):
            """交互式登录"""
            try:
                if self.login_crawler is None:
                    self.login_crawler = XiaoHongShuLoginCrawler()
                
                # 在后台任务中执行登录
                background_tasks.add_task(self._perform_login, request.timeout)
                
                return {
                    "status": "started",
                    "message": "登录流程已启动，请在浏览器中完成登录",
                    "timeout": request.timeout
                }
            except Exception as e:
                logger.error(f"启动登录失败: {e}")
                raise HTTPException(status_code=500, detail=f"启动登录失败: {str(e)}")
        
        @self.app.post("/search")
        async def search_notes(request: SearchRequest):
            """搜索小红书笔记"""
            try:
                crawler = await self.crawler_pool.acquire()
                try:
                    # 检查/刷新登录状态
                    if not await crawler.ensure_logged_in():
                        raise HTTPException(status_code=401, detail="未登录或登录已过期，请先完成登录")
                    
                    max_notes = request.limit or 10
                    if max_notes <= 0:
                        max_notes = 1

                    # 执行搜索
                    results = await crawler.search(
                        keyword=request.keyword,
                        max_notes=max_notes
                    )
                finally:
                    await self.crawler_pool.release(crawler)
                
                return {
                    "status": "success",
                    "keyword": request.keyword,
                    "count": len(results),
                    "results": results
                }
            except Exception as e:
                error_msg = str(e)
                error_trace = traceback.format_exc()
                logger.error(f"搜索失败: {error_msg}")
                logger.error(f"错误堆栈: {error_trace}")
            raise HTTPException(status_code=500, detail=f"搜索失败: {error_msg}")

        def _xhs_is_allowed_host(url: str) -> bool:
            try:
                from urllib.parse import urlparse as _urlparse
                parsed = _urlparse(url)
                if parsed.scheme not in ("http", "https"):
                    return False
                host = (parsed.hostname or "").lower()
                return host.endswith(".xhscdn.com") or host.endswith(".xiaohongshu.com")
            except Exception:
                return False

        def _xhs_load_cookies_list() -> list:
            try:
                from pathlib import Path as _Path
                import json as _json
                cookies_dir = _Path(__file__).parent / "data" / "cookies"
                candidates = [
                    cookies_dir / "xhs_cookies_primary.json",
                    cookies_dir / "xhs_cookies_backup.json",
                    cookies_dir / "xhs_cookies.json",
                ]
                cookie_file = next((p for p in candidates if p.exists()), None)
                if not cookie_file:
                    return []
                with open(cookie_file, "r", encoding="utf-8") as f:
                    data = _json.load(f)
                cookies = data.get("cookies", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                return cookies
            except Exception:
                return []

        @self.app.get("/proxy/image")
        async def proxy_image(url: str, referer: str = "https://www.xiaohongshu.com/explore"):
            if not _xhs_is_allowed_host(url):
                raise HTTPException(status_code=400, detail="不支持的图片来源")
            from urllib.parse import urlparse as _urlparse
            parsed = _urlparse(url)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                "Referer": referer,
                "Origin": "https://www.xiaohongshu.com",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Host": parsed.hostname or "",
                "Sec-Fetch-Site": "cross-site",
                "Sec-Fetch-Mode": "no-cors",
                "Sec-Fetch-Dest": "image",
                "sec-ch-ua": '"Chromium";v="120", "Not?A_Brand";v="99", "Google Chrome";v="120"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "Cache-Control": "no-cache",
            }
            cookies = _xhs_load_cookies_list()
            cookie_header = "; ".join([f"{c.get('name')}={c.get('value')}" for c in cookies if c.get('name') and c.get('value')])
            if cookie_header:
                headers["Cookie"] = cookie_header
            use_http2 = False
            try:
                import h2  # type: ignore
                use_http2 = True
            except Exception:
                use_http2 = False
            import httpx as _httpx
            async with _httpx.AsyncClient(timeout=20.0, follow_redirects=True, http2=use_http2) as client:
                try:
                    resp = await client.get(url, headers=headers)
                except Exception:
                    try:
                        async with _httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=False) as insecure_client:
                            insecure_resp = await insecure_client.get(url, headers=headers)
                            if insecure_resp.status_code == 200:
                                from fastapi.responses import StreamingResponse as _SR
                                ct = insecure_resp.headers.get("content-type", "image/jpeg")
                                return _SR(insecure_resp.aiter_bytes(), media_type=ct, headers={"Cache-Control": "public, max-age=86400"})
                    except Exception:
                        pass
                    raise HTTPException(status_code=502, detail="源站请求失败")
            if resp.status_code != 200:
                host = parsed.hostname or ""
                fallback_hosts = []
                if host.startswith("sns-webpic-") and host.endswith(".xhscdn.com"):
                    region = host.split("sns-webpic-")[-1].replace(".xhscdn.com", "")
                    fallback_hosts.append(f"sns-img-{region}.xhscdn.com")
                for region in ["qc", "hw", "bd"]:
                    h = f"sns-img-{region}.xhscdn.com"
                    if h not in fallback_hosts:
                        fallback_hosts.append(h)
                for fh in fallback_hosts:
                    alt = url.replace(host, fh)
                    try:
                        alt_headers = dict(headers)
                        alt_headers["Host"] = fh
                        alt_resp = await client.get(alt, headers=alt_headers)
                        if alt_resp.status_code == 200:
                            from fastapi.responses import StreamingResponse as _SR
                            content_type = alt_resp.headers.get("content-type", "image/jpeg")
                            return _SR(alt_resp.aiter_bytes(), media_type=content_type, headers={"Cache-Control": "public, max-age=86400"})
                    except Exception:
                        continue
                raise HTTPException(status_code=resp.status_code, detail="源站返回非200")
            content_type = resp.headers.get("content-type", "image/jpeg")
            if not content_type.startswith("image/"):
                raise HTTPException(status码=400, detail="非图片内容")
            from fastapi.responses import StreamingResponse as _SR
            return _SR(resp.aiter_bytes(), media_type=content_type, headers={"Cache-Control": "public, max-age=86400"})

        @self.app.get("/proxy/image_browser")
        async def proxy_image_browser(url: str, referer: str = "https://www.xiaohongshu.com/explore"):
            if not _xhs_is_allowed_host(url):
                raise HTTPException(status_code=400, detail="不支持的图片来源")
            from urllib.parse import urlparse as _urlparse
            parsed = _urlparse(url)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                "Referer": referer,
                "Origin": "https://www.xiaohongshu.com",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Host": parsed.hostname or "",
                "Sec-Fetch-Site": "cross-site",
                "Sec-Fetch-Mode": "no-cors",
                "Sec-Fetch-Dest": "image",
                "sec-ch-ua": '"Chromium";v="120", "Not?A_Brand";v="99", "Google Chrome";v="120"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "Cache-Control": "no-cache",
            }
            cookies_list = _xhs_load_cookies_list()
            try:
                from playwright.async_api import async_playwright as _apw
                async with _apw() as pw:
                    req_ctx = await pw.request.new_context(
                        user_agent=headers.get("User-Agent", ""),
                        extra_http_headers=headers,
                        storage_state={"cookies": cookies_list} if cookies_list else None,
                    )
                    pw_resp = await req_ctx.get(url)
                    body = await pw_resp.body() if pw_resp.ok else b""
                    await req_ctx.dispose()
                    if pw_resp.ok and body:
                        from fastapi.responses import StreamingResponse as _SR
                        ct = pw_resp.headers.get("content-type", "image/jpeg")
                        import io as _io
                        return _SR(_io.BytesIO(body), media_type=ct, headers={"Cache-Control": "public, max-age=86400"})
                    else:
                        raise HTTPException(status_code=pw_resp.status, detail="源站返回非200")
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=502, detail="源站请求失败")
        
        @self.app.post("/crawler/start")
        async def start_crawler():
            """启动爬虫"""
            try:
                await self.crawler_pool.ensure_min_crawlers(count=1)
                
                return {
                    "status": "success",
                    "message": "爬虫池已预热",
                    "max_instances": self.crawler_pool.max_crawlers
                }
            except Exception as e:
                logger.error(f"启动爬虫失败: {e}")
                raise HTTPException(status_code=500, detail=f"启动爬虫失败: {str(e)}")
        
        @self.app.post("/crawler/stop")
        async def stop_crawler():
            """停止爬虫"""
            try:
                await self.crawler_pool.shutdown()

                if self.login_crawler:
                    await self.login_crawler.close()
                    self.login_crawler = None
                
                return {
                    "status": "success",
                    "message": "爬虫已停止"
                }
            except Exception as e:
                error_msg = str(e)
                error_trace = traceback.format_exc()
                logger.error(f"搜索失败: {error_msg}")
                logger.error(f"错误堆栈: {error_trace}")
                raise HTTPException(status_code=500, detail=f"搜索失败: {error_msg}")
    
    async def _perform_login(self, timeout: int):
        """执行登录流程"""
        try:
            if self.login_crawler is None:
                self.login_crawler = XiaoHongShuLoginCrawler()
            
            # XiaoHongShuLoginCrawler没有start方法，interactive_login会自动启动内部的crawler
            success = await self.login_crawler.interactive_login()
            
            if success:
                logger.info("✅ 登录成功")
            else:
                logger.warning("❌ 登录失败或超时")
                
        except Exception as e:
            logger.error(f"登录过程中出错: {e}")
        finally:
            if self.login_crawler:
                await self.login_crawler.close()

# 创建服务器实例
server = XHSAPIServer()
app = server.app

if __name__ == "__main__":
    # 启动服务器
    uvicorn.run(
        "xhs_api_server:app",
        host="0.0.0.0",
        port=8002,
        reload=False,  # 禁用重载以避免事件循环问题
        log_level="info"
    )
