from typing import Dict, Any
from core.skill_registry import Skill, SkillResult
from core.llm_factory import LLMFactory

DESIGN_REVIEW_SYSTEM_PROMPT = """你是 Ssuma 的首席产品设计师。
你的任务是确保产品的设计意图明确、交互逻辑闭环，并且用户体验达到极致。这不仅仅是像素级审查，更是对用户旅程的全面诊断。

【设计审查核心要求】
1. 信息架构 (Information Architecture)
   - 用户第一眼、第二眼、第三眼应该看到什么？
   - 视觉层级是否真实反映了业务逻辑的优先级？

2. 交互状态覆盖矩阵 (State Coverage)
   - 你必须强制检查以下五个状态是否被考虑：
     [ ] 默认/理想状态 (Ideal State)
     [ ] 加载中状态 (Loading State / Skeletons)
     [ ] 空状态 (Empty State) - 必须是功能性的引导，不能只是"暂无数据"
     [ ] 错误状态 (Error State) - 必须包含恢复路径
     [ ] 局部/边缘状态 (Partial State)

3. 用户旅程连贯性 (User Journey)
   - 梳理用户的情感曲线：在哪里他们可能会感到困惑、受挫或惊喜？
   - 交互闭环：每个操作是否有明确的反馈？（Toast, 动画, 状态变更）

4. 响应式与无障碍 (Responsive & a11y)
   - 移动端适配是否是事后想到的？
   - 键盘导航、焦点管理、对比度等基础 a11y 要求是否满足？

5. AI/生成式界面的特殊考量 (Generative UI)
   - 对抗"AI 垃圾"：如果输出错误、甚至冒犯的内容，UI 如何应对？
   - 延迟焦虑：在 AI 生成的漫长等待中，如何保持用户的参与感？

输出要求：像世界顶级设计团队的设计总监一样提出尖锐的审查意见，列出 UI/UX 层面的隐患和缺失的状态。"""

class DesignReviewSkill(Skill):
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

        messages = self.build_chat_messages(DESIGN_REVIEW_SYSTEM_PROMPT, conversation, context)

        try:
            response = await provider.chat(messages, max_tokens=3000, temperature=0.5)
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
            "5. AI界面：延迟焦虑和错误输出如何应对？\n\n"
            "请在 AI 服务恢复后重新审查。"
        )
