"""
媒体文件处理器
处理用户发送的图片和视频消息
保存媒体信息到上下文，在生成日记时再下载上传
"""

import json
from typing import Dict, Any
from .base_handler import BaseHandler
from src.services.conversation_service import conversation_service
from src.services.message_service import message_service


class MediaHandler(BaseHandler):
    """媒体文件处理器"""
    
    async def handle(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理媒体文件消息
        
        Args:
            message: 飞书媒体消息数据
            
        Returns:
            处理结果
        """
        try:
            # 提取用户信息
            user_info = self.extract_user_info(message)
            chat_info = self.extract_chat_info(message)
            user_id = user_info['open_id']
            
            # 获取消息类型
            message_type = message.get("message_type", "")
            
            self.logger.info(f"收到媒体消息，类型: {message_type}, 用户: {user_id}")
            
            # 根据类型处理
            if message_type == "image":
                return await self.handle_image(message, user_info, chat_info)
            elif message_type == "media":
                return await self.handle_video(message, user_info, chat_info)
            else:
                return {"code": 1, "msg": f"不支持的媒体类型: {message_type}"}
                
        except Exception as e:
            self.logger.error(f"处理媒体消息时出错: {e}")
            return {"code": 1, "msg": f"媒体处理失败: {str(e)}"}
    
    async def handle_image(self, message: Dict[str, Any], user_info: Dict[str, str], chat_info: Dict[str, str]) -> Dict[str, Any]:
        """
        处理图片消息
        保存图片信息到上下文，在生成日记时再下载上传
        
        Args:
            message: 图片消息数据
            user_info: 用户信息
            chat_info: 聊天信息
            
        Returns:
            处理结果
        """
        try:
            user_id = user_info['open_id']
            
            # 解析消息内容获取图片信息
            content = json.loads(message.get("content", "{}"))
            
            # 获取图片信息
            image_key = content.get("image_key", "")
            file_name = content.get("file_name", "image.jpg")
            message_id = message.get("message_id", "")
            
            self.logger.info(f"处理图片: {file_name}, key: {image_key}, message_id: {message_id}")
            
            # 保存媒体信息到上下文（用于后续生成日记时下载上传）
            # 使用 message_id 和 image_key 作为 file_key 来下载资源
            media_info = {
                "type": "image",
                "file_name": file_name,
                "image_key": image_key,
                "message_id": message_id,
                "status": "pending"  # 待处理状态
            }
            
            # 添加媒体信息到上下文
            conversation_service.add_media_to_context(user_id, media_info)
            
            # 添加文本描述到上下文
            conversation_service.add_message(
                user_id, 
                "user", 
                f"[图片: {file_name}]"
            )
            
            # 回复用户
            reply = "图片已收到，我会在整理日记时保存它。还有其他内容吗？"
            await message_service.send_text_message(user_id, reply)
            
            # 保存助手回复
            conversation_service.add_message(user_id, "assistant", reply)
            
            return {
                "code": 0,
                "msg": "图片已接收",
                "data": {
                    "type": "image",
                    "user_id": user_id,
                    "file_name": file_name,
                    "image_key": image_key,
                    "message_id": message_id
                }
            }
            
        except Exception as e:
            self.logger.error(f"处理图片失败: {e}")
            return {"code": 1, "msg": f"图片处理失败: {str(e)}"}
    
    async def handle_video(self, message: Dict[str, Any], user_info: Dict[str, str], chat_info: Dict[str, str]) -> Dict[str, Any]:
        """
        处理视频消息
        保存视频信息到上下文
        
        Args:
            message: 视频消息数据
            user_info: 用户信息
            chat_info: 聊天信息
            
        Returns:
            处理结果
        """
        try:
            user_id = user_info['open_id']
            
            # 解析消息内容获取视频信息
            content = json.loads(message.get("content", "{}"))
            
            # 获取视频信息
            file_key = content.get("file_key", "")
            file_name = content.get("file_name", "video.mp4")
            file_size = content.get("file_size", 0)
            size_mb = file_size / (1024 * 1024)
            
            self.logger.info(f"处理视频: {file_name}, key: {file_key}, size: {size_mb:.1f}MB")
            
            # 保存媒体信息到上下文
            media_info = {
                "type": "video",
                "file_name": file_name,
                "file_key": file_key,
                "file_size": file_size,
                "status": "pending"
            }
            
            conversation_service.add_media_to_context(user_id, media_info)
            
            # 添加文本描述到上下文
            conversation_service.add_message(
                user_id, 
                "user", 
                f"[视频: {file_name} ({size_mb:.1f}MB)]"
            )
            
            # 回复用户
            if size_mb > 20:
                reply = f"🎬 视频已收到（{size_mb:.1f}MB）。\n⚠️ 注意：视频较大，我会在整理日记时尝试保存，但可能无法在文档中直接预览。"
            else:
                reply = "🎬 视频已收到，我会在整理日记时保存它。还有其他内容吗？"
            
            await message_service.send_text_message(user_id, reply)
            
            # 保存助手回复
            conversation_service.add_message(user_id, "assistant", reply)
            
            return {
                "code": 0,
                "msg": "视频已接收",
                "data": {
                    "type": "video",
                    "user_id": user_id,
                    "file_name": file_name,
                    "file_key": file_key,
                    "file_size": file_size
                }
            }
            
        except Exception as e:
            self.logger.error(f"处理视频失败: {e}")
            return {"code": 1, "msg": f"视频处理失败: {str(e)}"}
