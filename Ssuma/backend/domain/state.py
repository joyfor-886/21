import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from domain.enums import FlowPhase, ClarityLevel, UserIntent


class FlowState:
    """流程运行时状态"""

    def __init__(self, project_id: str = ""):
        self.project_id = project_id
        self.current_phase: FlowPhase = FlowPhase.INTENT_DETECTION
        self.channel: str = "standard"
        self.phase_completion: Dict[str, float] = {}
        self.conversation_turns: int = 0
        self.original_message: str = ""
        self.intent: Optional[UserIntent] = None
        self.clarity: Optional[ClarityLevel] = None
        self.confidence: float = 0.0
        self.workflow_history: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "current_phase": self.current_phase.value,
            "channel": self.channel,
            "phase_completion": self.phase_completion,
            "conversation_turns": self.conversation_turns,
            "original_message": self.original_message,
            "intent": self.intent.value if self.intent else None,
            "clarity": self.clarity.value if self.clarity else None,
            "confidence": self.confidence,
            "workflow_history": self.workflow_history,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FlowState":
        state = cls(project_id=data.get("project_id", ""))
        phase_val = data.get("current_phase", "intent_detection")
        try:
            state.current_phase = FlowPhase(phase_val)
        except ValueError:
            state.current_phase = FlowPhase.INTENT_DETECTION

        state.channel = data.get("channel", "standard")
        state.phase_completion = data.get("phase_completion", {})
        state.conversation_turns = data.get("conversation_turns", 0)
        state.original_message = data.get("original_message", "")

        intent_val = data.get("intent")
        if intent_val:
            try:
                state.intent = UserIntent(intent_val)
            except ValueError:
                state.intent = None

        clarity_val = data.get("clarity")
        if clarity_val:
            try:
                state.clarity = ClarityLevel(clarity_val)
            except ValueError:
                state.clarity = None

        state.confidence = data.get("confidence", 0.0)
        state.workflow_history = data.get("workflow_history", [])
        return state


class QuestionnaireState:
    """问卷运行时状态"""

    def __init__(self, project_id: str = ""):
        self.project_id = project_id
        self.current_stage: str = "basic_info"
        self.answers: Dict[str, Any] = {}
        self.completed: bool = False
        self.dimension_coverage: Dict[str, float] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "current_stage": self.current_stage,
            "answers": self.answers,
            "completed": self.completed,
            "dimension_coverage": self.dimension_coverage,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuestionnaireState":
        state = cls(project_id=data.get("project_id", ""))
        state.current_stage = data.get("current_stage", "basic_info")
        state.answers = data.get("answers", {})
        state.completed = data.get("completed", False)
        state.dimension_coverage = data.get("dimension_coverage", {})
        return state
