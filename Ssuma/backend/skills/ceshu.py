"""策书 (Ceshu) - 执行计划拆解专家

将高层方案拆解为 AI IDE 可逐条执行的 TDD 任务序列。
"""

from typing import Dict, Any
from core.skill_registry import Skill, SkillResult
from core.llm_factory import LLMFactory
from domain.enums import WORKFLOW_SYSTEM_PROMPTS

PLAN_WRITING_SYSTEM_PROMPT = WORKFLOW_SYSTEM_PROMPTS.get("ceshu", "")


class PlanWritingSkill(Skill):
    """策书 —— 将方案拆解为可执行的 TDD 实施计划"""

    name = "ceshu"
    description = "策书 - 将方案拆解为可执行的实施计划"
    trigger = "实施计划"

    async def run(self, conversation: str, context: Dict[str, Any] = None) -> SkillResult:
        try:
            provider = LLMFactory.get_provider()
        except Exception:
            return SkillResult(
                response=self._fallback_response(),
                stage="ceshu",
            )

        context = context or {}
        artifact_context = context.get("artifact_context", "")

        enhanced_prompt = PLAN_WRITING_SYSTEM_PROMPT

        if artifact_context:
            enhanced_prompt += f"\n\n【前序阶段成果】\n{artifact_context}"

        # 如果有已生成的技术 spec，附加上去
        generated_spec = context.get("generated_spec", "")
        if generated_spec:
            enhanced_prompt += f"\n\n【已生成的技术方案】\n{generated_spec[:3000]}"

        messages = self.build_chat_messages(enhanced_prompt, conversation, context)

        try:
            # 执行计划需要较大的 token 预算来输出完整的任务列表
            response = await provider.chat(messages, max_tokens=4096, temperature=0.3)
        except Exception:
            response = self._fallback_response()

        return SkillResult(
            response=response,
            stage="ceshu",
        )

    def _fallback_response(self) -> str:
        return (
            "⚠️ AI 服务暂时不可用，无法生成执行计划。\n\n"
            "建议您按以下步骤自行拆解：\n"
            "1. 将方案按功能模块拆分为独立任务\n"
            "2. 每个任务控制在 2-5 分钟可完成\n"
            "3. 先写失败测试，再写实现代码\n"
            "4. 每完成一个任务进行 Git commit\n"
            "5. 确保每个任务有明确的验证步骤\n\n"
            "请在 AI 服务恢复后重新生成计划。"
        )
