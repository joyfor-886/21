"""裁衡 (Caiheng) - CEO 视角产品审查专家

以投资人/CEO 的视角审查产品方案的商业可行性和产品价值。
"""

from typing import Dict, Any
from core.skill_registry import Skill, SkillResult
from core.llm_factory import LLMFactory
from domain.enums import WORKFLOW_SYSTEM_PROMPTS

CEO_REVIEW_SYSTEM_PROMPT = WORKFLOW_SYSTEM_PROMPTS.get("caiheng", "")


class CEOReviewSkill(Skill):
    """CEO 视角 —— 审查产品价值和商业可行性"""

    name = "caiheng"
    description = "裁衡 - CEO视角审视产品价值，挑战假设"
    trigger = "产品定义"

    async def run(self, conversation: str, context: Dict[str, Any] = None) -> SkillResult:
        try:
            provider = LLMFactory.get_provider()
        except Exception:
            return SkillResult(
                response=self._fallback_response(),
                stage="caiheng",
            )

        # 构建上下文增强的 prompt
        context = context or {}
        artifact_context = context.get("artifact_context", "")

        enhanced_prompt = CEO_REVIEW_SYSTEM_PROMPT

        if artifact_context:
            enhanced_prompt += f"\n\n【前序阶段成果参考】\n{artifact_context}"

        messages = self.build_chat_messages(enhanced_prompt, conversation, context)

        try:
            response = await provider.chat(messages, max_tokens=2048, temperature=0.5)
        except Exception:
            response = self._fallback_response()

        return SkillResult(
            response=response,
            stage="caiheng",
        )

    def _fallback_response(self) -> str:
        return (
            "⚠️ AI 服务暂时不可用，无法完成 CEO 视角审查。\n\n"
            "以下是一些通用的审查要点供您自行检查：\n"
            "1. 核心问题是否明确？解决方案是否切中痛点？\n"
            "2. 是否存在范围蔓延的风险？\n"
            "3. 成功指标是否可量化？\n"
            "4. 是否考虑了沉默失败模式？\n"
            "5. 错误处理是否完善？\n\n"
            "请在 AI 服务恢复后重新进行审查。"
        )
