"""设计审查 (Design Review) - 首席产品设计师 UX/UI 审查

确保交互状态覆盖、信息架构合理、用户体验极致。
"""

from typing import Dict, Any
from core.skill_registry import Skill, SkillResult
from core.llm_factory import LLMFactory
from domain.enums import WORKFLOW_SYSTEM_PROMPTS

BASE_PROMPT = WORKFLOW_SYSTEM_PROMPTS.get("design_review", "")

DESIGN_REVIEW_SYSTEM_PROMPT = BASE_PROMPT + """

【深化检查清单】
1. 信息架构：用户第一眼、第二眼、第三眼应该看到什么？
2. 交互状态覆盖矩阵（必须逐项标记）：
   [ ] 默认/理想状态
   [ ] 加载中状态（骨架屏/进度条）
   [ ] 空状态（功能性引导，不可只是"暂无数据"）
   [ ] 错误状态（含恢复路径）
   [ ] 局部/边缘状态
3. 用户旅程连贯性：操作反馈闭环（Toast/动画/状态变更）
4. 响应式与无障碍：移动端适配、键盘导航、焦点管理
5. 生成式 UI 特殊性：延迟焦虑应对、流式输出体验、错误内容兜底

输出专业设计审查报告，像世界顶级设计总监一样尖锐但建设性。"""


class DesignReviewSkill(Skill):
    """设计审查 —— 确保 UX/UI 质量和状态覆盖"""

    name = "design_review"
    description = "产品设计与 UX 审查，确保状态覆盖和信息架构合理"
    trigger = "设计方案"

    async def run(self, conversation: str, context: Dict[str, Any] = None) -> SkillResult:
        try:
            provider = LLMFactory.get_provider()
        except Exception:
            return SkillResult(
                response=self._fallback_response(),
                stage="design_review",
            )

        context = context or {}
        artifact_context = context.get("artifact_context", "")

        enhanced_prompt = DESIGN_REVIEW_SYSTEM_PROMPT
        if artifact_context:
            enhanced_prompt += f"\n\n【前序阶段成果】\n{artifact_context}"

        messages = self.build_chat_messages(enhanced_prompt, conversation, context)

        try:
            response = await provider.chat(messages, max_tokens=3072, temperature=0.5)
        except Exception:
            response = self._fallback_response()

        return SkillResult(
            response=response,
            stage="design_review",
        )

    def _fallback_response(self) -> str:
        return (
            "⚠️ AI 服务暂时不可用，无法完成设计审查。\n\n"
            "请自行检查以下设计要点：\n"
            "1. 信息架构：视觉层级是否反映业务优先级？\n"
            "2. 五个状态：默认/加载中/空/错误/局部状态是否覆盖？\n"
            "3. 用户旅程：是否有困惑/受挫点？\n"
            "4. 响应式：移动端是否适配？\n"
            "5. AI 界面：延迟焦虑和错误输出如何应对？\n\n"
            "请在 AI 服务恢复后重新审查。"
        )
