"""
应用配置管理
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """应用配置"""
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    # 基础配置
    APP_NAME: str = os.getenv("APP_NAME", "LX SkyRoam Agent")
    VERSION: str = os.getenv("VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", False)
    
    # 服务器配置
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = os.getenv("PORT", 8000)
    ALLOWED_HOSTS: List[str] = os.getenv("ALLOWED_HOSTS", "*").split(",") if isinstance(os.getenv("ALLOWED_HOSTS", "*"), str) else ["*"]
    
    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:123456@localhost:5432/skyroam")
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", False)
    
    # Redis配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    
    # Celery配置
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    
    # OpenAI配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")  # 自定义API地址
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    OPENAI_MAX_TOKENS: int = os.getenv("OPENAI_MAX_TOKENS", 4000)
    OPENAI_TEMPERATURE: float = os.getenv("OPENAI_TEMPERATURE", 0.7)
    OPENAI_TIMEOUT: int = os.getenv("OPENAI_TIMEOUT", 300)  # API超时时间（秒）
    OPENAI_MAX_RETRIES: int = os.getenv("OPENAI_MAX_RETRIES", 3)  # 最大重试次数
    
    # 第三方API配置
    WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "")  # OpenWeatherMap
    
    # Amadeus API配置
    AMADEUS_CLIENT_ID: str = os.getenv("AMADEUS_CLIENT_ID", "")
    AMADEUS_CLIENT_SECRET: str = os.getenv("AMADEUS_CLIENT_SECRET", "")
    AMADEUS_API_BASE: str = os.getenv("AMADEUS_API_BASE", "https://test.api.amadeus.com")
    AMADEUS_TOKEN_URL: str = os.getenv("AMADEUS_TOKEN_URL", "https://test.api.amadeus.com/v1/security/oauth2/token")
    
    HOTEL_API_KEY: str = os.getenv("HOTEL_API_KEY", "")    # Booking.com
    MAP_API_KEY: str = os.getenv("MAP_API_KEY", "")      # Google Maps
    
    # MCP服务配置
    BAIDU_MCP_ENDPOINT: str = os.getenv("BAIDU_MCP_ENDPOINT", "http://localhost:3001")  # 百度地图MCP服务端口
    AMAP_MCP_ENDPOINT: str = os.getenv("AMAP_MCP_ENDPOINT", "http://localhost:3002")  # 高德地图MCP服务
    MCP_TIMEOUT: int = os.getenv("MCP_TIMEOUT", 30)  # MCP服务超时时间（秒）

    # MCP服务API密钥（通过环境变量传递给MCP服务）
    BAIDU_MAPS_API_KEY: str = os.getenv("BAIDU_MAPS_API_KEY", "")  # 百度地图API密钥
    AMAP_API_KEY: str = os.getenv("AMAP_API_KEY", "")  # 高德地图API密钥
    
    # 地图服务提供商配置
    MAP_PROVIDER: str = os.getenv("MAP_PROVIDER", "amap")  # 地图服务提供商: "baidu" 或 "amap"
    
    # 餐厅数据源配置
    RESTAURANT_DATA_SOURCE: str = os.getenv("RESTAURANT_DATA_SOURCE", "amap")  # 餐厅数据源: "baidu" 或 "amap" 或 "both"
    
    # 天气数据源配置
    WEATHER_DATA_SOURCE: str = os.getenv("WEATHER_DATA_SOURCE", "amap")  # 天气数据源: "baidu" 或 "amap" 或 "openweather"
    
    # 高德地图MCP服务配置
    AMAP_MCP_MODE: str = os.getenv("AMAP_MCP_MODE", "http")  # 高德地图MCP模式: "http" 或 "sse"
    AMAP_MCP_HTTP_URL: str = os.getenv("AMAP_MCP_HTTP_URL", "http://localhost:3002/mcp")  # Streamable HTTP方式
    AMAP_MCP_SSE_URL: str = os.getenv("AMAP_MCP_SSE_URL", "http://localhost:3002/sse")   # SSE方式

    # 爬虫配置
    SCRAPY_USER_AGENT: str = os.getenv("SCRAPY_USER_AGENT", "LX-SkyRoam-Agent/1.0")
    SCRAPY_DELAY: float = os.getenv("SCRAPY_DELAY", 1.0)
    SCRAPY_CONCURRENT_REQUESTS: int = os.getenv("SCRAPY_CONCURRENT_REQUESTS", 16)

    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30)

    # 文件存储
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE: int = os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024)  # 10MB

    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")

    # 缓存配置
    CACHE_TTL: int = os.getenv("CACHE_TTL", 3600)  # 1小时
    CACHE_MAX_SIZE: int = os.getenv("CACHE_MAX_SIZE", 1000)

    # 任务配置
    TASK_TIMEOUT: int = os.getenv("TASK_TIMEOUT", 300)  # 5分钟
    MAX_CONCURRENT_TASKS: int = os.getenv("MAX_CONCURRENT_TASKS", 10)

    # 数据源配置
    DATA_SOURCES: List[str] = [
        "flights",
        "hotels", 
        "attractions",
        "weather",
        "restaurants",
        "transportation"
    ]

    # 评分权重配置
    SCORING_WEIGHTS: dict = {
        "price": 0.3,
        "rating": 0.25,
        "convenience": 0.2,
        "safety": 0.15,
        "popularity": 0.1
    }

# 创建全局配置实例
settings = Settings()

# 确保必要的目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs("logs", exist_ok=True)
