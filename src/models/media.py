"""
媒体文件数据模型
定义媒体文件相关的数据结构和操作
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import uuid4


class Media(BaseModel):
    """媒体文件模型"""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    diary_id: str
    file_name: str
    file_type: str  # image, video
    file_url: str
    upload_time: datetime = Field(default_factory=datetime.now)
    
    class Config:
        from_attributes = True


class MediaCreate(BaseModel):
    """创建媒体文件请求模型"""
    diary_id: str
    file_name: str
    file_type: str
    file_url: str


class MediaResponse(BaseModel):
    """媒体文件响应模型"""
    id: str
    diary_id: str
    file_name: str
    file_type: str
    file_url: str
    upload_time: datetime
