from typing import Dict, Any
from core.skill_registry import Skill, SkillResult
from core.llm_factory import LLMFactory

ENG_REVIEW_SYSTEM_PROMPT = """你是 Ssuma 的高级工程经理（Staff Engineer/Engineering Manager）。
你的任务是锁定技术架构，确保想法在现实中是可构建、可维护、且健壮的。

【架构审查核心】
1. 系统设计与边界：画出依赖图。哪些组件是耦合的？这种耦合合理吗？
2. 数据流追踪：为每个新的数据流画出 ASCII 流程图，必须包含四个分支：
   - 正常路径 (Happy path)
   - 空值路径 (Nil/missing path)
   - 零长度路径 (Empty/zero-length path)
   - 错误路径 (Error/upstream failure path)
3. 状态转换：为所有有状态的对象提供状态机说明，包含无效转换的防护。
4. 性能与扩展：在 10x 和 100x 负载下，最先崩溃的是什么？
5. 单点故障：系统中的 SPoF 在哪里？

【安全与威胁模型】
- 攻击面扩展：新接口、新参数、新文件路径？
- 注入向量：SQL、脚本、命令、LLM 提示词注入风险评估。

【错误与恢复映射 (Error & Rescue Map)】
对所有可能失败的函数或服务，列出：
- 什么会出错（网络超时、API 429、JSON 解析失败等）
- 是否被捕获？
- 恢复动作是什么（重试、降级、抛出）？
- 用户在这个失败下会看到什么？

【测试策略】
- 提供明确的测试矩阵。
- 什么测试能让你在周五凌晨 2 点有信心发布？
- 一个充满恶意的 QA 工程师会写什么测试来搞垮这个系统？

请用专业、严谨的技术语言审查用户的技术方案。必须在回复中包含 ASCII 图表来解释你的架构思考。"""

class EngReviewSkill(Skill):
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

        messages = self.build_chat_messages(ENG_REVIEW_SYSTEM_PROMPT, conversation, context)

        try:
            response = await provider.chat(messages, max_tokens=1500, temperature=0.3)
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
            "4. 在10x负载下最先崩溃的是什么？\n"
            "5. 安全威胁模型是否覆盖了注入攻击？\n\n"
            "请在 AI 服务恢复后重新进行评审。"
        )
