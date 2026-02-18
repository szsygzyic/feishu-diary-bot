"""
文字消息处理器
处理用户发送的文字消息，集成LLM智能对话功能
"""

import json
from typing import Dict, Any
from datetime import datetime
from .base_handler import BaseHandler
from src.services.llm_service import llm_service
from src.services.conversation_service import conversation_service
from src.services.message_service import message_service
from src.services.diary_service import diary_service
from src.services.media_process_service import media_process_service
from src.services.feishu_doc_service import feishu_doc_service
from uuid import uuid4


class TextHandler(BaseHandler):
    """文字消息处理器"""
    
    async def handle(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理文字消息
        
        Args:
            message: 飞书文字消息数据
            
        Returns:
            处理结果
        """
        try:
            self.logger.info("=== 开始处理文字消息 ===")
            
            # 提取用户信息
            user_info = self.extract_user_info(message)
            chat_info = self.extract_chat_info(message)
            user_id = user_info['open_id']
            
            # 解析消息内容
            content = json.loads(message.get("content", "{}"))
            text = content.get("text", "").strip()
            
            self.logger.info("收到文字消息: " + text)
            self.logger.info("用户: " + user_id)
            
            # 检查是否为命令
            if text.startswith("/"):
                return await self.handle_command(text, user_id, chat_info)
            
            # 分析用户意图
            intent = await llm_service.analyze_intent(text)
            
            # 如果是结束对话，生成日记
            if intent['should_generate_diary']:
                return await self.generate_diary(user_id, chat_info)
            
            # 正常对话流程
            # 1. 保存用户消息到上下文
            conversation_service.add_message(user_id, "user", text)
            
            # 2. 获取对话上下文
            context = conversation_service.get_context(user_id)
            
            # 3. 使用LLM生成回复
            reply = await llm_service.generate_guide_question(context)
            
            # 4. 保存助手回复到上下文
            conversation_service.add_message(user_id, "assistant", reply)
            
            # 5. 发送回复给用户
            await message_service.send_text_message(user_id, reply)
            
            return {
                "code": 0,
                "msg": "消息已处理",
                "data": {
                    "user_id": user_id,
                    "reply": reply
                }
            }
            
        except Exception as e:
            self.logger.error("处理文字消息时出错: " + str(e))
            return {"code": 1, "msg": "处理失败: " + str(e)}
    
    async def handle_command(self, text: str, user_id: str, chat_info: Dict[str, str]) -> Dict[str, Any]:
        """
        处理命令
        
        Args:
            text: 命令文本
            user_id: 用户ID
            chat_info: 聊天信息
            
        Returns:
            处理结果
        """
        command = text[1:].split()[0].lower()
        
        self.logger.info("执行命令: " + command)
        
        if command == "help":
            return await self.cmd_help(user_id)
        elif command == "query":
            return await self.cmd_query(user_id)
        elif command == "config":
            return await self.cmd_config(user_id, text)
        elif command == "diary":
            return await self.generate_diary(user_id, chat_info)
        elif command == "new":
            return await self.start_new_session(user_id)
        elif command == "delete":
            return await self.cmd_delete(user_id, text)
        elif command == "list":
            return await self.cmd_list(user_id)
        elif command == "cleantest":
            return await self.cmd_cleantest(user_id)
        else:
            return {"code": 1, "msg": "未知命令: " + command}
    
    async def generate_diary(self, user_id: str, chat_info: Dict[str, str]) -> Dict[str, Any]:
        """
        生成日记
        
        Args:
            user_id: 用户ID
            chat_info: 聊天信息
            
        Returns:
            处理结果
        """
        try:
            self.logger.info("开始生成日记: user_id=" + user_id)
            
            # 1. 获取对话上下文
            context = conversation_service.get_context(user_id)
            
            if len(context) <= 1:  # 只有系统消息，没有用户对话
                reply = "还没有记录今天的事情呢，先和我聊聊今天发生了什么吧~"
                await message_service.send_text_message(user_id, reply)
                return {"code": 0, "msg": reply}
            
            # 2. 使用LLM生成日记
            diary_content = await llm_service.generate_diary(context)
            
            # 3. 获取媒体文件
            media_files = conversation_service.get_media_files(user_id)
            
            # 4. 保存日记到数据库
            diary_id = str(uuid4())
            today = datetime.now().strftime("%Y-%m-%d")
            title = "日记 - " + today
            
            # 提取摘要（前100字）
            if len(diary_content) > 100:
                summary = diary_content[:100] + "..."
            else:
                summary = diary_content
            
            # 提取图片信息列表（用于飞书文档）- 包含 image_key
            image_info_list = [m for m in media_files if m.get("type") == "image"]

            # 提取图片URL列表（用于数据库保存）
            image_urls = [m.get("url") for m in media_files if m.get("type") == "image"]

            # 5. 清空媒体文件记录
            conversation_service.clear_media_files(user_id)

            # 6. 创建飞书文档（传入完整的图片信息，包含 image_key）
            doc_result = await feishu_doc_service.create_or_update_diary_document(
                user_id=user_id,
                date=today,
                title=title,
                content=diary_content,
                images=image_info_list
            )

            # 7. 保存日记到数据库（包含 document_id）
            document_id = doc_result.get("document_id") if doc_result else None
            save_success = diary_service.save_diary(
                diary_id=diary_id,
                user_id=user_id,
                title=title,
                content=diary_content,
                summary=summary,
                tags=["日记", today],
                images=image_urls,
                document_id=document_id
            )

            if save_success:
                self.logger.info("日记已保存: " + diary_id)
            else:
                self.logger.error("日记保存失败: " + diary_id)
            
            # 7. 构建回复消息（不使用f-string，避免解析错误）
            reply_lines = []
            reply_lines.append("今天的日记整理好了！")
            reply_lines.append("")
            
            if doc_result:
                reply_lines.append("已保存到飞书文档：" + doc_result['url'])
                reply_lines.append("")
            else:
                reply_lines.append("（飞书文档保存失败，请联系管理员）")
                reply_lines.append("")
            
            reply_lines.append(diary_content)
            
            if media_files:
                reply_lines.append("")
                reply_lines.append("媒体文件：" + str(len(media_files)) + " 个已保存")
            
            reply_lines.append("")
            reply_lines.append("提示：使用 /new 可以开始记录新的日记")
            
            reply = "\n".join(reply_lines)
            
            await message_service.send_text_message(user_id, reply)
            
            # 8. 关闭当前会话
            conversation_service.close_session(user_id)
            
            return {
                "code": 0,
                "msg": "日记生成成功",
                "data": {
                    "user_id": user_id,
                    "diary": diary_content
                }
            }
            
        except Exception as e:
            self.logger.error("生成日记失败: " + str(e))
            return {"code": 1, "msg": "生成日记失败: " + str(e)}
    
    async def start_new_session(self, user_id: str) -> Dict[str, Any]:
        """
        开始新的日记会话
        
        Args:
            user_id: 用户ID
            
        Returns:
            处理结果
        """
        # 关闭旧会话
        conversation_service.close_session(user_id)
        
        # 创建新会话
        session = conversation_service.get_or_create_session(user_id)
        
        # 发送欢迎消息
        reply = "让我们开始记录今天的故事吧！今天发生了什么有趣的事情吗？"
        await message_service.send_text_message(user_id, reply)
        
        # 保存助手消息
        conversation_service.add_message(user_id, "assistant", reply)
        
        return {
            "code": 0,
            "msg": "新会话已开始",
            "data": {"user_id": user_id}
        }
    
    async def cmd_help(self, user_id: str) -> Dict[str, Any]:
        """帮助命令"""
        help_text = """飞书日记机器人使用指南

记录日记：
直接发送文字或语音，我会引导你完成日记

可用命令：
/help - 显示帮助信息
/diary - 整理并生成今天的日记
/new - 开始新的日记记录
/list - 列出所有日记文档（带删除链接）
/query - 查询历史日记
/delete <文档ID> - 删除指定文档
/cleantest - 一键清除所有测试文档
/config - 配置个人设置

使用提示：
- 直接和我聊天，我会用简短的问题引导你
- 说完后发送 /diary 或说"整理日记"
- 支持文字、语音、图片、视频多种格式
- 所有日记会自动整理到飞书文档

删除文档：
- 使用 /cleantest 一键清除所有文档（最方便）
- 或使用 /list 查看所有文档，每条记录都附带删除命令
- 或直接发送 /delete <文档ID> 删除指定文档
- 删除的文档会进入回收站，可恢复"""
        
        await message_service.send_text_message(user_id, help_text)
        return {"code": 0, "msg": "帮助信息已发送"}
    
    async def cmd_query(self, user_id: str) -> Dict[str, Any]:
        """查询日记命令"""
        try:
            # 获取最近的5篇日记
            diaries = diary_service.get_diaries_by_user(user_id, limit=5)
            
            if not diaries:
                reply = "还没有日记记录呢，快开始记录第一篇日记吧！\n发送 /new 开始记录"
                await message_service.send_text_message(user_id, reply)
                return {"code": 0, "msg": "无日记记录"}
            
            # 构建日记列表
            reply_lines = ["最近的日记：", ""]
            for i, diary in enumerate(diaries, 1):
                date = diary['create_date']
                if len(diary['summary']) > 50:
                    summary = diary['summary'][:50] + "..."
                else:
                    summary = diary['summary']
                reply_lines.append(str(i) + ". " + date)
                reply_lines.append("   " + summary)
                reply_lines.append("")
            
            reply_lines.append("提示：发送 /diary 查看今天的日记")
            reply = "\n".join(reply_lines)
            
            await message_service.send_text_message(user_id, reply)
            return {"code": 0, "msg": "日记列表已发送"}
            
        except Exception as e:
            self.logger.error("查询日记失败: " + str(e))
            reply = "查询日记时出错，请稍后再试"
            await message_service.send_text_message(user_id, reply)
            return {"code": 1, "msg": "查询失败: " + str(e)}
    
    async def cmd_config(self, user_id: str, text: str) -> Dict[str, Any]:
        """配置命令"""
        reply = "配置功能开发中，敬请期待..."
        await message_service.send_text_message(user_id, reply)
        return {"code": 0, "msg": reply}

    async def cmd_list(self, user_id: str) -> Dict[str, Any]:
        """
        列出用户的所有日记文档
        """
        try:
            # 获取用户的日记列表
            diaries = diary_service.get_diaries_by_user(user_id, limit=20)

            if not diaries:
                reply = "还没有日记记录呢，快开始记录第一篇日记吧！\n发送 /new 开始记录"
                await message_service.send_text_message(user_id, reply)
                return {"code": 0, "msg": "无日记记录"}

            # 构建日记列表
            reply_lines = ["你的日记列表：", ""]

            for i, diary in enumerate(diaries, 1):
                date = diary.get('create_date', '未知日期')
                title = diary.get('title', '无标题')
                document_id = diary.get('document_id', '')

                # 显示摘要（前30字）
                summary = diary.get('summary', '')
                if len(summary) > 30:
                    summary = summary[:30] + "..."

                reply_lines.append(f"{i}. {date} - {title}")
                reply_lines.append(f"   摘要: {summary}")

                if document_id:
                    doc_url = f"https://www.feishu.cn/docx/{document_id}"
                    reply_lines.append(f"   文档: {doc_url}")
                    reply_lines.append(f"   删除: /delete {document_id}")
                else:
                    reply_lines.append(f"   文档: 未生成飞书文档")

                reply_lines.append("")

            reply_lines.append("提示：")
            reply_lines.append("- 点击文档链接查看完整日记")
            reply_lines.append("- 使用 /delete <文档ID> 删除指定文档")
            reply_lines.append("- 发送 /diary 查看今天的日记")

            reply = "\n".join(reply_lines)

            await message_service.send_text_message(user_id, reply)
            return {"code": 0, "msg": "日记列表已发送"}

        except Exception as e:
            self.logger.error(f"列出日记失败: {e}")
            reply = "获取日记列表时出错，请稍后再试"
            await message_service.send_text_message(user_id, reply)
            return {"code": 1, "msg": f"列出日记失败: {str(e)}"}

    async def cmd_cleantest(self, user_id: str) -> Dict[str, Any]:
        """
        清除所有测试文档
        一键删除用户的所有日记文档和数据库记录
        """
        try:
            # 获取用户的所有日记
            diaries = diary_service.get_diaries_by_user(user_id, limit=1000)

            if not diaries:
                reply = "没有需要清理的文档"
                await message_service.send_text_message(user_id, reply)
                return {"code": 0, "msg": "无文档需要清理"}

            total_count = len(diaries)
            doc_deleted_count = 0
            doc_failed_count = 0
            no_doc_count = 0

            # 发送开始清理的消息
            reply = f"开始清理，共 {total_count} 条日记记录..."
            await message_service.send_text_message(user_id, reply)

            # 遍历删除所有文档（飞书文档）
            for diary in diaries:
                document_id = diary.get('document_id')
                if document_id:
                    success = await feishu_doc_service.delete_document(document_id)
                    if success:
                        doc_deleted_count += 1
                    else:
                        doc_failed_count += 1
                else:
                    no_doc_count += 1

            # 删除数据库记录
            db_deleted_count = diary_service.delete_diaries_by_user(user_id)

            # 构建结果消息
            reply_lines = ["清理完成！", ""]
            reply_lines.append(f"总计日记记录: {total_count} 条")
            reply_lines.append(f"飞书文档删除: {doc_deleted_count} 个")
            reply_lines.append(f"飞书文档删除失败: {doc_failed_count} 个")
            reply_lines.append(f"无飞书文档的记录: {no_doc_count} 条")
            reply_lines.append(f"数据库记录清理: {db_deleted_count} 条")

            if doc_failed_count > 0:
                reply_lines.append("")
                reply_lines.append("部分飞书文档删除失败，请手动清理：")
                reply_lines.append("1. 打开飞书云文档")
                reply_lines.append("2. 进入'我的文档'或'与我共享'")
                reply_lines.append("3. 选中要删除的文档，右键删除")
                reply_lines.append("4. 或前往回收站彻底删除")

            reply_lines.append("")
            reply_lines.append("提示：")
            reply_lines.append("- 所有日记记录已从数据库清除")
            reply_lines.append("- 删除的飞书文档已进入回收站")
            reply_lines.append("- 发送 /list 确认清理结果")

            reply = "\n".join(reply_lines)
            await message_service.send_text_message(user_id, reply)

            self.logger.info(f"用户 {user_id} 清理完成: 总计{total_count}, 文档删除{doc_deleted_count}, 失败{doc_failed_count}, 数据库清理{db_deleted_count}")
            return {"code": 0, "msg": f"清理完成"}

        except Exception as e:
            self.logger.error(f"清理文档失败: {e}")
            reply = "清理文档时出错，请稍后再试"
            await message_service.send_text_message(user_id, reply)
            return {"code": 1, "msg": f"清理文档失败: {str(e)}"}

    async def cmd_delete(self, user_id: str, text: str) -> Dict[str, Any]:
        """
        删除文档命令
        用法: /delete <文档ID>
        """
        try:
            # 解析命令参数
            parts = text.split()
            if len(parts) < 2:
                reply = "请提供要删除的文档ID\n用法: /delete <文档ID>\n\n示例: /delete doxcn123456"
                await message_service.send_text_message(user_id, reply)
                return {"code": 1, "msg": "缺少文档ID"}

            document_id = parts[1].strip()

            # 验证文档ID格式
            if not document_id:
                reply = "文档ID不能为空"
                await message_service.send_text_message(user_id, reply)
                return {"code": 1, "msg": "文档ID为空"}

            self.logger.info(f"用户 {user_id} 请求删除文档: {document_id}")

            # 1. 调用删除文档API（飞书文档）
            doc_success = await feishu_doc_service.delete_document(document_id)

            # 2. 删除数据库中关联的日记记录
            diaries = diary_service.get_diaries_by_document_id(document_id)
            db_deleted_count = 0
            if diaries:
                for diary in diaries:
                    diary_id = diary.get('id')
                    if diary_id:
                        success = diary_service.delete_diary(diary_id)
                        if success:
                            db_deleted_count += 1
                            self.logger.info(f"数据库日记记录已删除: {diary_id}")

            # 构建回复消息
            if doc_success:
                reply_lines = ["文档删除成功！", ""]
                reply_lines.append(f"文档ID: {document_id}")
                if db_deleted_count > 0:
                    reply_lines.append(f"关联日记记录: 已删除 {db_deleted_count} 条")
                reply_lines.append("")
                reply_lines.append("注意：文档已进入回收站，如需彻底删除请前往飞书云文档回收站。")
                reply = "\n".join(reply_lines)
                await message_service.send_text_message(user_id, reply)
                return {"code": 0, "msg": "文档删除成功"}
            else:
                # 即使飞书文档删除失败，如果数据库记录删除了也告知用户
                if db_deleted_count > 0:
                    reply = f"数据库记录已清理 {db_deleted_count} 条，但飞书文档删除失败。\n文档ID: {document_id}\n请手动检查飞书文档。"
                else:
                    reply = f"文档删除失败，请检查文档ID是否正确，或稍后重试。\n文档ID: {document_id}"
                await message_service.send_text_message(user_id, reply)
                return {"code": 1, "msg": "文档删除失败"}

        except Exception as e:
            self.logger.error(f"删除文档命令失败: {e}")
            reply = "删除文档时出错，请稍后重试"
            await message_service.send_text_message(user_id, reply)
            return {"code": 1, "msg": f"删除文档失败: {str(e)}"}
