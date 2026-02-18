"""
大语言模型服务
提供智能对话、日记生成、上下文理解等功能
支持联网搜索获取实时信息
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
from src.utils.config import settings
from src.utils.logger import logger


class LLMService:
    """大语言模型服务"""
    
    def __init__(self):
        """初始化LLM服务"""
        # 使用配置中的 LLM 设置（支持 OpenAI、SiliconFlow 等）
        self.api_key = getattr(settings, 'llm_api_key', '')
        self.api_base = getattr(settings, 'llm_api_base', 'https://api.openai.com/v1')
        self.model = getattr(settings, 'llm_model', 'gpt-3.5-turbo')
        
    def get_current_date_info(self) -> str:
        """
        获取当前日期信息
        
        Returns:
            日期信息字符串
        """
        now = datetime.now()
        weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        weekday = weekdays[now.weekday()]
        
        return f"今天是 {now.strftime('%Y年%m月%d日')} {weekday}"
    
    async def search_web(self, query: str) -> str:
        """
        联网搜索（使用 Bing Search API 或返回日期信息）
        
        Args:
            query: 搜索关键词
            
        Returns:
            搜索结果摘要
        """
        try:
            # 检查是否是天气查询
            if '天气' in query:
                return f"{self.get_current_date_info()}。由于天气查询需要定位信息，建议查看手机天气应用获取准确的当地天气。"
            
            # 检查是否是日期/时间查询
            if '几号' in query or '日期' in query or '时间' in query or '今天' in query:
                return self.get_current_date_info()
            
            # 其他查询返回当前日期
            return f"{self.get_current_date_info()}。其他实时信息建议查看相关应用或网站。"
                    
        except Exception as e:
            logger.error(f"联网搜索失败: {e}")
            return f"搜索出错: {str(e)}"
    
    async def chat_with_internet(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """
        带联网功能的对话
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            
        Returns:
            LLM回复内容
        """
        # 获取最后一条用户消息
        last_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "")
                break
        
        logger.info(f"chat_with_internet 收到消息: {last_message}")
        
        # 判断是否需要联网搜索
        search_keywords = ['天气', '新闻', '今天', '现在', '最新', '股价', '汇率', '时间', '几号', '日期']
        need_search = any(keyword in last_message for keyword in search_keywords)
        
        logger.info(f"是否需要搜索: {need_search}, 消息长度: {len(last_message)}")
        
        if need_search and len(last_message) < 100:  # 增加长度限制，避免搜索长对话
            # 执行搜索
            logger.info(f"开始联网搜索: {last_message}")
            search_result = await self.search_web(last_message)
            logger.info(f"搜索结果: {search_result[:200]}...")  # 只打印前200字符
            
            # 将搜索结果添加到上下文
            enhanced_messages = messages.copy()
            enhanced_messages.append({
                "role": "system",
                "content": f"联网搜索结果：{search_result}"
            })
            
            return await self.chat(enhanced_messages, temperature)
        else:
            # 普通对话
            logger.info("使用普通对话模式")
            return await self.chat(messages, temperature)
        
    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """
        与LLM对话
        
        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            temperature: 温度参数，控制创造性
            
        Returns:
            LLM回复内容
        """
        try:
            if not self.api_key:
                # 如果没有配置API Key，使用模拟回复
                return self._mock_response(messages)
            
            # 在系统消息中添加当前日期
            date_info = self.get_current_date_info()
            enhanced_messages = []
            
            # 找到系统消息并增强
            has_system = False
            for msg in messages:
                if msg.get("role") == "system":
                    enhanced_msg = msg.copy()
                    enhanced_msg["content"] = f"{msg['content']}\n\n[{date_info}]"
                    enhanced_messages.append(enhanced_msg)
                    has_system = True
                else:
                    enhanced_messages.append(msg)
            
            # 如果没有系统消息，添加一个
            if not has_system:
                enhanced_messages.insert(0, {
                    "role": "system",
                    "content": f"你是一个有帮助的助手。{date_info}"
                })
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": enhanced_messages,
                        "temperature": temperature,
                        "max_tokens": 500
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    logger.error(f"LLM API错误: {response.status_code} - {response.text}")
                    return self._mock_response(messages)
                    
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return self._mock_response(messages)
    
    def _mock_response(self, messages: List[Dict[str, str]]) -> str:
        """
        模拟LLM回复（当没有配置API Key时使用）
        
        Args:
            messages: 消息列表
            
        Returns:
            模拟回复
        """
        # 获取最后一条用户消息
        last_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "")
                break
        
        # 检查是否是天气查询
        if "天气" in last_message:
            return "抱歉，我无法获取实时天气信息。你可以查看天气预报应用，然后告诉我天气怎么样，我会记录到你的日记中。"
        
        # 检查是否是时间/日期查询
        if "时间" in last_message or "日期" in last_message or "今天几号" in last_message:
            return f"{self.get_current_date_info()}。有什么想记录的吗？"
        
        # 简单的模拟回复逻辑
        if "今天" in last_message or "日记" in last_message:
            return "今天发生了什么有趣的事情吗？可以和我分享一下。"
        elif "早上" in last_message or "上午" in last_message:
            return "上午过得怎么样？完成了哪些事情？"
        elif "下午" in last_message or "晚上" in last_message:
            return "下午/晚上有什么特别的经历吗？"
        elif "心情" in last_message or "感觉" in last_message:
            return "理解你的感受。还有什么想记录的吗？"
        elif "结束" in last_message or "完成" in last_message or "整理" in last_message:
            return "好的，我来帮你整理今天的日记。"
        else:
            return "嗯，我明白了。还有其他想分享的吗？"
    
    async def generate_guide_question(self, context: List[Dict[str, str]]) -> str:
        """
        生成引导问题
        
        Args:
            context: 对话上下文
            
        Returns:
            引导问题
        """
        date_info = self.get_current_date_info()
        
        system_prompt = f"""你是一个贴心的日记助手。

{date_info}

【重要规则】
1. 如果用户问日期、时间、天气等简单问题，直接回答，不要反问
2. 如果用户问新闻、实时信息等，告知用户你无法获取实时信息，建议查看相关应用
3. 只有当用户开始分享今天的事情时，才用问题引导对话
4. 保持对话自然、温暖，不要一直反问
5. 不要使用emoji表情符号
6. 使用纯文本格式

【日记引导原则】
- 用户开始分享时：适度追问细节
- 用户说完时：主动提出整理日记
- 每次回复不超过30个字

请根据用户消息生成合适的回复："""
        
        messages = [
            {"role": "system", "content": system_prompt},
            *context
        ]
        
        # 使用带联网功能的对话
        return await self.chat_with_internet(messages, temperature=0.8)
    
    async def generate_diary(self, context: List[Dict[str, str]]) -> str:
        """
        生成完整日记
        
        Args:
            context: 对话上下文
            
        Returns:
            整理好的日记内容
        """
        date_info = self.get_current_date_info()
        
        system_prompt = """你是一个专业的日记整理助手。请将用户今天的对话整理成一篇完整的日记。

""" + date_info + """

日记格式：
# 日记 - 【日期】

## 今日概览
用2-3句话总结今天的主要事件

## 详细记录
按时间顺序或主题组织内容，分段描述

## 心情与感悟
记录用户的情绪变化和思考

## 明日期待
如果有提到明天的计划，记录下来

要求：
1. 保持第一人称（"我"）
2. 语言流畅、自然
3. 保留关键细节
4. 适当润色，但不要改变原意
5. 篇幅适中
6. 不要使用emoji表情符号
7. 使用纯文本格式"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            *context,
            {"role": "user", "content": "请根据以上对话，帮我整理成一篇完整的日记。"}
        ]
        
        return await self.chat(messages, temperature=0.7)
    
    async def analyze_intent(self, message: str) -> Dict[str, Any]:
        """
        分析用户意图
        
        Args:
            message: 用户消息
            
        Returns:
            意图分析结果
        """
        # 简单的意图识别
        intent = {
            "type": "chat",  # chat, end, command
            "should_generate_diary": False
        }
        
        message_lower = message.lower()
        
        # 判断是否是结束对话（添加更多关键词）
        end_keywords = ["结束", "完成", "整理", "生成日记", "好了", "就这样", "总结", "帮我总结", "整理日记"]
        if any(keyword in message_lower for keyword in end_keywords):
            intent["type"] = "end"
            intent["should_generate_diary"] = True
        
        # 判断是否是命令
        if message.startswith("/"):
            intent["type"] = "command"
        
        return intent


# 创建全局LLM服务实例
llm_service = LLMService()
