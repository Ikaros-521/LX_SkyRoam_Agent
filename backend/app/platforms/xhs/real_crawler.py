"""
小红书真实数据爬虫 - 集成版
整合Playwright爬虫到现有系统架构
"""

import asyncio
from typing import Dict, List, Optional, Any
from loguru import logger

from .playwright_crawler import PlaywrightXHSCrawler
from .base.base_crawler import AbstractCrawler


class XiaoHongShuRealCrawler(AbstractCrawler):
    """小红书真实数据爬虫 - 继承抽象基类"""
    
    def __init__(self):
        self.playwright_crawler = PlaywrightXHSCrawler()
        self.is_started = False
        self.is_logged_in = False
    
    async def start(self):
        """启动爬虫"""
        try:
            await self.playwright_crawler.start()
            self.is_started = True
            # 同步登录状态
            self.is_logged_in = self.playwright_crawler.is_logged_in
            logger.info("小红书真实数据爬虫启动成功")
        except Exception as e:
            logger.error(f"启动爬虫失败: {e}")
            raise
    
    async def close(self):
        """关闭爬虫"""
        try:
            await self.playwright_crawler.close()
            self.is_started = False
            self.is_logged_in = False
            logger.info("小红书真实数据爬虫已关闭")
        except Exception as e:
            logger.error(f"关闭爬虫失败: {e}")
    
    async def login_with_qr(self, timeout: int = 60) -> bool:
        """二维码登录"""
        try:
            if not self.is_started:
                await self.start()
            
            success = await self.playwright_crawler.login_with_qr(timeout)
            self.is_logged_in = success
            return success
        except Exception as e:
            logger.error(f"二维码登录失败: {e}")
            return False
    
    async def check_login_status(self) -> bool:
        """检查登录状态"""
        try:
            if not self.is_started:
                return False
            
            status = await self.playwright_crawler.check_login_status()
            # 同步登录状态
            self.is_logged_in = status
            return status
        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")
            return False
    
    async def search(self, keyword: str, max_notes: int = 20) -> List[Dict[str, Any]]:
        """搜索笔记"""
        try:
            if not self.is_started:
                await self.start()
            
            # 检查登录状态
            if not self.is_logged_in:
                await self.check_login_status()
            
            if not self.is_logged_in:
                logger.warning("用户未登录，建议先登录获取更好的数据")
            
            notes = await self.playwright_crawler.search_notes(keyword, max_notes)
            logger.info(f"搜索 '{keyword}' 获得 {len(notes)} 条真实数据")
            return notes
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []

    async def ensure_logged_in(self, force_reload: bool = False) -> bool:
        """确保当前会话已登录，必要时尝试重新加载Cookies或重启浏览器"""
        if not self.is_started:
            await self.start()

        if not force_reload and self.is_logged_in:
            return True

        if await self.check_login_status():
            return True

        logger.warning("检测到登录状态已失效，尝试重新加载Cookies")
        try:
            if await self.playwright_crawler.reload_cookies():
                if await self.check_login_status():
                    logger.info("通过重新加载Cookies恢复登录状态成功")
                    return True
        except Exception as e:
            logger.error(f"重新加载Cookies失败: {e}")

        logger.warning("Cookies刷新仍未登录，尝试重启浏览器后重试")
        await self.restart()
        return await self.check_login_status()

    async def restart(self):
        """重新启动浏览器实例"""
        try:
            if self.is_started:
                await self.close()
        finally:
            await self.start()
    
    async def get_note_by_keyword(self, keyword: str, page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
        """根据关键词获取笔记（兼容旧接口）"""
        max_notes = page * page_size
        all_notes = await self.search(keyword, max_notes)
        
        # 分页处理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        return all_notes[start_idx:end_idx]
    
    # 实现抽象基类的必需方法
    def launch_browser(self):
        """启动浏览器（同步版本，用于兼容）"""
        try:
            # 在新的事件循环中运行异步方法
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.start())
            loop.close()
        except Exception as e:
            logger.error(f"同步启动浏览器失败: {e}")
            raise
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


class XiaoHongShuLoginCrawler:
    """小红书登录爬虫 - 专门用于登录操作"""
    
    def __init__(self):
        self.crawler = XiaoHongShuRealCrawler()
    
    async def interactive_login(self) -> bool:
        """交互式登录流程"""
        try:
            logger.info("=== 小红书登录流程 ===")
            logger.info("1. 启动浏览器...")
            
            await self.crawler.start()
            
            logger.info("2. 检查当前登录状态...")
            if await self.crawler.check_login_status():
                logger.info("✅ 用户已登录！")
                return True
            
            logger.info("3. 开始二维码登录...")
            logger.info("📱 请使用小红书APP扫描二维码登录")
            
            success = await self.crawler.login_with_qr(timeout=120)  # 2分钟超时
            
            if success:
                logger.info("✅ 登录成功！")
                logger.info("🎉 现在可以获取真实数据了")
            else:
                logger.error("❌ 登录失败或超时")
            
            return success
            
        except Exception as e:
            logger.error(f"登录流程失败: {e}")
            return False
        finally:
            # 不关闭浏览器，保持登录状态
            pass
    
    async def test_search(self, keyword: str = "北京旅游") -> List[Dict[str, Any]]:
        """测试搜索功能"""
        try:
            logger.info(f"🔍 测试搜索: {keyword}")
            notes = await self.crawler.search(keyword, max_notes=5)
            
            if notes:
                logger.info(f"✅ 成功获取 {len(notes)} 条真实数据")
                for i, note in enumerate(notes[:3], 1):
                    logger.info(f"  {i}. {note['title'][:50]}...")
            else:
                logger.warning("⚠️ 未获取到数据")
            
            return notes
            
        except Exception as e:
            logger.error(f"测试搜索失败: {e}")
            return []
    
    async def close(self):
        """关闭爬虫"""
        await self.crawler.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# 创建全局实例（单例模式）
_global_crawler_instance = None

def get_crawler_instance() -> XiaoHongShuRealCrawler:
    """获取全局爬虫实例"""
    global _global_crawler_instance
    if _global_crawler_instance is None:
        _global_crawler_instance = XiaoHongShuRealCrawler()
    return _global_crawler_instance
