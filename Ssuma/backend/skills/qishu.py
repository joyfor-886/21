"""
枢墨启枢技能 (qishu.py)
启枢 - 追问澄清，通过 LLM 动态生成情境追问来澄清需求

核心原则：
1. 所有追问由 LLM 根据用户输入动态生成，不用硬编码选项
2. 一次只问一个问题
3. 追问必须贴合用户的具体项目场景
4. 如果用户已经说得清楚，直接总结确认
"""

from typing import Dict, Any, List, Optional
from core.skill_registry import Skill, SkillResult
from core.llm_factory import LLMFactory
from domain.enums import WORKFLOW_SYSTEM_PROMPTS
import json
import logging

logger = logging.getLogger('Ssuma.Qishu')

QISHU_SYSTEM_PROMPT = WORKFLOW_SYSTEM_PROMPTS["qishu"]


class BrainstormingSkill(Skill):
    """
    启枢技能 - 追问澄清专家（LLM 动态追问版）

    工作流程：
    1. 将用户输入 + 系统提示词交给 LLM
    2. LLM 根据用户具体项目动态生成追问和选项
    3. 每轮对话 LLM 都能看到完整上下文，自适应调整追问策略
    """

    name = "qishu"
    description = "启枢 - 追问澄清，通过情境追问澄清需求"
    trigger = "我想做"

    def __init__(self):
        super().__init__()
        self.max_turns = 3

    async def run(self, conversation: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            provider = LLMFactory.get_provider()
        except Exception as e:
            logger.error(f"Failed to get LLM provider: {e}")
            return SkillResult(
                response="抱歉，AI 服务暂时不可用，请检查模型配置后重试。",
                stage="qishu",
            )

        messages = self._build_messages(conversation, context)

        try:
            response = await provider.chat(
                messages=messages,
                max_tokens=800,
                temperature=0.7,
            )
            response = self._ensure_format(response)
        except Exception as e:
            logger.error(f"Qishu LLM call failed: {e}")
            response = self._fallback_response(conversation)

        return SkillResult(
            response=response,
            stage="qishu",
            metadata={"max_turns": self.max_turns},
        )

    def _build_messages(self, conversation: str, context: Dict[str, Any] = None) -> List[Dict[str, str]]:
        return self.build_chat_messages(QISHU_SYSTEM_PROMPT, conversation, context)

    def _ensure_format(self, response: str) -> str:
        """确保响应格式完整"""
        # 如果 LLM 没有加"或者直接告诉我"，补上
        if "或者直接告诉我" not in response and "💡" not in response[-50:]:
            response += "\n\n💡 或者直接告诉我你的想法"

        return response

    def _fallback_response(self, user_input: str) -> str:
        """LLM 不可用时的降级响应"""
        return (
            f"我理解你想做的项目。为了更好地帮助你，请告诉我更多细节：\n\n"
            f"1. 这个项目主要给谁用？\n"
            f"2. 最核心的功能是什么？\n"
            f"3. 有没有类似的参考产品？\n\n"
            f"💡 或者直接告诉我你的想法"
        )
