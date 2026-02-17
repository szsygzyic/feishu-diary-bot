"""
日记数据模型
定义日记相关的数据结构和操作
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import uuid4


class Diary(BaseModel):
    """日记模型"""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    content: str
    create_time: datetime = Field(default_factory=datetime.now)
    update_time: datetime = Field(default_factory=datetime.now)
    category: Optional[str] = None
    document_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class DiaryCreate(BaseModel):
    """创建日记请求模型"""
    user_id: str
    content: str
    category: Optional[str] = None


class DiaryUpdate(BaseModel):
    """更新日记请求模型"""
    content: Optional[str] = None
    category: Optional[str] = None
    document_url: Optional[str] = None


class DiaryResponse(BaseModel):
    """日记响应模型"""
    id: str
    user_id: str
    content: str
    create_time: datetime
    category: Optional[str] = None
    document_url: Optional[str] = None
