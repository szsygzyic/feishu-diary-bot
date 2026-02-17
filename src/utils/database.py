"""
数据库管理模块
管理SQLite数据库连接和操作
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from .config import settings
from .logger import logger


class Database:
    """数据库管理类"""
    
    def __init__(self, db_url: str = None):
        """
        初始化数据库连接
        
        Args:
            db_url: 数据库连接URL，默认使用配置中的URL
        """
        self.db_url = db_url or settings.database_url
        self.db_path = self._parse_db_path()
        self._init_db()
    
    def _parse_db_path(self) -> str:
        """解析数据库文件路径"""
        if self.db_url.startswith("sqlite:///"):
            return self.db_url.replace("sqlite:///", "")
        return self.db_url
    
    def _init_db(self):
        """初始化数据库，创建必要的表"""
        # 确保数据库目录存在
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建日记表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS diary (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    category TEXT,
                    document_url TEXT
                )
            """)
            
            # 创建媒体文件表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS media (
                    id TEXT PRIMARY KEY,
                    diary_id TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_url TEXT NOT NULL,
                    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (diary_id) REFERENCES diary(id)
                )
            """)
            
            # 创建用户配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_config (
                    user_id TEXT PRIMARY KEY,
                    template TEXT,
                    document_structure TEXT,
                    preferences TEXT,
                    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("数据库初始化完成")
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def execute(self, query: str, params: tuple = ()) -> int:
        """
        执行SQL语句
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            影响的行数
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """
        查询单条记录
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果字典，如果没有则返回None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        查询多条记录
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]


# 创建全局数据库实例
db = Database()
