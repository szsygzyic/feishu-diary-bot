"""
日记服务
管理日记的保存、查询、更新等操作
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.utils.database import db
from src.utils.logger import logger


class DiaryService:
    """日记服务"""
    
    def __init__(self):
        """初始化日记服务"""
        self._init_table()
    
    def _init_table(self):
        """初始化日记表"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS diaries (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        title TEXT,
                        content TEXT NOT NULL,
                        summary TEXT,
                        mood TEXT,
                        weather TEXT,
                        location TEXT,
                        tags TEXT,
                        images TEXT,
                        document_id TEXT,
                        create_date TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                logger.info("日记表初始化完成")
        except Exception as e:
            logger.error(f"初始化日记表失败: {e}")
    
    def save_diary(self, diary_id: str, user_id: str, title: str, content: str,
                   summary: str = "", mood: str = "", weather: str = "",
                   location: str = "", tags: List[str] = None, images: List[str] = None,
                   document_id: str = None) -> bool:
        """
        保存日记

        Args:
            diary_id: 日记ID
            user_id: 用户ID
            title: 标题
            content: 内容
            summary: 摘要
            mood: 心情
            weather: 天气
            location: 地点
            tags: 标签列表
            images: 图片URL列表
            document_id: 飞书文档ID

        Returns:
            是否成功
        """
        try:
            today = datetime.now().strftime("%Y-%m-%d")

            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO diaries
                    (id, user_id, title, content, summary, mood, weather, location, tags, images, document_id, create_date, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    diary_id, user_id, title, content, summary, mood, weather, location,
                    json.dumps(tags or []), json.dumps(images or []), document_id, today
                ))
                conn.commit()

                logger.info(f"日记保存成功: {diary_id}")
                return True

        except Exception as e:
            logger.error(f"保存日记失败: {e}")
            return False
    
    def get_diary_by_id(self, diary_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取日记
        
        Args:
            diary_id: 日记ID
            
        Returns:
            日记信息
        """
        try:
            result = db.fetch_one(
                "SELECT * FROM diaries WHERE id = ?",
                (diary_id,)
            )
            
            if result:
                return self._format_diary(result)
            return None
            
        except Exception as e:
            logger.error(f"获取日记失败: {e}")
            return None
    
    def get_diaries_by_user(self, user_id: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取用户的日记列表
        
        Args:
            user_id: 用户ID
            limit: 数量限制
            offset: 偏移量
            
        Returns:
            日记列表
        """
        try:
            results = db.fetch_all(
                "SELECT * FROM diaries WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (user_id, limit, offset)
            )
            
            return [self._format_diary(r) for r in results]
            
        except Exception as e:
            logger.error(f"获取日记列表失败: {e}")
            return []
    
    def get_diaries_by_date(self, user_id: str, date: str) -> List[Dict[str, Any]]:
        """
        获取指定日期的日记
        
        Args:
            user_id: 用户ID
            date: 日期 (YYYY-MM-DD)
            
        Returns:
            日记列表
        """
        try:
            results = db.fetch_all(
                "SELECT * FROM diaries WHERE user_id = ? AND create_date = ? ORDER BY created_at DESC",
                (user_id, date)
            )
            
            return [self._format_diary(r) for r in results]
            
        except Exception as e:
            logger.error(f"获取日期日记失败: {e}")
            return []
    
    def get_today_diary(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取今天的日记

        Args:
            user_id: 用户ID

        Returns:
            日记信息
        """
        today = datetime.now().strftime("%Y-%m-%d")
        diaries = self.get_diaries_by_date(user_id, today)
        return diaries[0] if diaries else None

    def get_diaries_by_document_id(self, document_id: str) -> List[Dict[str, Any]]:
        """
        根据文档ID获取日记

        Args:
            document_id: 飞书文档ID

        Returns:
            日记列表
        """
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM diaries WHERE document_id = ?",
                    (document_id,)
                )
                results = cursor.fetchall()

                # 获取列名
                columns = [description[0] for description in cursor.description]

                # 转换为字典列表
                diaries = []
                for row in results:
                    diary = dict(zip(columns, row))
                    diaries.append(self._format_diary(diary))

                return diaries

        except Exception as e:
            logger.error(f"根据文档ID获取日记失败: {e}")
            return []

    def delete_diary(self, diary_id: str) -> bool:
        """
        删除日记
        
        Args:
            diary_id: 日记ID
            
        Returns:
            是否成功
        """
        try:
            db.execute(
                "DELETE FROM diaries WHERE id = ?",
                (diary_id,)
            )
            logger.info(f"日记删除成功: {diary_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除日记失败: {e}")
            return False
    
    def _format_diary(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化日记数据

        Args:
            row: 数据库行

        Returns:
            格式化后的日记
        """
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "title": row["title"],
            "content": row["content"],
            "summary": row["summary"],
            "mood": row["mood"],
            "weather": row["weather"],
            "location": row["location"],
            "tags": json.loads(row["tags"]) if row["tags"] else [],
            "images": json.loads(row["images"]) if row["images"] else [],
            "document_id": row.get("document_id", ""),
            "create_date": row["create_date"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }

    def delete_diary(self, diary_id: str) -> bool:
        """
        删除日记

        Args:
            diary_id: 日记ID

        Returns:
            是否成功
        """
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM diaries WHERE id = ?", (diary_id,))
                conn.commit()

                if cursor.rowcount > 0:
                    logger.info(f"日记删除成功: {diary_id}")
                    return True
                else:
                    logger.warning(f"日记不存在: {diary_id}")
                    return False

        except Exception as e:
            logger.error(f"删除日记失败: {e}")
            return False

    def delete_diaries_by_user(self, user_id: str) -> int:
        """
        删除用户的所有日记

        Args:
            user_id: 用户ID

        Returns:
            删除的日记数量
        """
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM diaries WHERE user_id = ?", (user_id,))
                conn.commit()

                deleted_count = cursor.rowcount
                logger.info(f"用户 {user_id} 的日记已清空，共删除 {deleted_count} 条")
                return deleted_count

        except Exception as e:
            logger.error(f"清空用户日记失败: {e}")
            return 0


# 创建全局日记服务实例
diary_service = DiaryService()
