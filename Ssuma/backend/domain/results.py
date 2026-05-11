from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from domain.enums import UserIntent, ClarityLevel, FlowPhase


class IntentAnalysisResult:

    def __init__(
        self,
        intent: UserIntent,
        clarity: ClarityLevel,
        confidence: float,
        reasoning: str,
        recommended_workflow: str,
        next_action: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.intent = intent
        self.clarity = clarity
        self.confidence = confidence
        self.reasoning = reasoning
        self.recommended_workflow = recommended_workflow
        self.next_action = next_action
        self.context = context or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value,
            "clarity": self.clarity.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "recommended_workflow": self.recommended_workflow,
            "next_action": self.next_action,
            "context": self.context,
        }


@dataclass
class SkillResult:
    """Skill 执行结果的统一格式

    所有 Skill.run() 必须返回此类型。
    stage 值必须与 FlowPhase 枚举值一致。
    """
    response: str
    stage: str = ""
    artifacts: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"response": self.response, "stage": self.stage}
        if self.artifacts:
            result["artifacts"] = self.artifacts
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class CompletionResult:
    """阶段完成度评估结果"""
    phase: str
    score: float
    dimensions_covered: List[str] = field(default_factory=list)
    dimensions_missing: List[str] = field(default_factory=list)
    can_advance: bool = False
    reason: str = ""


@dataclass
class PhaseArtifact:
    """阶段产出的结构化物件"""
    phase: str
    summary: str
    decisions: List[str] = field(default_factory=list)
    commitments: List[Dict[str, str]] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    key_insights: List[str] = field(default_factory=list)
    raw_output: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "summary": self.summary,
            "decisions": self.decisions,
            "commitments": self.commitments,
            "open_questions": self.open_questions,
            "key_insights": self.key_insights,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PhaseArtifact":
        return cls(
            phase=data.get("phase", ""),
            summary=data.get("summary", ""),
            decisions=data.get("decisions", []),
            commitments=data.get("commitments", []),
            open_questions=data.get("open_questions", []),
            key_insights=data.get("key_insights", []),
            raw_output=data.get("raw_output", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            metadata=data.get("metadata", {}),
        )

    def to_compact_context(self) -> str:
        parts = [f"[{self.phase}阶段总结]"]
        parts.append(self.summary)

        if self.decisions:
            parts.append("关键决策: " + "；".join(self.decisions[:5]))
        if self.commitments:
            for c in self.commitments[:3]:
                parts.append(f"约束[{c.get('category', '')}]: {c.get('content', '')}")
        if self.open_questions:
            parts.append("待解决: " + "；".join(self.open_questions[:3]))
        if self.key_insights:
            parts.append("关键洞察: " + "；".join(self.key_insights[:3]))

        return "\n".join(parts)
