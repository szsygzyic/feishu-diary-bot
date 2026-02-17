"""
飞书客户端初始化模块
配置和管理飞书开放平台客户端
"""

from lark_oapi import Client
from src.utils.config import settings
from src.utils.logger import logger


class FeishuClient:
    """飞书客户端管理类"""
    
    _instance = None
    
    def __new__(cls):
        """单例模式，确保只有一个客户端实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = None
        return cls._instance
    
    def init_client(self) -> Client:
        """
        初始化飞书客户端
        
        Returns:
            配置好的飞书客户端实例
        """
        if self._client is None:
            try:
                self._client = Client.builder() \
                    .app_id(settings.feishu_app_id) \
                    .app_secret(settings.feishu_app_secret) \
                    .build()
                logger.info("飞书客户端初始化成功")
            except Exception as e:
                logger.error(f"飞书客户端初始化失败: {e}")
                raise
        
        return self._client
    
    def get_client(self) -> Client:
        """
        获取飞书客户端实例
        
        Returns:
            飞书客户端实例
        """
        if self._client is None:
            return self.init_client()
        return self._client
    
    def is_configured(self) -> bool:
        """
        检查飞书配置是否完整
        
        Returns:
            配置是否完整
        """
        return all([
            settings.feishu_app_id,
            settings.feishu_app_secret
        ])


# 创建全局飞书客户端实例
feishu_client = FeishuClient()
