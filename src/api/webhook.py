"""
飞书Webhook接口
接收和处理飞书机器人发送的事件回调
"""

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from typing import Dict, Any
import json
import base64
import hashlib
import time
from Crypto.Cipher import AES

from src.utils.config import settings
from src.utils.logger import logger
from src.handlers.text_handler import TextHandler
from src.handlers.voice_handler import VoiceHandler
from src.handlers.media_handler import MediaHandler
from src.services.diary_service import diary_service

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

# 创建消息处理器实例
text_handler = TextHandler()
voice_handler = VoiceHandler()
media_handler = MediaHandler()

# 消息去重缓存（简单实现，生产环境建议使用Redis）
processed_messages = {}


class AESCipher:
    """AES解密工具类"""
    
    def __init__(self, key: str):
        """
        初始化AES解密器
        
        Args:
            key: 加密密钥（需要是16、24或32字节）
        """
        # 使用SHA256生成32字节密钥
        self.key = hashlib.sha256(key.encode('utf-8')).digest()
        self.block_size = AES.block_size
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        解密数据
        
        Args:
            encrypted_data: Base64编码的加密数据
            
        Returns:
            解密后的字符串
        """
        try:
            # Base64解码
            encrypted_bytes = base64.b64decode(encrypted_data)
            
            # 提取IV（前16字节）和密文
            iv = encrypted_bytes[:self.block_size]
            ciphertext = encrypted_bytes[self.block_size:]
            
            # 创建AES解密器
            cipher = AES.new(self.key, AES.MODE_CBC, iv)
            
            # 解密
            decrypted = cipher.decrypt(ciphertext)
            
            # 去除PKCS7填充
            pad_length = decrypted[-1]
            decrypted = decrypted[:-pad_length]
            
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"解密失败: {e}")
            raise


def decrypt_message(encrypt_data: str) -> Dict[str, Any]:
    """
    解密飞书消息
    
    Args:
        encrypt_data: 加密的消息数据
        
    Returns:
        解密后的消息字典
    """
    if not settings.feishu_encrypt_key:
        raise ValueError("FEISHU_ENCRYPT_KEY 未配置")
    
    cipher = AESCipher(settings.feishu_encrypt_key)
    decrypted_str = cipher.decrypt(encrypt_data)
    return json.loads(decrypted_str)


def is_duplicate_message(message_id: str) -> bool:
    """
    检查消息是否已处理（防重）
    
    Args:
        message_id: 消息ID
        
    Returns:
        是否重复
    """
    current_time = time.time()
    
    # 清理过期记录（5分钟前的）
    expired_keys = [k for k, v in processed_messages.items() if current_time - v > 300]
    for k in expired_keys:
        del processed_messages[k]
    
    # 检查是否已处理
    if message_id in processed_messages:
        return True
    
    # 记录消息
    processed_messages[message_id] = current_time
    return False


async def process_message_async(message: Dict[str, Any], sender: Dict[str, Any], message_type: str):
    """
    异步处理消息（后台任务）
    
    Args:
        message: 消息数据
        sender: 发送者信息
        message_type: 消息类型
    """
    try:
        # 合并消息和发送者信息
        full_message = {**message, "sender": sender}
        
        # 根据消息类型分发到不同的处理器
        if message_type == "text":
            await text_handler.handle(full_message)
        elif message_type == "audio":
            await voice_handler.handle(full_message)
        elif message_type in ["image", "media"]:
            await media_handler.handle(full_message)
        else:
            logger.warning(f"不支持的消息类型: {message_type}")
            
    except Exception as e:
        logger.error(f"异步处理消息失败: {e}")


@router.post("/event")
async def handle_event(request: Request, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    处理飞书事件回调
    
    Args:
        request: FastAPI请求对象
        background_tasks: 后台任务
        
    Returns:
        响应数据
    """
    try:
        # 获取请求体
        body = await request.body()
        body_str = body.decode('utf-8')
        
        data = json.loads(body_str)
        
        # 处理加密消息
        if "encrypt" in data:
            try:
                decrypted_data = decrypt_message(data["encrypt"])
                data = decrypted_data
            except Exception as e:
                logger.error(f"解密消息失败: {e}")
        
        # 处理URL验证（飞书首次配置回调时需要）
        if "challenge" in data:
            challenge = data["challenge"]
            logger.info(f"收到challenge验证: {challenge}")
            return {"challenge": challenge}
        
        # 解析事件数据
        event_data = data.get("event", {})
        header = data.get("header", {})
        event_type = header.get("event_type", "")
        
        # 处理消息接收事件
        if event_type == "im.message.receive_v1":
            message = event_data.get("message", {})
            sender = event_data.get("sender", {})
            message_type = message.get("message_type", "")
            message_id = message.get("message_id", "")

            # 检查消息是否已处理（防重）
            if is_duplicate_message(message_id):
                logger.info(f"消息已处理，跳过: {message_id}")
                return {"code": 0, "msg": "success"}

            logger.info(f"收到消息，类型: {message_type}, id: {message_id}")

            # 使用后台任务处理消息，立即返回响应
            background_tasks.add_task(process_message_async, message, sender, message_type)

        # 处理文档彻底删除事件
        elif event_type == "drive.file.deleted_completely_v1":
            file_token = event_data.get("file_token", "")
            file_type = event_data.get("file_type", "")

            logger.info(f"收到文档彻底删除事件: {file_token}, 类型: {file_type}")

            # 从数据库中删除对应的日记记录
            if file_token:
                # 查找并删除包含该文档ID的日记记录
                diaries = diary_service.get_diaries_by_document_id(file_token)
                if diaries:
                    for diary in diaries:
                        diary_id = diary.get('id')
                        if diary_id:
                            success = diary_service.delete_diary(diary_id)
                            if success:
                                logger.info(f"日记记录已同步删除: {diary_id}, 文档: {file_token}")
                            else:
                                logger.error(f"日记记录删除失败: {diary_id}")
                else:
                    logger.info(f"未找到关联的日记记录: {file_token}")

        # 立即返回成功响应（避免飞书超时重试）
        return {"code": 0, "msg": "success"}
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"处理事件时出错: {e}")
        # 即使出错也返回成功，避免飞书重试
        return {"code": 0, "msg": "success"}
