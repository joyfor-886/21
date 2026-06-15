"""甄微 (Zhenwei) - 首席架构师技术评审

以 Staff Engineer 视角深度审查技术方案的可构建性、安全性和可维护性。
"""

from typing import Dict, Any
from core.skill_registry import Skill, SkillResult
from core.llm_factory import LLMFactory
from domain.enums import WORKFLOW_SYSTEM_PROMPTS

# 基础提示词来自 enums，在此基础上增强工程深度
BASE_PROMPT = WORKFLOW_SYSTEM_PROMPTS.get("zhenwei", "")

ENG_REVIEW_SYSTEM_PROMPT = BASE_PROMPT + """

【深化审查 —— 以下内容必须覆盖】

1. **数据流追踪**：为核心业务流程画出 ASCII 流程图，包含四个分支：
   - 正常路径 (Happy path)
   - 空值路径 (Nil/missing path)
   - 零长度路径 (Empty/zero-length path)
   - 错误路径 (Error/upstream failure path)

2. **状态转换**：为所有有状态的对象提供状态机说明，包含无效转换的防护。

3. **错误与恢复映射 (Error & Rescue Map)**：
   对所有可能失败的关键操作，列出：
   - 什么会出错（网络超时、API 429、JSON 解析失败等）
   - 是否被捕获？
   - 恢复动作是什么（重试、降级、抛出）？
   - 用户在这个失败下会看到什么？

4. **测试策略**：
   - 什么测试能让你在凌晨 2 点有信心发布？
   - 一个充满恶意的 QA 工程师会写什么测试来搞垮这个系统？

5. **单点故障与扩展性**：
   - 系统中的 SPoF 在哪里？
   - 在 10x 和 100x 负载下，最先崩溃的是什么？"""


class EngReviewSkill(Skill):
    """甄微 —— 架构师视角，深度技术评审"""

    name = "zhenwei"
    description = "甄微 - 技术评审，审核架构和数据流"
    trigger = "技术方案"

    async def run(self, conversation: str, context: Dict[str, Any] = None) -> SkillResult:
        try:
            provider = LLMFactory.get_provider()
        except Exception:
            return SkillResult(
                response=self._fallback_response(),
                stage="zhenwei",
            )

        context = context or {}
        artifact_context = context.get("artifact_context", "")

        enhanced_prompt = ENG_REVIEW_SYSTEM_PROMPT
        if artifact_context:
            enhanced_prompt += f"\n\n【前序阶段成果】\n{artifact_context}"

        messages = self.build_chat_messages(enhanced_prompt, conversation, context)

        try:
            response = await provider.chat(messages, max_tokens=3072, temperature=0.3)
        except Exception:
            response = self._fallback_response()

        return SkillResult(
            response=response,
            stage="zhenwei",
        )

    def _fallback_response(self) -> str:
        return (
            "⚠️ AI 服务暂时不可用，无法完成技术架构评审。\n\n"
            "以下是一些通用的架构审查要点供您自行检查：\n"
            "1. 系统边界是否清晰？组件耦合度如何？\n"
            "2. 数据流是否有完整的正常/空值/错误路径？\n"
            "3. 是否存在单点故障？\n"
            "4. 在 10x 负载下最先崩溃的是什么？\n"
            "5. 安全威胁模型是否覆盖了注入攻击？\n\n"
            "请在 AI 服务恢复后重新进行评审。"
        )
