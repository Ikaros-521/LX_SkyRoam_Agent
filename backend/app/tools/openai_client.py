"""
OpenAI客户端工具
支持自定义API地址和配置
"""

import openai
from typing import Optional, Dict, Any, List
from loguru import logger
import asyncio
from app.core.config import settings


class OpenAIClient:
    """OpenAI客户端"""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.api_base = settings.OPENAI_API_BASE
        self.model = settings.OPENAI_MODEL
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.temperature = settings.OPENAI_TEMPERATURE
        self.timeout = settings.OPENAI_TIMEOUT
        self.max_retries = settings.OPENAI_MAX_RETRIES
        
        # 配置OpenAI客户端
        self._configure_client()
    
    def _configure_client(self):
        """配置OpenAI客户端"""
        try:
            # 设置API密钥
            openai.api_key = self.api_key
            
            # 如果设置了自定义API地址，则使用自定义地址
            if self.api_base and self.api_base != "https://api.openai.com/v1":
                openai.api_base = self.api_base
                logger.info(f"使用自定义OpenAI API地址: {self.api_base}")
            else:
                logger.info("使用默认OpenAI API地址")
            
            # 设置默认参数
            openai.api_timeout = self.timeout
            
        except Exception as e:
            logger.error(f"配置OpenAI客户端失败: {e}")
            raise
    
    async def generate_text(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """生成文本"""
        try:
            messages = []
            
            # 添加系统提示
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # 添加用户提示
            messages.append({"role": "user", "content": prompt})
            
            # 调用API
            response = await self._call_api(
                messages=messages,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature or self.temperature,
                **kwargs
            )

            # logger.debug(f"OpenAI API响应: {response.choices[0].message.content}")
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"生成文本失败: {e}")
            raise
    
    async def generate_travel_plan(
        self, 
        destination: str, 
        duration_days: int, 
        budget: float,
        preferences: List[str],
        requirements: str = "",
        map_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """生成旅行计划"""
        try:
            system_prompt = """你是一个专业的旅行规划师，擅长为游客制定详细的旅行计划。
请根据用户的需求，生成一个结构化的旅行方案，包括：
1. 每日行程安排
2. 推荐景点
3. 餐饮建议
4. 交通安排
5. 预算分配
6. 注意事项

请以JSON格式返回结果。"""
            
            # 构建地图数据信息
            map_info = ""
            if map_data:
                map_info = f"""

百度地图数据：
景点信息：{len(map_data.get('attractions', []))}个景点
交通信息：{len(map_data.get('transportation', []))}种交通方式
餐厅信息：{len(map_data.get('restaurants', []))}家餐厅
天气信息：{map_data.get('weather', {})}

请充分利用这些真实数据制定计划。
"""

            user_prompt = f"""
请为以下旅行需求制定详细计划：

目的地：{destination}
旅行天数：{duration_days}天
预算：{budget}元
旅行偏好：{', '.join(preferences)}
特殊要求：{requirements}{map_info}

请生成一个完整的旅行方案，优先考虑交通便利的景点和实用的交通方式。
"""
            
            response = await self.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=self.max_tokens
            )
            
            # 尝试解析JSON响应
            import json
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # 如果不是JSON格式，返回文本响应
                return {
                    "plan": response,
                    "destination": destination,
                    "duration_days": duration_days,
                    "budget": budget
                }
                
        except Exception as e:
            logger.error(f"生成旅行计划失败: {e}")
            raise
    
    async def analyze_travel_data(
        self, 
        data: Dict[str, Any], 
        analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """分析旅行数据"""
        try:
            system_prompt = """你是一个专业的旅行数据分析师，擅长分析各种旅行数据，
包括景点、酒店、餐厅、交通等信息。请提供专业的分析和建议。"""
            
            user_prompt = f"""
请分析以下旅行数据，分析类型：{analysis_type}

数据内容：
{data}

请提供详细的分析报告和建议。
"""
            
            response = await self.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=self.max_tokens
            )
            
            return {
                "analysis": response,
                "analysis_type": analysis_type,
                "data_summary": self._summarize_data(data)
            }
            
        except Exception as e:
            logger.error(f"分析旅行数据失败: {e}")
            raise
    
    async def optimize_travel_plan(
        self, 
        current_plan: Dict[str, Any], 
        optimization_goals: List[str]
    ) -> Dict[str, Any]:
        """优化旅行计划"""
        try:
            system_prompt = """你是一个旅行计划优化专家，擅长根据用户需求优化现有的旅行计划。
请提供具体的优化建议和改进方案。"""
            
            user_prompt = f"""
请优化以下旅行计划：

当前计划：
{current_plan}

优化目标：
{', '.join(optimization_goals)}

请提供优化后的计划和改进建议。
"""
            
            response = await self.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=self.max_tokens
            )
            
            return {
                "optimized_plan": response,
                "optimization_goals": optimization_goals,
                "original_plan": current_plan
            }
            
        except Exception as e:
            logger.error(f"优化旅行计划失败: {e}")
            raise
    
    async def _call_api(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs
    ) -> Any:
        """调用OpenAI API"""
        try:
            # 使用异步客户端
            client = openai.AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.api_base if self.api_base != "https://api.openai.com/v1" else None,
                timeout=self.timeout
            )
            
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                temperature=kwargs.get('temperature', self.temperature),
                **{k: v for k, v in kwargs.items() if k not in ['max_tokens', 'temperature']}
            )
            
            return response
            
        except Exception as e:
            logger.error(f"调用OpenAI API失败: {e}")
            raise
    
    def _summarize_data(self, data: Dict[str, Any]) -> str:
        """总结数据"""
        summary = []
        
        if 'attractions' in data:
            summary.append(f"景点数量: {len(data['attractions'])}")
        
        if 'hotels' in data:
            summary.append(f"酒店数量: {len(data['hotels'])}")
        
        if 'restaurants' in data:
            summary.append(f"餐厅数量: {len(data['restaurants'])}")
        
        if 'flights' in data:
            summary.append(f"航班数量: {len(data['flights'])}")
        
        return "; ".join(summary)
    
    def get_client_info(self) -> Dict[str, Any]:
        """获取客户端信息"""
        return {
            "api_base": self.api_base,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "has_api_key": bool(self.api_key)
        }


# 创建全局客户端实例
openai_client = OpenAIClient()
