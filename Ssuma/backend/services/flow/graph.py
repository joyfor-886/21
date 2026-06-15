"""Flow 状态图 — 声明式阶段路由

参考 LangGraph StateGraph 设计，用声明式图替代 140 行 if-elif 链。

核心思想：
  - 每个阶段是一个节点（node）
  - 节点间的转移由条件边（conditional edge）决定
  - 通道配置决定哪些节点在路径上
  - 意图和完成度决定走哪条边

与 LangGraph 的区别：
  - 不引入 langgraph 依赖（纯 Python 实现）
  - 保持与现有 FlowPhase 枚举的兼容性
  - 路由逻辑可测试、可扩展
"""

from typing import Dict, Any, List, Optional, Callable
from enum import Enum
import logging

from domain.enums import (
    FlowPhase,
    UserIntent,
    ClarityLevel,
    CHANNEL_PHASES,
    PHASE_ORDER,
    INTENT_PHASE_MAP,
)
from domain.results import IntentAnalysisResult

logger = logging.getLogger('Ssuma.FlowGraph')


class TransitionReason(Enum):
    """转移原因"""
    COMPLETION_ADVANCE = "completion_advance"    # 完成度达标，前进
    INTENT_DIRECT = "intent_direct"              # 意图直接跳转
    INTENT_BACK = "intent_back"                  # 意图回退
    CHANNEL_NEXT = "channel_next"                # 通道顺序前进
    CHANNEL_SKIP = "channel_skip"                # 通道跳过（模型不支持）
    INTENT_DETECTION = "intent_detection"        # 意图检测阶段路由
    FORCE_WORKFLOW = "force_workflow"             # 强制工作流
    STAY = "stay"                                # 停留当前阶段


class FlowGraph:
    """声明式阶段路由图

    用法：
        graph = FlowGraph()
        next_phase, reason = graph.route(current_phase, intent_result, channel, phase_completion)
    """

    # 默认阶段前进映射（不依赖通道）
    DEFAULT_PROGRESSION: Dict[FlowPhase, FlowPhase] = {
        FlowPhase.QISHU: FlowPhase.CAIHENG,
        FlowPhase.TANYIN: FlowPhase.CAIHENG,
        FlowPhase.CAIHENG: FlowPhase.ZHENWEI,
        FlowPhase.ZHENWEI: FlowPhase.CESHU,
        FlowPhase.CESHU: FlowPhase.NINGMO,
        FlowPhase.NINGMO: FlowPhase.COMPLETED,
        FlowPhase.POWANG: FlowPhase.JIANYAN,
        FlowPhase.JIANYAN: FlowPhase.COMPLETED,
        FlowPhase.COMPLETED: FlowPhase.COMPLETED,
    }

    def __init__(self):
        self._phase_capability_checker: Optional[Callable[[FlowPhase], bool]] = None

    def set_capability_checker(self, checker: Callable[[FlowPhase], bool]) -> None:
        """设置阶段能力检查器（用于模型档次过滤）"""
        self._phase_capability_checker = checker

    def _check_capability(self, phase: FlowPhase) -> bool:
        if self._phase_capability_checker:
            return self._phase_capability_checker(phase)
        return True

    def route(
        self,
        current_phase: FlowPhase,
        intent_result: IntentAnalysisResult,
        channel: str,
        phase_completion: Dict[str, float],
        force_workflow: Optional[str] = None,
    ) -> tuple:
        """路由到下一阶段

        Returns:
            (next_phase, reason) 元组
        """
        # 1. 强制工作流
        if force_workflow:
            return self.workflow_to_phase(force_workflow), TransitionReason.FORCE_WORKFLOW

        # 2. 意图检测阶段 — 特殊路由
        if current_phase == FlowPhase.INTENT_DETECTION:
            return self._route_from_intent_detection(intent_result, channel)

        # 3. 当前阶段未完成 — 停留
        current_completion = phase_completion.get(current_phase.value, 0.0)
        if current_completion < 0.55:
            intent_target = self.intent_to_phase(intent_result.intent)
            # 允许回退到更早的阶段
            if self.phase_index(intent_target) < self.phase_index(current_phase):
                return intent_target, TransitionReason.INTENT_BACK
            return current_phase, TransitionReason.STAY

        # 4. 当前阶段已完成 — 前进
        return self._route_advance(current_phase, intent_result, channel, phase_completion)

    def _route_from_intent_detection(
        self,
        intent_result: IntentAnalysisResult,
        channel: str,
    ) -> tuple:
        """意图检测阶段的特殊路由逻辑"""
        intent = intent_result.intent
        clarity = intent_result.clarity

        # 直接意图映射
        if intent in [UserIntent.QISHU, UserIntent.CAIHENG, UserIntent.ZHENWEI,
                      UserIntent.CESHU, UserIntent.NINGMO]:
            target = self.intent_to_phase(intent)
            if self._check_capability(target):
                return target, TransitionReason.INTENT_DIRECT

        # 模糊需求 → 探隐
        if clarity == ClarityLevel.FUZZY:
            return FlowPhase.TANYIN, TransitionReason.INTENT_DETECTION

        # 清晰高置信 → 启枢
        if clarity == ClarityLevel.CLEAR and intent_result.confidence > 0.8:
            return FlowPhase.QISHU, TransitionReason.INTENT_DETECTION

        # 默认 → 通道首阶段
        channel_phases = CHANNEL_PHASES.get(channel, CHANNEL_PHASES["standard"])
        first_phase = channel_phases[0] if channel_phases else FlowPhase.QISHU
        return first_phase, TransitionReason.INTENT_DETECTION

    def _route_advance(
        self,
        current_phase: FlowPhase,
        intent_result: IntentAnalysisResult,
        channel: str,
        phase_completion: Dict[str, float],
    ) -> tuple:
        """当前阶段完成后的前进路由"""
        channel_phases = CHANNEL_PHASES.get(channel, CHANNEL_PHASES["standard"])
        intent_target = self.intent_to_phase(intent_result.intent)

        # 意图跳转（只允许前进 1 步或回退）
        if current_phase in channel_phases and intent_target in channel_phases:
            current_idx = channel_phases.index(current_phase)
            target_idx = channel_phases.index(intent_target)
            if target_idx <= current_idx + 1 and self._check_capability(intent_target):
                return intent_target, TransitionReason.INTENT_DIRECT

        # 通道顺序前进
        if current_phase in channel_phases:
            current_idx = channel_phases.index(current_phase)
            # 找下一个能力支持的阶段
            for i in range(current_idx + 1, len(channel_phases)):
                candidate = channel_phases[i]
                if self._check_capability(candidate):
                    return candidate, TransitionReason.CHANNEL_NEXT
            return FlowPhase.COMPLETED, TransitionReason.CHANNEL_NEXT

        # 不在通道中 → 使用默认前进映射
        next_phase = self.DEFAULT_PROGRESSION.get(current_phase, current_phase)
        if self._check_capability(next_phase):
            return next_phase, TransitionReason.COMPLETION_ADVANCE

        return current_phase, TransitionReason.STAY

    def get_suggested_next_phase(self, current_phase: FlowPhase, channel: str) -> FlowPhase:
        """获取建议的下一阶段（用于 UI 提示）"""
        channel_phases = CHANNEL_PHASES.get(channel, CHANNEL_PHASES["standard"])

        if current_phase in channel_phases:
            current_idx = channel_phases.index(current_phase)
            if current_idx + 1 < len(channel_phases):
                return channel_phases[current_idx + 1]

        return self.DEFAULT_PROGRESSION.get(current_phase, current_phase)

    @staticmethod
    def phase_index(phase: FlowPhase) -> int:
        try:
            return PHASE_ORDER.index(phase)
        except ValueError:
            return 0

    @staticmethod
    def intent_to_phase(intent: UserIntent) -> FlowPhase:
        return INTENT_PHASE_MAP.get(intent, FlowPhase.QISHU)

    @staticmethod
    def workflow_to_phase(workflow: str) -> FlowPhase:
        mapping = {
            "qishu": FlowPhase.QISHU,
            "tanyin": FlowPhase.TANYIN,
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
            FlowPhase.TANYIN: UserIntent.TANYIN,
            FlowPhase.CAIHENG: UserIntent.CAIHENG,
            FlowPhase.ZHENWEI: UserIntent.ZHENWEI,
            FlowPhase.CESHU: UserIntent.CESHU,
            FlowPhase.NINGMO: UserIntent.NINGMO,
        }
        return mapping.get(phase, UserIntent.CHAT)
