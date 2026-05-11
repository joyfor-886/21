from typing import Dict, Any, List, Optional
import logging

from domain.enums import (
    FlowPhase,
    UserIntent,
    ClarityLevel,
    CHANNEL_PHASES,
    PHASE_ORDER,
    WORKFLOW_SYSTEM_PROMPTS,
    INTENT_PHASE_MAP,
)
from domain.results import IntentAnalysisResult

logger = logging.getLogger('Ssuma.FlowRouter')


class FlowRouter:
    """阶段路由决策器"""

    @staticmethod
    def phase_index(phase: FlowPhase) -> int:
        try:
            return PHASE_ORDER.index(phase)
        except ValueError:
            return 0

    @staticmethod
    def get_channel_phases(channel: str) -> List[FlowPhase]:
        return CHANNEL_PHASES.get(channel, CHANNEL_PHASES["standard"])

    @staticmethod
    def intent_to_phase(intent: UserIntent) -> FlowPhase:
        return INTENT_PHASE_MAP.get(intent, FlowPhase.QISHU)

    @staticmethod
    def workflow_to_phase(workflow: str) -> FlowPhase:
        mapping = {
            "qishu": FlowPhase.QISHU,
            "questionnaire": FlowPhase.QUESTIONNAIRE,
            "caiheng": FlowPhase.CAIHENG,
            "zhenwei": FlowPhase.ZHENWEI,
            "ceshu": FlowPhase.CESHU,
            "ningmo": FlowPhase.NINGMO,
            "powang": FlowPhase.POWANG,
            "jianyan": FlowPhase.JIANYAN,
            "chat": FlowPhase.QISHU,
        }
        return mapping.get(workflow, FlowPhase.QISHU)

    @staticmethod
    def intent_for_phase(phase: FlowPhase) -> UserIntent:
        mapping = {
            FlowPhase.QISHU: UserIntent.QISHU,
            FlowPhase.QUESTIONNAIRE: UserIntent.QUESTIONNAIRE,
            FlowPhase.CAIHENG: UserIntent.CAIHENG,
            FlowPhase.ZHENWEI: UserIntent.ZHENWEI,
            FlowPhase.CESHU: UserIntent.CESHU,
            FlowPhase.NINGMO: UserIntent.NINGMO,
        }
        return mapping.get(phase, UserIntent.CHAT)

    @staticmethod
    def check_phase_capability(phase: FlowPhase) -> bool:
        try:
            from core.llm_adapter import get_llm_adapter
            from core.llm_factory import LLMFactory

            adapter = get_llm_adapter()
            provider_name = LLMFactory.get_default_provider()
            provider = LLMFactory.get_provider(provider_name)
            model_name = getattr(provider, "model", "")

            model_info = adapter.detect_tier(model_name)
            config = adapter.get_capability_config(model_info.tier)

            phase_capability_map = {
                FlowPhase.QISHU: config.qishu_enabled,
                FlowPhase.CAIHENG: config.caiheng_enabled,
                FlowPhase.ZHENWEI: config.zhenwei_enabled,
                FlowPhase.CESHU: config.ceshu_enabled,
                FlowPhase.NINGMO: True,
                FlowPhase.POWANG: config.powang_enabled,
                FlowPhase.JIANYAN: config.jianyan_enabled,
            }

            enabled = phase_capability_map.get(phase, True)
            if not enabled:
                logger.info(f"Phase {phase.value} skipped (model tier doesn't support it)")
            return enabled
        except Exception:
            return True

    def determine_next_phase(
        self,
        current_phase: FlowPhase,
        intent_result: IntentAnalysisResult,
        force_workflow: Optional[str],
        channel: str,
        phase_completion: Dict[str, float],
    ) -> FlowPhase:
        if force_workflow:
            return self.workflow_to_phase(force_workflow)

        intent_target = self.intent_to_phase(intent_result.intent)
        channel_phases = self.get_channel_phases(channel)

        current_completion = phase_completion.get(current_phase.value, 0.0)

        if current_completion < 0.55 and current_phase not in [FlowPhase.INTENT_DETECTION]:
            if self.phase_index(intent_target) < self.phase_index(current_phase):
                return intent_target
            return current_phase

        if current_completion >= 0.55:
            if current_phase in channel_phases:
                current_idx = channel_phases.index(current_phase)
                if intent_target in channel_phases:
                    target_idx = channel_phases.index(intent_target)
                    if target_idx <= current_idx + 1:
                        if self.check_phase_capability(intent_target):
                            return intent_target
                if current_idx + 1 < len(channel_phases):
                    next_phase = channel_phases[current_idx + 1]
                    if self.check_phase_capability(next_phase):
                        return next_phase
                    for i in range(current_idx + 2, len(channel_phases)):
                        candidate = channel_phases[i]
                        if self.check_phase_capability(candidate):
                            return candidate
                    return FlowPhase.COMPLETED

        if current_phase == FlowPhase.INTENT_DETECTION:
            channel_phases = self.get_channel_phases(channel)
            if intent_result.clarity == ClarityLevel.FUZZY:
                return FlowPhase.QUESTIONNAIRE
            elif intent_result.clarity == ClarityLevel.CLEAR and intent_result.confidence > 0.8:
                return FlowPhase.QISHU
            else:
                return channel_phases[0] if channel_phases else FlowPhase.QISHU

        return current_phase

    def get_suggested_next_phase(
        self,
        current_phase: FlowPhase,
        channel: str,
    ) -> FlowPhase:
        channel_phases = self.get_channel_phases(channel)

        if current_phase in channel_phases:
            current_idx = channel_phases.index(current_phase)
            if current_idx + 1 < len(channel_phases):
                return channel_phases[current_idx + 1]

        phase_progression = {
            FlowPhase.QISHU: FlowPhase.CAIHENG,
            FlowPhase.QUESTIONNAIRE: FlowPhase.CAIHENG,
            FlowPhase.CAIHENG: FlowPhase.ZHENWEI,
            FlowPhase.ZHENWEI: FlowPhase.CESHU,
            FlowPhase.CESHU: FlowPhase.NINGMO,
            FlowPhase.NINGMO: FlowPhase.COMPLETED,
            FlowPhase.COMPLETED: FlowPhase.COMPLETED,
        }
        return phase_progression.get(current_phase, current_phase)
