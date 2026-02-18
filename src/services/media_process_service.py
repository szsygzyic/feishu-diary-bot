"""
媒体处理服务
在生成日记时下载图片并上传到飞书文档
"""

import httpx
from typing import List, Dict, Any, Optional
from src.utils.config import settings
from src.utils.logger import logger


class MediaProcessService:
    """媒体处理服务"""
    
    async def download_image(self, image_key: str, access_token: str) -> Optional[bytes]:
        """
        下载图片
        使用飞书图片下载API: GET /open-apis/im/v1/images/{image_key}
        文档: https://open.feishu.cn/document/server-docs/docs/im-v1/image/get
        
        Args:
            image_key: 图片key
            access_token: 飞书访问令牌
            
        Returns:
            图片二进制数据
        """
        try:
            async with httpx.AsyncClient() as client:
                # 直接下载图片
                response = await client.get(
                    f"https://open.feishu.cn/open-apis/im/v1/images/{image_key}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=30.0
                )
                
                logger.info(f"下载图片API响应: {response.status_code}")
                
                if response.status_code == 200:
                    logger.info(f"图片下载成功: {len(response.content)} bytes")
                    return response.content
                else:
                    logger.error(f"图片下载失败: {response.status_code}, 响应: {response.text[:200]}")
                    return None
                    
        except Exception as e:
            logger.error(f"下载图片异常: {e}")
            return None
    
    async def upload_image_to_document(self, image_data: bytes, file_name: str, access_token: str) -> Optional[str]:
        """
        上传图片到飞书文档
        
        Args:
            image_data: 图片二进制数据
            file_name: 文件名
            access_token: 飞书访问令牌
            
        Returns:
            上传后的图片URL
        """
        try:
            # 先上传图片素材
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://open.feishu.cn/open-apis/im/v1/images",
                    headers={"Authorization": f"Bearer {access_token}"},
                    files={"image": (file_name, image_data, "image/jpeg")},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 0:
                        image_key = result["data"]["image_key"]
                        logger.info(f"图片上传成功: {image_key}")
                        return image_key
                    else:
                        logger.error(f"图片上传失败: {result}")
                        return None
                else:
                    logger.error(f"图片上传请求失败: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"上传图片异常: {e}")
            return None
    
    async def process_media_for_diary(self, media_list: List[Dict[str, Any]], access_token: str) -> List[Dict[str, Any]]:
        """
        处理日记中的所有媒体文件
        简化方案：直接使用原有的 image_key，不再下载上传
        
        Args:
            media_list: 媒体文件列表
            access_token: 飞书访问令牌
            
        Returns:
            处理后的媒体列表
        """
        processed_media = []
        
        for media in media_list:
            if media.get("type") == "image":
                image_key = media.get("image_key")
                file_name = media.get("file_name", "image.jpg")
                
                if not image_key:
                    logger.error("图片没有 image_key")
                    processed_media.append({
                        **media,
                        "status": "no_image_key"
                    })
                    continue
                
                logger.info(f"处理图片: {file_name}, image_key: {image_key}")
                
                # 下载图片
                image_data = await self.download_image(image_key, access_token)
                
                if image_data:
                    # 上传到飞书文档获取 file_token
                    file_token = await self.upload_image_to_document(image_data, file_name, access_token)
                    
                    if file_token:
                        processed_media.append({
                            "type": "image",
                            "file_name": file_name,
                            "image_key": image_key,
                            "file_token": file_token,
                            "status": "uploaded"
                        })
                    else:
                        processed_media.append({
                            **media,
                            "status": "upload_failed"
                        })
                else:
                    processed_media.append({
                        **media,
                        "status": "download_failed"
                    })
            else:
                # 其他类型直接保留
                processed_media.append(media)
        
        return processed_media


# 创建全局媒体处理服务实例
media_process_service = MediaProcessService()
