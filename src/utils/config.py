"""
配置管理模块
管理应用的所有配置信息，包括飞书配置、服务器配置、数据库配置等
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置类"""
    
    # 飞书机器人配置
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_verification_token: str = ""
    feishu_encrypt_key: str = ""
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000
    
    # 数据库配置
    database_url: str = "sqlite:///./feishu_diary.db"
    
    # 日志配置
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    
    # LLM 配置（支持 OpenAI 和 SiliconFlow）
    llm_api_key: str = ""
    llm_api_base: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-3.5-turbo"
    
    # 应用配置
    app_name: str = "Feishu Diary Bot"
    app_version: str = "1.0.0"
    debug: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置实例（单例模式）
    使用lru_cache确保只创建一个配置实例
    """
    return Settings()


# 导出配置实例
settings = get_settings()
