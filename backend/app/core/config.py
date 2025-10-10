"""
应用配置管理
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """应用配置"""
    
    # 基础配置
    APP_NAME: str = "LX SkyRoam Agent"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # 数据库配置
    DATABASE_URL: str = "postgresql://postgres:123456@localhost:5432/skyroam"
    DATABASE_ECHO: bool = False
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    
    # Celery配置
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # OpenAI配置
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"  # 自定义API地址
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    OPENAI_MAX_TOKENS: int = 4000
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_TIMEOUT: int = 60  # API超时时间（秒）
    OPENAI_MAX_RETRIES: int = 3  # 最大重试次数
    
    # 第三方API配置
    WEATHER_API_KEY: str = ""  # OpenWeatherMap
    FLIGHT_API_KEY: str = ""   # Amadeus
    HOTEL_API_KEY: str = ""    # Booking.com
    MAP_API_KEY: str = ""      # Google Maps
    
    # 爬虫配置
    SCRAPY_USER_AGENT: str = "LX-SkyRoam-Agent/1.0"
    SCRAPY_DELAY: float = 1.0
    SCRAPY_CONCURRENT_REQUESTS: int = 16
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 文件存储
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # 缓存配置
    CACHE_TTL: int = 3600  # 1小时
    CACHE_MAX_SIZE: int = 1000
    
    # 任务配置
    TASK_TIMEOUT: int = 300  # 5分钟
    MAX_CONCURRENT_TASKS: int = 10
    
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
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()

# 确保必要的目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs("logs", exist_ok=True)
