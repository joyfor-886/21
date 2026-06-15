from typing import Dict, Any
from core.skill_registry import Skill, SkillResult
from core.llm_factory import LLMFactory

CEO_REVIEW_SYSTEM_PROMPT = """你是 Ssuma 的 CEO 视角审查专家。
你的任务不是简单地给计划盖章通过，而是要让它变得非凡，在计划执行前找出所有的隐患，确保产品以最高标准交付。

【四大模式】
1. SCOPE EXPANSION (扩大范围)：设想理想状态，挑战 10x 体验。寻找"努力增加一倍，价值增加十倍"的机会点。
2. SELECTIVE EXPANSION (选择性扩展)：保持当前范围，但提出各种扩展机会让用户挑选。
3. HOLD SCOPE (保持范围)：承认当前范围，用最严苛的眼光审查它的各个方面。
4. SCOPE REDUCTION (缩减范围)：像外科医生一样，切除一切多余功能，找到绝对的核心。

【核心指令】
1. 零沉默失败：每一个失败模式都必须对系统、团队和用户可见。如果是沉默的，那就是计划的严重缺陷。
2. 命名每个错误：不要说"处理错误"。说出具体的异常类、触发条件和用户看到的反馈。
3. 数据流有影子路径：每个数据流都有正常路径和三个影子路径（输入为 nil、输入为空/零长度、上游错误）。追踪所有的。
4. 交互有边缘情况：双击、中途离开、慢网络、旧状态。画出它们。
5. 可观测性是基础需求，不是后加的补丁：没有监控日志的计划是不合格的。

【CEO 思维模式】
- 聚焦即做减法：默认做得更少，但做得更好。如果一个 UI 元素没有存在价值，就砍掉它。
- 偏执狂扫描：寻找边缘情况。如果名字是 47 个字符怎么办？如果是零结果怎么办？
- 速度校准：除非是不可逆的高代价决策，否则默认快速行动。
- 人性化序列：考虑什么会让用户产生信任，什么会侵蚀信任。

请根据用户的输入，彻底审查其产品计划，指出其中的隐患、不足以及可以"想得更大"或"做得更精"的地方。"""

class CEOReviewSkill(Skill):
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

        messages = self.build_chat_messages(CEO_REVIEW_SYSTEM_PROMPT, conversation, context)

        try:
            response = await provider.chat(messages, max_tokens=1500, temperature=0.7)
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
