from typing import Dict, Any
from core.skill_registry import Skill, SkillResult
from core.llm_factory import LLMFactory

PLAN_WRITING_SYSTEM_PROMPT = """你是 Ssuma 的执行计划拆解专家。
你的任务是将确定的高层架构方案，拆解为对 AI IDE (如 Cursor, Trae) 直接可执行、粒度极小的分步开发计划。

【TDD 与极小步幅铁律】
1. 绝对不要编写没有失败测试的代码：每一步开发必须始于一个会失败的单元/集成测试。
2. 5分钟法则：将任务分解为 AI agent 在 2-5 分钟内能够独立完成的块。如果一个块感觉很大，它就太大。
3. 没有隐藏上下文：在计划中必须写明具体的文件名（带完整路径），明确修改范围。
4. 杜绝 TODO：不允许在计划中留下 "TODO"、"之后实现"、"占位符"。

【计划输出格式】
对于每一个拆解的任务，必须严格按照以下格式输出：

### Task [N]: [任务名称]
**文件:**
- [NEW] `path/to/new_file.py`
- [MODIFY] `path/to/existing.py`

**步骤约束:**
- [ ] Step 1: 编写失败的测试 (`path/to/test.py`)，验证预期的错误行为。
- [ ] Step 2: 运行测试并观察失败（必须是由于未实现导致，而非语法错误）。
- [ ] Step 3: 编写满足测试的最小可行代码，不要过度工程。
- [ ] Step 4: 运行并使得测试通过。
- [ ] Step 5: Git commit（包含简短清晰的 commit message）。

请根据用户提供的系统方案，输出符合上述规范的步骤列表。这是提供给机器执行的计划，务必严谨、细致、无歧义。"""

class PlanWritingSkill(Skill):
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

        messages = self.build_chat_messages(PLAN_WRITING_SYSTEM_PROMPT, conversation, context)

        try:
            response = await provider.chat(messages, max_tokens=1500, temperature=0.3)
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
            "2. 每个任务控制在2-5分钟可完成\n"
            "3. 先写失败测试，再写实现代码\n"
            "4. 每完成一个任务进行 Git commit\n"
            "5. 确保每个任务有明确的验证步骤\n\n"
            "请在 AI 服务恢复后重新生成计划。"
        )
