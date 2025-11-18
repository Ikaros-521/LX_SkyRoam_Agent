"""
小红书API客户端
通过HTTP接口调用独立的小红书API服务
"""

import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from loguru import logger
from app.core.config import settings


class XHSAPIClient:
    """小红书API客户端"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.XHS_API_BASE
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取HTTP会话"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """关闭客户端"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"健康检查失败: {response.status}")
        except Exception as e:
            logger.error(f"小红书API服务健康检查失败: {e}")
            raise
    
    async def get_cookie_status(self) -> Dict[str, Any]:
        """获取Cookie状态"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/cookie/status") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"获取Cookie状态失败: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"获取Cookie状态失败: {e}")
            raise
    
    async def start_login(self, timeout: int = 300) -> Dict[str, Any]:
        """启动登录流程"""
        try:
            session = await self._get_session()
            data = {"timeout": timeout}
            async with session.post(f"{self.base_url}/login", json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"启动登录失败: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"启动登录失败: {e}")
            raise
    
    async def search_notes(self, keyword: str, limit: int = 10, sort_type: str = "general") -> Dict[str, Any]:
        """搜索小红书笔记"""
        try:
            session = await self._get_session()
            data = {
                "keyword": keyword,
                "limit": limit,
                "sort_type": sort_type
            }
            async with session.post(f"{self.base_url}/search", json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"搜索失败: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"搜索笔记失败: {e}")
            raise
    
    async def start_crawler(self) -> Dict[str, Any]:
        """启动爬虫"""
        try:
            session = await self._get_session()
            async with session.post(f"{self.base_url}/crawler/start") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"启动爬虫失败: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"启动爬虫失败: {e}")
            raise
    
    async def stop_crawler(self) -> Dict[str, Any]:
        """停止爬虫"""
        try:
            session = await self._get_session()
            async with session.post(f"{self.base_url}/crawler/stop") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"停止爬虫失败: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"停止爬虫失败: {e}")
            raise


# 全局客户端实例
xhs_api_client = XHSAPIClient(settings.XHS_API_BASE)