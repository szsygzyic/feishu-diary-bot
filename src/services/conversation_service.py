"""
对话上下文管理服务
管理用户的对话历史和状态
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.utils.database import db
from src.utils.logger import logger


class ConversationService:
    """对话上下文管理服务"""
    
    def __init__(self):
        """初始化对话服务"""
        self._init_table()
    
    def _init_table(self):
        """初始化对话记录表"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                # 检查表是否存在
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversation'")
                table_exists = cursor.fetchone()
                
                if not table_exists:
                    # 创建新表
                    cursor.execute("""
                        CREATE TABLE conversation (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id TEXT NOT NULL,
                            session_date TEXT NOT NULL,
                            messages TEXT NOT NULL,
                            media_files TEXT DEFAULT '[]',
                            status TEXT DEFAULT 'active',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                else:
                    # 检查是否需要添加 media_files 列
                    cursor.execute("PRAGMA table_info(conversation)")
                    columns = [col[1] for col in cursor.fetchall()]
                    
                    if 'media_files' not in columns:
                        cursor.execute("ALTER TABLE conversation ADD COLUMN media_files TEXT DEFAULT '[]'")
                
                conn.commit()
                logger.info("对话记录表初始化完成")
        except Exception as e:
            logger.error(f"初始化对话表失败: {e}")
    
    def get_or_create_session(self, user_id: str) -> Dict[str, Any]:
        """
        获取或创建今天的对话会话
        
        Args:
            user_id: 用户ID
            
        Returns:
            会话信息
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        try:
            # 查询今天的会话
            result = db.fetch_one(
                "SELECT * FROM conversation WHERE user_id = ? AND session_date = ? AND status = 'active'",
                (user_id, today)
            )
            
            if result:
                # 检查会话是否过期（超过24小时）
                updated_at = datetime.fromisoformat(result['updated_at'])
                if datetime.now() - updated_at > timedelta(hours=24):
                    # 关闭旧会话
                    self.close_session(user_id)
                    # 创建新会话
                    return self._create_new_session(user_id, today)
                
                # 返回现有会话
                return {
                    "id": result['id'],
                    "user_id": result['user_id'],
                    "session_date": result['session_date'],
                    "messages": json.loads(result['messages']),
                    "media_files": json.loads(result.get('media_files', '[]')),
                    "status": result['status']
                }
            else:
                # 创建新会话
                return self._create_new_session(user_id, today)
                
        except Exception as e:
            logger.error(f"获取会话失败: {e}")
            return self._create_new_session(user_id, today)
    
    def _create_new_session(self, user_id: str, session_date: str) -> Dict[str, Any]:
        """
        创建新会话
        
        Args:
            user_id: 用户ID
            session_date: 会话日期
            
        Returns:
            新会话信息
        """
        # 初始化系统消息
        initial_messages = [
            {
                "role": "system",
                "content": "你是一个贴心的日记助手。帮助用户记录今天的事情，用简短的问题引导对话，适度追问细节，最后整理成完整的日记。"
            }
        ]
        
        initial_media = []
        
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO conversation (user_id, session_date, messages, media_files, status) VALUES (?, ?, ?, ?, 'active')",
                    (user_id, session_date, json.dumps(initial_messages), json.dumps(initial_media))
                )
                conn.commit()
                session_id = cursor.lastrowid
                
                logger.info(f"创建新会话: user_id={user_id}, session_id={session_id}")
                
                return {
                    "id": session_id,
                    "user_id": user_id,
                    "session_date": session_date,
                    "messages": initial_messages,
                    "media_files": initial_media,
                    "status": "active"
                }
        except Exception as e:
            logger.error(f"创建会话失败: {e}")
            return {
                "id": None,
                "user_id": user_id,
                "session_date": session_date,
                "messages": initial_messages,
                "media_files": initial_media,
                "status": "active"
            }
    
    def add_message(self, user_id: str, role: str, content: str) -> bool:
        """
        添加消息到会话
        
        Args:
            user_id: 用户ID
            role: 消息角色 (user/assistant/system)
            content: 消息内容
            
        Returns:
            是否成功
        """
        try:
            session = self.get_or_create_session(user_id)
            messages = session['messages']
            
            # 添加新消息
            messages.append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            })
            
            # 只保留最近20条消息（避免过长）
            if len(messages) > 20:
                # 保留系统消息和最近的消息
                system_messages = [m for m in messages if m['role'] == 'system']
                other_messages = [m for m in messages if m['role'] != 'system'][-18:]
                messages = system_messages + other_messages
            
            # 更新数据库
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE conversation SET messages = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (json.dumps(messages), session['id'])
                )
                conn.commit()
            
            logger.info(f"添加消息: user_id={user_id}, role={role}")
            return True
            
        except Exception as e:
            logger.error(f"添加消息失败: {e}")
            return False
    
    def add_media_to_context(self, user_id: str, media_info: Dict[str, Any]) -> bool:
        """
        添加媒体信息到会话上下文
        
        Args:
            user_id: 用户ID
            media_info: 媒体信息
            
        Returns:
            是否成功
        """
        try:
            session = self.get_or_create_session(user_id)
            media_files = session['media_files']
            
            # 添加媒体信息
            media_info['added_at'] = datetime.now().isoformat()
            media_files.append(media_info)
            
            # 更新数据库
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE conversation SET media_files = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (json.dumps(media_files), session['id'])
                )
                conn.commit()
            
            logger.info(f"添加媒体信息: user_id={user_id}, type={media_info.get('type')}")
            return True
            
        except Exception as e:
            logger.error(f"添加媒体信息失败: {e}")
            return False
    
    def get_media_files(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取会话中的所有媒体文件
        
        Args:
            user_id: 用户ID
            
        Returns:
            媒体文件列表
        """
        session = self.get_or_create_session(user_id)
        return session.get('media_files', [])
    
    def clear_media_files(self, user_id: str) -> bool:
        """
        清空会话中的媒体文件（生成日记后调用）
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否成功
        """
        try:
            session = self.get_or_create_session(user_id)
            
            # 更新数据库
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE conversation SET media_files = '[]', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (session['id'],)
                )
                conn.commit()
            
            logger.info(f"清空媒体文件: user_id={user_id}")
            return True
            
        except Exception as e:
            logger.error(f"清空媒体文件失败: {e}")
            return False
    
    def get_context(self, user_id: str) -> List[Dict[str, str]]:
        """
        获取对话上下文（用于LLM）
        
        Args:
            user_id: 用户ID
            
        Returns:
            消息列表
        """
        session = self.get_or_create_session(user_id)
        messages = session['messages']
        
        # 转换为LLM需要的格式（去掉timestamp）
        context = []
        for msg in messages:
            context.append({
                "role": msg['role'],
                "content": msg['content']
            })
        
        return context
    
    def close_session(self, user_id: str) -> bool:
        """
        关闭会话
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否成功
        """
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            db.execute(
                "UPDATE conversation SET status = 'closed' WHERE user_id = ? AND session_date = ? AND status = 'active'",
                (user_id, today)
            )
            logger.info(f"关闭会话: user_id={user_id}")
            return True
        except Exception as e:
            logger.error(f"关闭会话失败: {e}")
            return False
    
    def get_today_diary_data(self, user_id: str) -> str:
        """
        获取今天的日记原始数据
        
        Args:
            user_id: 用户ID
            
        Returns:
            日记内容文本
        """
        context = self.get_context(user_id)
        
        # 提取用户和助手的对话
        diary_lines = []
        for msg in context:
            if msg['role'] == 'user':
                diary_lines.append(f"我: {msg['content']}")
            elif msg['role'] == 'assistant':
                diary_lines.append(f"助手: {msg['content']}")
        
        return "\n".join(diary_lines)


# 创建全局对话服务实例
conversation_service = ConversationService()
