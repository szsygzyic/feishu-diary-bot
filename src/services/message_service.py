"""
消息发送服务
用于向飞书用户发送消息
"""

import json
from typing import Dict, Any, Optional
import httpx
from src.utils.config import settings
from src.utils.logger import logger


class MessageService:
    """消息发送服务"""
    
    def __init__(self):
        """初始化消息服务"""
        self.app_id = settings.feishu_app_id
        self.app_secret = settings.feishu_app_secret
        self.access_token = None
    
    async def _get_access_token(self) -> str:
        """
        获取飞书访问令牌
        
        Returns:
            access_token
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal",
                    json={
                        "app_id": self.app_id,
                        "app_secret": self.app_secret
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 0:
                        return result["app_access_token"]
                    else:
                        logger.error(f"获取token失败: {result}")
                        return ""
                else:
                    logger.error(f"获取token请求失败: {response.status_code}")
                    return ""
        except Exception as e:
            logger.error(f"获取token异常: {e}")
            return ""
    
    async def send_text_message(self, user_id: str, text: str) -> Dict[str, Any]:
        """
        发送文字消息
        
        Args:
            user_id: 用户open_id
            text: 消息内容
            
        Returns:
            发送结果
        """
        try:
            # 获取access_token
            token = await self._get_access_token()
            if not token:
                logger.error("无法获取access_token")
                return {"code": 1, "msg": "无法获取access_token"}
            
            # 构建消息内容
            content = json.dumps({"text": text})
            
            # 调用飞书API发送消息
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://open.feishu.cn/open-apis/im/v1/messages",
                    params={"receive_id_type": "open_id"},
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "receive_id": user_id,
                        "content": content,
                        "msg_type": "text"
                    }
                )
                
                logger.info(f"发送消息API响应: {response.status_code} - {response.text}")
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 0:
                        logger.info(f"消息发送成功: {user_id}")
                        return {
                            "code": 0,
                            "msg": "消息发送成功",
                            "data": result.get("data", {})
                        }
                    else:
                        logger.error(f"消息发送失败: {result}")
                        return {
                            "code": 1,
                            "msg": f"发送失败: {result.get('msg', '未知错误')}"
                        }
                else:
                    logger.error(f"消息发送请求失败: {response.status_code} - {response.text}")
                    return {
                        "code": 1,
                        "msg": f"请求失败: {response.status_code}"
                    }
            
        except Exception as e:
            logger.error(f"发送消息异常: {e}")
            return {"code": 1, "msg": f"发送异常: {str(e)}"}
    
    async def reply_message(self, message_id: str, text: str) -> Dict[str, Any]:
        """
        回复消息
        
        Args:
            message_id: 原消息ID
            text: 回复内容
            
        Returns:
            发送结果
        """
        try:
            # 获取access_token
            token = await self._get_access_token()
            if not token:
                return {"code": 1, "msg": "无法获取access_token"}
            
            # 构建消息内容
            content = json.dumps({"text": text})
            
            # 调用飞书API回复消息
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "content": content,
                        "msg_type": "text"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 0:
                        logger.info(f"消息回复成功: {message_id}")
                        return {"code": 0, "msg": "回复成功"}
                    else:
                        logger.error(f"消息回复失败: {result}")
                        return {"code": 1, "msg": f"回复失败: {result.get('msg', '未知错误')}"}
                else:
                    logger.error(f"消息回复请求失败: {response.status_code}")
                    return {"code": 1, "msg": f"请求失败: {response.status_code}"}
            
        except Exception as e:
            logger.error(f"回复消息异常: {e}")
            return {"code": 1, "msg": f"回复异常: {str(e)}"}


# 创建全局消息服务实例
message_service = MessageService()
