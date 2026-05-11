from typing import Dict, Any, List, Optional, Callable, Awaitable
import json
import logging
from services.intent_analyzer import (
    IntentAnalyzer,
    IntentAnalysisResult,
    UserIntent,
    ClarityLevel,
    FlowState,
    INTENT_LABELS,
    INTENT_DESCRIPTIONS,
)
from services.questionnaire_service import QuestionnaireState
from services.response_validator import ResponseValidator
from services.context_manager import ContextManager
from services.feedback_service import FeedbackService
from services.fact_checker import FactChecker
from services.phase_gates import PhaseCompletionGate
from services.artifact_store import ArtifactStore, PhaseArtifact, extract_artifact_from_response
from core.skill_registry import SkillRegistry, Skill
from services.flow.router import (
    FlowPhase,
    FlowRouter,
    PHASE_ORDER,
    CHANNEL_PHASES,
    WORKFLOW_SYSTEM_PROMPTS,
)

logger = logging.getLogger('Ssuma.AdaptiveFlow')


class AdaptiveFlowService:
    """向后兼容适配层 — 所有 @classmethod 委托到 FlowService 实例

    新代码应直接使用:
        from services.flow.service import get_flow_service
        service = get_flow_service()
        result = await service.process_message(...)

    旧代码仍可使用:
        result = await AdaptiveFlowService.process_message(...)
    """

    STATE_SERVICE_FLOW = "adaptive_flow_current"
    STATE_SERVICE_STATE = "adaptive_flow_state"
    STATE_SERVICE_CHANNEL = "adaptive_flow_channel"

    @classmethod
    def _get_service(cls):
        from services.flow.service import get_flow_service
        return get_flow_service()

    @classmethod
    async def process_message(
        cls,
        project_id: str,
        message: str,
        conversation: Optional[str] = None,
        force_workflow: Optional[str] = None,
        attachments: Optional[List[dict]] = None
    ) -> Dict[str, Any]:
        return await cls._get_service().process_message(
            project_id, message, conversation, force_workflow, attachments
        )

    @classmethod
    def get_flow_status(cls, project_id: str) -> Dict[str, Any]:
        return cls._get_service().get_flow_status(project_id)

    @classmethod
    def get_flow_options(cls, project_id: str) -> List[Dict[str, Any]]:
        return cls._get_service().get_flow_options(project_id)

    @classmethod
    def reset_flow(cls, project_id: str):
        return cls._get_service().reset_flow(project_id)

    @classmethod
    def switch_workflow(cls, project_id: str, workflow: str) -> bool:
        return cls._get_service().switch_workflow(project_id, workflow)
