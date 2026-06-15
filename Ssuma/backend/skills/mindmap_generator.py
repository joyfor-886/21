from typing import Dict, Any
from core.skill_registry import Skill, SkillResult
from core.llm_factory import LLMFactory
from domain.enums import WORKFLOW_SYSTEM_PROMPTS
import json

MINDMAP_SYSTEM_PROMPT = WORKFLOW_SYSTEM_PROMPTS.get("mindmap", """你是思维导图数据生成器。将对话内容转换为严格 JSON 层级结构。

输出格式：
- 合法 JSON，不含 Markdown 代码块符号
- 根节点 "name" + "children"
- 最多 4 层深度
- 只输出 JSON，不输出任何其他文字""")

class MindmapGeneratorSkill(Skill):
    name = "mindmap-generator"
    description = "将讨论内容提取为思维导图结构 (JSON)"
    trigger = "思维导图"

    async def run(self, conversation: str, context: Dict[str, Any] = None) -> SkillResult:
        try:
            provider = LLMFactory.get_provider()
        except Exception:
            return SkillResult(
                response=self._fallback_response(),
                stage="mindmap",
            )

        messages = [
            {"role": "system", "content": MINDMAP_SYSTEM_PROMPT},
            {"role": "user", "content": f"将以下对话内容整理为 JSON 思维导图：\n\n{conversation}"}
        ]

        try:
            response = await provider.chat(messages, max_tokens=4000, temperature=0.2)
        except Exception:
            return SkillResult(
                response=self._fallback_response(),
                stage="mindmap",
            )

        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()

        return SkillResult(
            response=response,
            stage="mindmap",
            metadata={"mindmap_data": cleaned_response},
        )

    def _fallback_response(self) -> str:
        return "⚠️ AI 服务暂时不可用，无法生成思维导图。请在服务恢复后重试。"
