from typing import Dict, Any
from core.skill_registry import Skill, SkillResult
from core.llm_factory import LLMFactory

AUTOPLAN_SYSTEM_PROMPT = """你是 Ssuma 的自动化流水线 (Autoplan)。
你的任务是根据用户的初始意图，自动调度其他 AI 角色（CEO、设计、工程、计划专家），生成一份极其完整的项目方案。

【自动规划流程】
当你被触发时，你需要阅读之前的对话，并输出一份总体架构方向，然后说明你将如何引导整个工作流：
1. 提取并确认核心目标。
2. 说明你已经预先思考了哪些 CEO 维度的边界问题。
3. 说明技术架构的初步方向。
4. 提示用户："接下来，系统将自动依次进行深入的 CEO 审核、技术架构细化和执行计划拆解。是否允许继续？"

你不需要生成所有细节，你的角色是一个 Orchestrator（协调者），让用户确认自动流水线的开启。"""

class AutoPlanSkill(Skill):
    name = "autoplan"
    description = "自动规划流水线：一键触发完整的评审流"
    trigger = "自动规划"

    async def run(self, conversation: str, context: Dict[str, Any] = None) -> SkillResult:
        try:
            provider = LLMFactory.get_provider()
        except Exception:
            return SkillResult(
                response=self._fallback_response(),
                stage="autoplan",
            )

        messages = self.build_chat_messages(AUTOPLAN_SYSTEM_PROMPT, conversation, context)

        try:
            response = await provider.chat(messages, max_tokens=1500, temperature=0.7)
        except Exception:
            response = self._fallback_response()

        return SkillResult(
            response=response,
            stage="autoplan",
        )

    def _fallback_response(self) -> str:
        return (
            "⚠️ AI 服务暂时不可用，无法启动自动规划流水线。\n\n"
            "您可以手动按以下顺序推进：\n"
            "1. 启枢 — 明确需求\n"
            "2. 裁衡 — CEO视角审视\n"
            "3. 甄微 — 技术架构评审\n"
            "4. 策书 — 执行计划拆解\n"
            "5. 凝墨 — 生成完整方案\n\n"
            "请在 AI 服务恢复后重新启动。"
        )
