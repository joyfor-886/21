import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from core.skill_registry import Skill, SkillResult

logger = logging.getLogger('Ssuma.JianyanSkill')

JIANYAN_SYSTEM_PROMPT = """你是"渐衍"技能 - 分阶段生成专家。

你的职责是将复杂的项目方案拆分为多个阶段，逐步生成并验证每个阶段的可达成性。

【分阶段策略】
1. 先生成大纲/架构（Phase 1）
2. 评估技术可行性（Phase 2）
3. 生成详细规格（Phase 3）
4. 验证完整性（Phase 4）

每个阶段都可以单独Review和修正，避免一次性生成导致的质量问题。

【输出格式】
请描述你将如何分阶段生成此方案，并列出每个阶段的产出物和验证要点。

保持简洁，明确每个阶段的交付物和时间预估。"""


@dataclass
class Phase:
    phase_num: int
    title: str
    deliverables: List[str]
    verification: List[str]
    estimated_time: str


class JianyanSkill(Skill):
    """渐衍 - 分阶段生成，逐步验证

    改进点：
    1. 继承 Skill 基类
    2. 从 @classmethod 改为实例方法
    3. 参考 massimodeluisa/recursive-decomposition-skill 的递归分解模式
    4. 支持 context 中的 artifacts 注入
    """
    name = "jianyan"
    description = "渐衍 - 分阶段生成，逐步验证"
    trigger = "分阶段"
    required_outputs = ["phases", "deliverables", "verification"]

    async def run(self, conversation: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        from core.llm_factory import LLMFactory

        context = context or {}

        # 当前方案概要
        current_spec = context.get("current_spec", conversation)

        # 分析并生成分阶段计划
        prompt = f"""请将以下项目方案分阶段生成：

【项目概述】
{current_spec[:3000]}

请分析并给出分阶段生成计划：

每个阶段应包含：
1. 阶段名称（Phase N）
2. 交付物（具体文件/功能）
3. 验证要点（如何确认完成）
4. 时间预估

请以JSON数组格式输出，例如：
[
    {{
        "phase": 1,
        "title": "基础架构",
        "deliverables": ["package.json", "项目结构"],
        "verification": ["npm run build 成功"],
        "estimated_time": "1-2小时"
    }}
]

只输出JSON。"""

        try:
            provider = LLMFactory.get_provider()
            response = await provider.chat(
                [{"role": "system", "content": JIANYAN_SYSTEM_PROMPT},
                 {"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.5
            )

            if not response or not response.strip():
                response = "分阶段生成暂时不可用，请稍后再试。"

            phases = self._parse_phases(response)

            return SkillResult(
                response=response,
                stage="jianyan",
                metadata={"phases": phases},
            )
        except Exception as e:
            logger.error(f"Jianyan skill error: {e}")
            return self._fallback_response(conversation)

    def _fallback_response(self, conversation: str) -> SkillResult:
        return SkillResult(
            response=(
                "⚠️ 分阶段生成服务暂时不可用。\n\n"
                "建议按以下阶段手动规划：\n"
                "1. **基础架构** — 搭建项目骨架和核心数据模型\n"
                "2. **核心功能** — 实现最小可用功能集\n"
                "3. **完善与测试** — 补充边界情况和自动化测试\n"
                "4. **集成验证** — 端到端验证所有功能\n\n"
                "💡 AI服务恢复后，可以重新生成详细的分阶段计划。"
            ),
            stage="jianyan",
            metadata={"phases": []},
        )

    def _parse_phases(self, response: str) -> List[Dict]:
        """解析阶段数据"""
        try:
            json_start = response.find("[")
            json_end = response.rfind("]") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                phases = json.loads(json_str)

                return [
                    {
                        "phase": p.get("phase", 0),
                        "title": p.get("title", ""),
                        "deliverables": p.get("deliverables", []),
                        "verification": p.get("verification", []),
                        "estimated_time": p.get("estimated_time", "")
                    }
                    for p in phases
                ]
        except Exception:
            pass

        return []

    def generate_phases_summary(self, phases: List[Dict]) -> str:
        """生成阶段摘要"""
        if not phases:
            return "⚠️ 无法生成分阶段计划"

        total_time = sum(
            self._parse_time(p.get("estimated_time", ""))
            for p in phases
        )

        summary = f"""## 📋 渐衍分阶段计划

共 **{len(phases)}** 个阶段，预计总时间 **{total_time}**

| 阶段 | 交付物 | 验证 | 时间 |
|------|--------|------|------|
"""
        for p in phases:
            dels = ", ".join(p.get("deliverables", [])[:2])
            vers = ", ".join(p.get("verification", [])[:2])
            summary += f"| {p.get('phase', '')} | {p.get('title', '')} | {dels} | {vers} | {p.get('estimated_time', '')} |\n"

        return summary

    def _parse_time(self, time_str: str) -> float:
        """解析时间字符串为小时"""
        import re
        match = re.search(r"(\d+)", time_str)
        if match:
            return float(match.group(1))
        return 1

    def get_current_phase(self, phases: List[Dict], current: int = 0) -> Optional[Dict]:
        """获取当前应该执行的阶段"""
        if current < len(phases):
            return phases[current]
        return None
