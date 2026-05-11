import re
import logging
from typing import Dict, Any, List, Optional
from services.artifact_store import PhaseArtifact

logger = logging.getLogger('Ssuma.ArtifactExtractor')


class ArtifactExtractor:
    """从 LLM 响应中提取结构化物件

    参考 Dean Peters 的假设驱动发现模式：
    不依赖额外 LLM 调用，通过规则提取关键信息。

    与 ArtifactStore 职责分离：
    - ArtifactExtractor: 负责从文本中提取结构化信息（"是什么"）
    - ArtifactStore: 负责存储和检索 PhaseArtifact（"怎么存"）
    """

    @staticmethod
    async def extract(
        phase: str,
        response: str,
        conversation: str = "",
        completion_result=None,
    ) -> PhaseArtifact:
        decisions = ArtifactExtractor._extract_decisions(response)
        commitments = ArtifactExtractor._extract_commitments(response)
        open_questions = ArtifactExtractor._extract_questions(response)
        key_insights = ArtifactExtractor._extract_insights(response)
        summary = ArtifactExtractor._extract_summary(response, phase)

        metadata = {}
        if completion_result:
            metadata["completion_score"] = completion_result.score
            metadata["dimensions_covered"] = completion_result.dimensions_covered
            metadata["dimensions_missing"] = completion_result.dimensions_missing

        return PhaseArtifact(
            phase=phase,
            summary=summary,
            decisions=decisions,
            commitments=commitments,
            open_questions=open_questions,
            key_insights=key_insights,
            raw_output=response[:2000],
            metadata=metadata,
        )

    @staticmethod
    def _extract_decisions(text: str) -> List[str]:
        decisions = []
        patterns = [
            r'(?:决定|选择|采用|确认|确定)[：:]\s*(.+?)(?:[。\n]|$)',
            r'(?:我们|方案|系统)(?:将|会|应该)(.+?)(?:[。\n]|$)',
            r'(?:使用|基于|依靠)(.+?)(?:来实现|来构建|作为)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            decisions.extend([m.strip()[:100] for m in matches[:3]])
        return decisions[:5]

    @staticmethod
    def _extract_commitments(text: str) -> List[Dict[str, str]]:
        commitments = []

        non_goals = re.findall(
            r'(?:不做|非目标|out of scope|不包含)[：:]\s*(.+?)(?:[。\n]|$)',
            text, re.IGNORECASE
        )
        for ng in non_goals[:2]:
            commitments.append({"category": "非目标", "content": ng.strip()[:100]})

        constraints = re.findall(
            r'(?:约束|限制|前提|必须)[：:]\s*(.+?)(?:[。\n]|$)', text
        )
        for c in constraints[:2]:
            commitments.append({"category": "约束", "content": c.strip()[:100]})

        return commitments[:5]

    @staticmethod
    def _extract_questions(text: str) -> List[str]:
        questions = []

        q_patterns = re.findall(r'([^.!?\n]*[？?])', text)
        questions.extend([q.strip()[:100] for q in q_patterns[:3]])

        pending = re.findall(
            r'(?:待确认|待解决|需要确认|需要决定)[：:]\s*(.+?)(?:[。\n]|$)', text
        )
        questions.extend([p.strip()[:100] for p in pending[:2]])

        return questions[:5]

    @staticmethod
    def _extract_insights(text: str) -> List[str]:
        insights = []

        patterns = [
            r'(?:关键|核心|重要|洞察|发现)[：:]\s*(.+?)(?:[。\n]|$)',
            r'(?:核心问题|最大风险|关键假设)[：:]\s*(.+?)(?:[。\n]|$)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            insights.extend([m.strip()[:100] for m in matches[:2]])

        return insights[:5]

    @staticmethod
    def _extract_summary(text: str, phase: str) -> str:
        base = text.strip()[:200]
        sentences = re.split(r'[。！？\n]', base)
        if sentences:
            summary = sentences[0][:100]
        else:
            summary = base[:100]

        if not summary:
            summary = f"{phase}阶段讨论完成"

        return summary
