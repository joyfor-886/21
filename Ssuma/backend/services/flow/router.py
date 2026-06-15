"""阶段路由决策器 — 向后兼容层

核心路由逻辑已迁移到 flow/graph.py 的 FlowGraph。
本文件保留 FlowRouter 类名以兼容现有导入。
"""

from typing import Dict, Any, List, Optional
import logging

from domain.enums import FlowPhase, UserIntent, CHANNEL_PHASES, PHASE_ORDER, INTENT_PHASE_MAP, WORKFLOW_SYSTEM_PROMPTS
from domain.results import IntentAnalysisResult
from services.flow.graph import FlowGraph

logger = logging.getLogger('Ssuma.FlowRouter')


class FlowRouter:
    """阶段路由决策器 — 委托到 FlowGraph"""

    def __init__(self):
        self._graph = FlowGraph()
        # 设置能力检查器
        self._graph.set_capability_checker(self._check_phase_capability)

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
        return FlowGraph.workflow_to_phase(workflow)

    @staticmethod
    def intent_for_phase(phase: FlowPhase) -> UserIntent:
        return FlowGraph.intent_for_phase(phase)

    @staticmethod
    def check_phase_capability(phase: FlowPhase) -> bool:
        return FlowRouter._check_phase_capability(phase)

    @staticmethod
    def _check_phase_capability(phase: FlowPhase) -> bool:
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
        next_phase, reason = self._graph.route(
            current_phase, intent_result, channel, phase_completion, force_workflow
        )
        logger.debug(f"Route: {current_phase.value} → {next_phase.value} ({reason.value})")
        return next_phase

    def get_suggested_next_phase(self, current_phase: FlowPhase, channel: str) -> FlowPhase:
        return self._graph.get_suggested_next_phase(current_phase, channel)
