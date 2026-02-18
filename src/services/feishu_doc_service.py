"""
飞书文档服务
用于创建、编辑和管理飞书文档
支持图片插入功能
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx
from urllib.parse import quote
from src.utils.config import settings
from src.utils.logger import logger


class FeishuDocService:
    """飞书文档服务"""
    
    def __init__(self):
        """初始化文档服务"""
        self.app_id = settings.feishu_app_id
        self.app_secret = settings.feishu_app_secret
    
    async def _get_tenant_access_token(self) -> str:
        """获取租户访问令牌"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                    json={
                        "app_id": self.app_id,
                        "app_secret": self.app_secret
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 0:
                        return result["tenant_access_token"]
                    else:
                        logger.error("获取tenant_token失败: " + str(result))
                        return ""
                else:
                    logger.error("获取tenant_token请求失败: " + str(response.status_code))
                    return ""
        except Exception as e:
            logger.error("获取tenant_token异常: " + str(e))
            return ""
    
    async def create_document(self, title: str, content: str, folder_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """创建飞书文档"""
        try:
            token = await self._get_tenant_access_token()
            if not token:
                logger.error("无法获取tenant_access_token")
                return None
            
            async with httpx.AsyncClient() as client:
                # 创建文档
                create_response = await client.post(
                    "https://open.feishu.cn/open-apis/docx/v1/documents",
                    headers={"Authorization": "Bearer " + token},
                    json={
                        "title": title,
                        "folder_token": folder_token
                    }
                )
                
                if create_response.status_code != 200:
                    logger.error("创建文档失败: " + str(create_response.status_code))
                    return None
                
                create_result = create_response.json()
                if create_result.get("code") != 0:
                    logger.error("创建文档API错误: " + str(create_result))
                    return None
                
                document_info = create_result["data"]["document"]
                document_id = document_info["document_id"]
                
                logger.info("文档创建成功: " + document_id)
                
                # 添加文档内容
                content_added = await self._add_document_content(document_id, content, token)
                
                if not content_added:
                    logger.warning("文档内容添加失败，但文档已创建")
                
                return {
                    "document_id": document_id,
                    "title": title,
                    "url": "https://www.feishu.cn/docx/" + document_id
                }
                
        except Exception as e:
            logger.error("创建文档异常: " + str(e))
            return None
    
    async def _add_document_content(self, document_id: str, content: str, token: str) -> bool:
        """添加文档内容"""
        try:
            blocks = self._convert_content_to_blocks(content)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://open.feishu.cn/open-apis/docx/v1/documents/" + document_id + "/blocks/" + document_id + "/children",
                    headers={"Authorization": "Bearer " + token},
                    json={
                        "children": blocks
                    }
                )
                
                logger.info("添加内容API响应: " + str(response.status_code) + " - " + response.text[:200])
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 0:
                        logger.info("文档内容添加成功: " + document_id)
                        return True
                    else:
                        logger.error("添加内容API错误: " + str(result))
                        return False
                else:
                    logger.error("添加内容请求失败: " + str(response.status_code))
                    return False
                    
        except Exception as e:
            logger.error("添加文档内容异常: " + str(e))
            return False
    
    def _convert_content_to_blocks(self, content: str) -> List[Dict[str, Any]]:
        """将文本内容转换为飞书文档块"""
        blocks = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 标题（以 # 开头）
            if line.startswith('# '):
                blocks.append({
                    "block_type": 3,
                    "heading1": {
                        "elements": [{"text_run": {"content": line[2:]}}]
                    }
                })
            elif line.startswith('## '):
                blocks.append({
                    "block_type": 4,
                    "heading2": {
                        "elements": [{"text_run": {"content": line[3:]}}]
                    }
                })
            elif line.startswith('### '):
                blocks.append({
                    "block_type": 5,
                    "heading3": {
                        "elements": [{"text_run": {"content": line[4:]}}]
                    }
                })
            # 普通文本
            else:
                blocks.append({
                    "block_type": 2,
                    "text": {
                        "elements": [{"text_run": {"content": line}}]
                    }
                })
        
        return blocks
    
    async def create_or_update_diary_document(self, user_id: str, date: str, title: str,
                                               content: str, images: List[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """创建或更新日记文档"""
        try:
            # 创建文档
            result = await self.create_document(title, content)

            if not result:
                logger.error("文档创建失败")
                return None

            document_id = result['document_id']

            # 设置文档权限，让用户可以编辑和删除
            token = await self._get_tenant_access_token()
            if token:
                await self._set_document_permission(document_id, user_id, token)

                # 如果有图片，插入图片
                if images and len(images) > 0:
                    await self._insert_images_to_document(document_id, images, token)

            logger.info("日记文档创建成功: " + document_id)
            return result

        except Exception as e:
            logger.error("创建日记文档异常: " + str(e))
            return None

    async def _set_document_permission(self, document_id: str, user_id: str, token: str) -> bool:
        """
        设置文档权限，让用户可以编辑和删除
        使用飞书权限API: POST /open-apis/drive/v1/permissions/{token}/members
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://open.feishu.cn/open-apis/drive/v1/permissions/{document_id}/members?type=docx&need_notification=false",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "member_type": "openid",
                        "member_id": user_id,
                        "perm": "full_access"  # 给用户完全访问权限（可编辑、可删除）
                    }
                )

                logger.info(f"设置文档权限响应: {response.status_code} - {response.text[:200]}")

                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 0:
                        logger.info(f"文档权限设置成功: {document_id} for user {user_id}")
                        return True
                    else:
                        logger.error(f"设置文档权限API错误: {result}")
                        return False
                else:
                    logger.error(f"设置文档权限请求失败: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"设置文档权限异常: {e}")
            return False
    
    async def delete_document(self, document_id: str) -> bool:
        """
        删除飞书文档
        使用飞书删除文件API: DELETE /open-apis/drive/v1/files/{file_token}?type=docx
        文档: https://open.feishu.cn/document/server-docs/docs/drive-v1/file/delete

        Args:
            document_id: 文档ID (file_token)

        Returns:
            是否删除成功
        """
        try:
            token = await self._get_tenant_access_token()
            if not token:
                logger.error("无法获取tenant_access_token")
                return False

            async with httpx.AsyncClient() as client:
                # 添加 type=docx 参数
                response = await client.delete(
                    f"https://open.feishu.cn/open-apis/drive/v1/files/{document_id}?type=docx",
                    headers={"Authorization": f"Bearer {token}"}
                )

                logger.info(f"删除文档API响应: {response.status_code} - {response.text[:500]}")

                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 0:
                        logger.info(f"文档删除成功: {document_id}")
                        return True
                    else:
                        logger.error(f"删除文档API错误: {result}")
                        return False
                else:
                    logger.error(f"删除文档请求失败: {response.status_code}, 响应: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"删除文档异常: {e}")
            return False
    
    async def _insert_images_to_document(self, document_id: str, images: List[Dict[str, Any]], token: str) -> bool:
        """
        插入图片到文档
        正确流程：1. 创建图片块 -> 2. 直接上传图片到该图片块
        """
        try:
            async with httpx.AsyncClient() as client:
                for img in images:
                    file_name = img.get('file_name', 'image.jpg')
                    image_key = img.get('image_key')
                    message_id = img.get('message_id')
                    
                    if not image_key or not message_id:
                        logger.warning(f"图片 {file_name} 缺少 image_key 或 message_id，跳过")
                        continue
                    
                    # 步骤1：创建图片块
                    logger.info(f"创建图片块: {file_name}")
                    block_response = await client.post(
                        f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{document_id}/children",
                        headers={"Authorization": "Bearer " + token},
                        json={
                            "children": [{
                                "block_type": 27,  # image block
                                "image": {}  # 空的image属性
                            }]
                        }
                    )
                    
                    logger.info(f"创建图片块响应: {block_response.status_code} - {block_response.text[:300]}")
                    
                    if block_response.status_code != 200:
                        logger.error(f"创建图片块失败: {block_response.status_code}, 响应: {block_response.text}")
                        continue
                    
                    block_result = block_response.json()
                    if block_result.get("code") != 0:
                        logger.error(f"创建图片块API错误: {block_result}")
                        continue
                    
                    block_id = block_result["data"]["children"][0]["block_id"]
                    logger.info(f"图片块创建成功: {block_id}")
                    
                    # 步骤2：下载图片（使用 message_id 和 image_key 作为 file_key）
                    logger.info(f"下载图片: message_id={message_id}, file_key={image_key}")
                    image_data = await self._download_image(message_id, image_key, token)
                    if not image_data:
                        logger.error(f"下载图片失败: {image_key}")
                        continue
                    
                    # 步骤3：上传图片到文档
                    logger.info(f"上传图片到文档: {document_id}")
                    file_token = await self._upload_image_to_document(document_id, image_data, file_name, token)
                    
                    if not file_token:
                        logger.error(f"图片上传失败: {file_name}")
                        continue
                    
                    # 步骤4：更新图片块，绑定 file_token
                    logger.info(f"更新图片块: {block_id} with file_token: {file_token}")
                    update_success = await self._update_image_block(document_id, block_id, file_token, token)
                    
                    if update_success:
                        logger.info(f"图片 {file_name} 插入成功")
                    else:
                        logger.error(f"图片 {file_name} 插入失败")
                    
            return True
            
        except Exception as e:
            logger.error(f"插入图片异常: {e}")
            return False
    
    async def _download_image(self, message_id: str, file_key: str, token: str) -> Optional[bytes]:
        """
        下载图片
        使用飞书获取消息资源API: GET /open-apis/im/v1/messages/{message_id}/resources/{file_key}?type=image
        文档: https://open.feishu.cn/document/server-docs/im-v1/message/get
        """
        try:
            # 对 message_id 和 file_key 进行 URL 编码
            encoded_message_id = quote(message_id, safe='')
            encoded_file_key = quote(file_key, safe='')
            
            # 添加 type=image 查询参数
            url = f"https://open.feishu.cn/open-apis/im/v1/messages/{encoded_message_id}/resources/{encoded_file_key}?type=image"
            logger.info(f"下载图片URL: {url}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=30.0
                )
                
                logger.info(f"下载图片API响应: {response.status_code}")
                
                if response.status_code == 200:
                    logger.info(f"图片下载成功: {len(response.content)} bytes")
                    return response.content
                else:
                    logger.error(f"下载图片失败: {response.status_code}, {response.text[:500]}")
                    return None
        except Exception as e:
            logger.error(f"下载图片异常: {e}")
            return None
    
    async def _upload_image_to_document(self, document_id: str, image_data: bytes, file_name: str, token: str) -> Optional[str]:
        """
        上传图片到文档
        返回 file_token，用于后续绑定到图片块
        """
        try:
            async with httpx.AsyncClient() as client:
                # 构建上传请求
                # parent_type: doc_image
                # parent_node: 文档ID (document_id)
                files = {
                    "file": (file_name, image_data, "image/jpeg"),
                    "file_name": (None, file_name),
                    "parent_type": (None, "doc_image"),
                    "parent_node": (None, document_id),
                    "size": (None, str(len(image_data)))
                }
                
                response = await client.post(
                    "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all",
                    headers={"Authorization": f"Bearer {token}"},
                    files=files,
                    timeout=60.0
                )
                
                logger.info(f"上传图片响应: {response.status_code} - {response.text[:500]}")
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 0:
                        file_token = result.get('data', {}).get('file_token')
                        logger.info(f"图片上传成功: {file_token}")
                        return file_token
                    else:
                        logger.error(f"上传图片API错误: {result}")
                        return None
                else:
                    logger.error(f"上传图片请求失败: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"上传图片异常: {e}")
            return None
    
    async def _update_image_block(self, document_id: str, block_id: str, file_token: str, token: str) -> bool:
        """
        更新图片块，绑定 file_token
        使用 batch_update 接口的 replace_image 操作
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/batch_update",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "requests": [
                            {
                                "block_id": block_id,
                                "replace_image": {
                                    "token": file_token
                                }
                            }
                        ]
                    }
                )
                
                logger.info(f"更新图片块响应: {response.status_code} - {response.text[:500]}")
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 0:
                        logger.info(f"图片块更新成功: {block_id}")
                        return True
                    else:
                        logger.error(f"更新图片块API错误: {result}")
                        return False
                else:
                    logger.error(f"更新图片块请求失败: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"更新图片块异常: {e}")
            return False


# 创建全局文档服务实例
feishu_doc_service = FeishuDocService()
