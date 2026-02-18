"""
消息处理器基类
定义所有消息处理器的通用接口和方法
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from src.utils.logger import logger


class BaseHandler(ABC):
    """消息处理器基类"""
    
    def __init__(self):
        """初始化处理器"""
        self.logger = logger
    
    @abstractmethod
    async def handle(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理消息的抽象方法
        
        Args:
            message: 飞书消息数据
            
        Returns:
            处理结果
        """
        pass
    
    def extract_user_info(self, message: Dict[str, Any]) -> Dict[str, str]:
        """
        提取用户信息
        
        Args:
            message: 飞书消息数据
            
        Returns:
            用户信息字典
        """
        sender = message.get("sender", {})
        sender_id = sender.get("sender_id", {})
        
        return {
            "open_id": sender_id.get("open_id", ""),
            "user_id": sender_id.get("user_id", ""),
            "union_id": sender_id.get("union_id", "")
        }
    
    def extract_chat_info(self, message: Dict[str, Any]) -> Dict[str, str]:
        """
        提取聊天信息
        
        Args:
            message: 飞书消息数据
            
        Returns:
            聊天信息字典
        """
        return {
            "chat_id": message.get("chat_id", ""),
            "chat_type": message.get("chat_type", ""),
            "message_id": message.get("message_id", "")
        }
