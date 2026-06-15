from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from domain.enums import UserIntent, ClarityLevel, FlowPhase

INTENT_LABELS = {
    UserIntent.QISHU: "启枢",
    UserIntent.TANYIN: "探隐",
    UserIntent.CAIHENG: "裁衡",
    UserIntent.ZHENWEI: "甄微",
    UserIntent.CESHU: "策书",
    UserIntent.NINGMO: "凝墨",
    UserIntent.CHAT: "对话",
    UserIntent.UNKNOWN: "待分析",
}

CLARITY_LABELS = {
    ClarityLevel.FUZZY: "模糊 - 需要引导",
    ClarityLevel.PARTIAL: "部分清晰 - 需要澄清",
    ClarityLevel.CLEAR: "清晰 - 可以直接生成方案",
    ClarityLevel.TECHNICAL: "技术讨论 - 深入实现层面",
}


class IntentAnalysisResult(BaseModel):
    """意图分析结果 — Pydantic 结构化输出"""
    intent: UserIntent
    clarity: ClarityLevel
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""
    recommended_workflow: str = ""
    next_action: str = ""
    context: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value,
            "intent_label": INTENT_LABELS.get(self.intent, ""),
            "clarity": self.clarity.value,
            "clarity_label": CLARITY_LABELS.get(self.clarity, ""),
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "recommended_workflow": self.recommended_workflow,
            "next_action": self.next_action,
            "context": self.context,
        }


class CompletionResult(BaseModel):
    """阶段完成度评估结果 — Pydantic 结构化输出"""
    phase: str
    score: float = Field(ge=0.0, le=1.0)
    dimensions_covered: List[str] = Field(default_factory=list)
    dimensions_missing: List[str] = Field(default_factory=list)
    should_advance: bool = False
    reasoning: str = ""
    next_questions: List[str] = Field(default_factory=list)


class SkillResult(BaseModel):
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


class PhaseArtifact(BaseModel):
    """阶段产出的结构化物件 — Pydantic 结构化输出"""
    phase: str
    summary: str = ""
    decisions: List[str] = Field(default_factory=list)
    commitments: List[Dict[str, str]] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    key_insights: List[str] = Field(default_factory=list)
    raw_output: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PhaseArtifact":
        return cls.model_validate(data)

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
