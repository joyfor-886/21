"""自动规划 (AutoPlan) - 一键触发完整评审流水线

现在委托给 AutoPilotService 执行，避免功能重复。
"""

from typing import Dict, Any
from core.skill_registry import Skill, SkillResult
from core.llm_factory import LLMFactory
from domain.enums import WORKFLOW_SYSTEM_PROMPTS

AUTOPLAN_SYSTEM_PROMPT = WORKFLOW_SYSTEM_PROMPTS.get("autoplan", """你是 Ssuma 的自动化流水线协调者。基于用户意图快速评估项目范围并自动调度审查流程。

工作方式：
1. 提取并确认核心目标
2. 预判 CEO 维度边界问题
3. 预判技术架构方向
4. 提示系统将自动依次深入评审

简洁、果断。""")


class AutoPlanSkill(Skill):
    """自动规划 —— 触发完整流水线

    当用户触发此技能时，返回流水线确认信息。
    实际的全自动流水线执行由 AutoPilotService 负责（通过 API 调用）。
    """

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
            response = await provider.chat(messages, max_tokens=1024, temperature=0.7)
        except Exception:
            response = self._fallback_response()

        # 在回复末尾添加流水线启动提示
        response += (
            "\n\n---\n"
            "💡 **自动流水线已就绪**\n\n"
            "接下来系统将自动依次执行：\n"
            "1. 启枢（追问澄清）→ 2. 裁衡（价值审视）→ 3. 甄微（技术评审）\n"
            "→ 4. 策书（任务规划）→ 5. 凝墨（方案整合）→ 6. 破妄（覆盖验证）\n"
            "→ 7. 渐衍（分阶段生成）\n\n"
            "全部完成后自动导出 AI IDE 可执行文件。\n\n"
            "点击右下角 **⚡ Auto-Pilot** 按钮一键启动，或继续对话手动推进。"
        )

        return SkillResult(
            response=response,
            stage="autoplan",
        )

    def _fallback_response(self) -> str:
        return (
            "⚠️ AI 服务暂时不可用，无法启动自动规划流水线。\n\n"
            "您可以手动按以下顺序推进：\n"
            "1. 启枢 — 明确需求\n"
            "2. 裁衡 — CEO 视角审视\n"
            "3. 甄微 — 技术架构评审\n"
            "4. 策书 — 执行计划拆解\n"
            "5. 凝墨 — 生成完整方案\n"
            "6. 破妄 — 需求覆盖验证\n"
            "7. 渐衍 — 分阶段演进规划\n\n"
            "请在 AI 服务恢复后重新启动。"
        )
