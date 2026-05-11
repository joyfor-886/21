from enum import Enum
from typing import Dict, List


class FlowPhase(Enum):
    INTENT_DETECTION = "intent_detection"
    QISHU = "qishu"
    QUESTIONNAIRE = "questionnaire"
    CAIHENG = "caiheng"
    ZHENWEI = "zhenwei"
    CESHU = "ceshu"
    NINGMO = "ningmo"
    POWANG = "powang"
    JIANYAN = "jianyan"
    COMPLETED = "completed"


class UserIntent(Enum):
    QISHU = "qishu"
    QUESTIONNAIRE = "questionnaire"
    CAIHENG = "caiheng"
    ZHENWEI = "zhenwei"
    CESHU = "ceshu"
    NINGMO = "ningmo"
    CHAT = "chat"
    UNKNOWN = "unknown"


class ClarityLevel(Enum):
    FUZZY = "fuzzy"
    PARTIAL = "partial"
    CLEAR = "clear"
    TECHNICAL = "technical"


class ModelTier(Enum):
    ADEQUATE = "adequate"
    BASIC = "basic"
    INSUFFICIENT = "insufficient"


class DataQuality(Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


PHASE_ORDER: List[FlowPhase] = [
    FlowPhase.INTENT_DETECTION,
    FlowPhase.QISHU,
    FlowPhase.QUESTIONNAIRE,
    FlowPhase.CAIHENG,
    FlowPhase.ZHENWEI,
    FlowPhase.CESHU,
    FlowPhase.NINGMO,
    FlowPhase.POWANG,
    FlowPhase.JIANYAN,
    FlowPhase.COMPLETED,
]

CHANNEL_PHASES: Dict[str, List[FlowPhase]] = {
    "fast": [
        FlowPhase.QISHU,
        FlowPhase.CAIHENG,
        FlowPhase.NINGMO,
    ],
    "standard": [
        FlowPhase.QISHU,
        FlowPhase.QUESTIONNAIRE,
        FlowPhase.CAIHENG,
        FlowPhase.CESHU,
        FlowPhase.NINGMO,
    ],
    "deep": [
        FlowPhase.QISHU,
        FlowPhase.QUESTIONNAIRE,
        FlowPhase.CAIHENG,
        FlowPhase.ZHENWEI,
        FlowPhase.CESHU,
        FlowPhase.NINGMO,
        FlowPhase.POWANG,
    ],
}

INTENT_PHASE_MAP: Dict[UserIntent, FlowPhase] = {
    UserIntent.QISHU: FlowPhase.QISHU,
    UserIntent.QUESTIONNAIRE: FlowPhase.QUESTIONNAIRE,
    UserIntent.CAIHENG: FlowPhase.CAIHENG,
    UserIntent.ZHENWEI: FlowPhase.ZHENWEI,
    UserIntent.CESHU: FlowPhase.CESHU,
    UserIntent.NINGMO: FlowPhase.NINGMO,
    UserIntent.CHAT: FlowPhase.QISHU,
    UserIntent.UNKNOWN: FlowPhase.QISHU,
}

WORKFLOW_SYSTEM_PROMPTS: Dict[str, str] = {
    "qishu": "你是枢墨的启枢专家。通过对话帮助用户从模糊想法走向清晰需求。一次只问一个问题。你必须始终使用中文回复。",
    "questionnaire": "你是枢墨的问卷专家。通过结构化问卷收集项目的关键维度信息。你必须始终使用中文回复。",
    "caiheng": "你是枢墨的裁衡专家。从CEO视角审查项目方案的商业可行性和战略一致性。你必须始终使用中文回复。",
    "zhenwei": "你是枢墨的真伪专家。从架构师视角审查技术方案的可行性和工程合理性。你必须始终使用中文回复。",
    "ceshu": "你是枢墨的策术专家。将审查通过的方案拆解为可执行的TDD步骤。你必须始终使用中文回复。",
    "ningmo": "你是枢墨的凝墨专家。将多轮讨论成果整合为结构化的项目执行方案。你必须始终使用中文回复。",
    "powang": "你是枢墨的破妄专家。验证方案是否满足原始需求，评估覆盖度。你必须始终使用中文回复。",
    "jianyan": "你是枢墨的渐衍专家。将复杂方案分阶段生成并逐步验证。你必须始终使用中文回复。",
}
