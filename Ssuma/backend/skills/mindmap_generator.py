from typing import Dict, Any
from core.skill_registry import Skill, SkillResult
from core.llm_factory import LLMFactory
import json

MINDMAP_SYSTEM_PROMPT = """你是思维导图数据生成器。
你的唯一任务是将对话内容转换为严格的 JSON 格式，表示思维导图的层级结构。

输出格式要求：
1. 必须是合法的 JSON，不要输出 Markdown 代码块符号(如 ```json)
2. 根节点包含 "name" 和 "children"
3. "children" 是一个数组，每个元素包含 "name" 和可选的 "children"
4. 最多不要超过 4 层深度

示例：
{
  "name": "电商平台",
  "children": [
    {
      "name": "用户系统",
      "children": [
        {"name": "注册登录"},
        {"name": "个人中心"}
      ]
    },
    {
      "name": "订单系统",
      "children": [
        {"name": "购物车"},
        {"name": "结算"}
      ]
    }
  ]
}

绝对只输出 JSON，不要输出任何其他的文字解释！"""

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
