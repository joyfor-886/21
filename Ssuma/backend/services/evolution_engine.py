"""自我进化引擎 (Self-Evolution Engine) — 反射-微调模式

三层记忆架构的第三层：进化记忆。
从项目完成后的指标中自动提炼经验，微调系统参数。

设计参考：
  - DeerFlow: LLM 驱动的长期记忆，自动总结项目经验
  - Reflexion: 输出→反思→纠正→再输出的自精炼循环
  - NeoLabHQ/kaizen: 渐进式改善哲学

核心机制（简化版）：
  1. 反射（Reflect）：项目完成后，分析本次流程指标
  2. 提炼（Distill）：从指标中识别瓶颈和改进点
  3. 微调（Tune）：自动调整阈值/prompt，LOW 风险直接应用
  4. 记录（Record）：所有变更写入进化日志，可审计可回滚

与旧版的区别：
  - 旧版：observe_and_propose() 从未被调用（死代码）
  - 新版：reflect_and_tune() 在项目完成时自动触发
  - 旧版：MEDIUM/HIGH 风险需人工审核（实际无人审核）
  - 新版：只做 LOW 风险微调（阈值±0.05），HIGH 风险仅记录建议
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import json
import logging
import copy

logger = logging.getLogger('Ssuma.Evolution')


class EvolutionType(Enum):
    PROMPT_REFINEMENT = "prompt_refinement"
    THRESHOLD_ADJUSTMENT = "threshold_adjustment"
    DIMENSION_ADDITION = "dimension_addition"
    ROUTE_OPTIMIZATION = "route_optimization"
    CHANNEL_TUNING = "channel_tuning"


class EvolutionRisk(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EvolutionRecord(BaseModel):
    """进化记录 — Pydantic 结构化"""
    id: str
    type: EvolutionType
    risk: EvolutionRisk
    description: str = ""
    rationale: str = ""
    before_state: Dict[str, Any] = Field(default_factory=dict)
    after_state: Dict[str, Any] = Field(default_factory=dict)
    metric_before: Dict[str, float] = Field(default_factory=dict)
    metric_after: Dict[str, float] = Field(default_factory=dict)
    auto_applied: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ProjectReflection(BaseModel):
    """项目反思报告 — 项目完成时自动生成"""
    project_id: str
    channel: str = ""
    total_turns: int = 0
    phase_scores: Dict[str, float] = Field(default_factory=dict)
    bottleneck_phase: str = ""
    bottleneck_score: float = 0.0
    fast_phases: List[str] = Field(default_factory=list)
    slow_phases: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class SelfEvolutionEngine:
    """自我进化引擎 — 反射-微调模式

    核心入口：reflect_and_tune(project_id, phase_scores, total_turns)
    在项目完成或阶段转换时调用，自动分析并微调系统参数。
    """

    _evolution_log: List[EvolutionRecord] = []
    _reflections: List[ProjectReflection] = []
    _original_gates_snapshot: Optional[Dict[str, Any]] = None
    _current_config: Dict[str, Any] = {
        "advance_threshold": {
            "qishu": 0.55,
            "tanyin": 0.5,
            "caiheng": 0.5,
            "zhenwei": 0.5,
            "ceshu": 0.5,
            "ningmo": 0.7,
        },
        "channel_config": {
            "fast": ["qishu", "caiheng", "ningmo"],
            "standard": ["qishu", "tanyin", "caiheng", "ceshu", "ningmo"],
            "deep": ["qishu", "tanyin", "caiheng", "zhenwei", "ceshu", "ningmo", "powang", "jianyan"],
        },
    }

    # 速率限制
    MAX_TUNES_PER_DAY = 5
    COOLDOWN_MINUTES = 30
    THRESHOLD_DELTA = 0.05  # 每次微调幅度

    @classmethod
    def reflect_and_tune(
        cls,
        project_id: str,
        phase_scores: Dict[str, float],
        total_turns: int,
        channel: str = "standard",
    ) -> Optional[EvolutionRecord]:
        """项目完成后自动反射并微调

        这是进化的唯一入口。在 FlowService 检测到项目完成时调用。
        只做 LOW 风险微调（阈值±0.05），HIGH 风险仅记录建议。
        """
        # 1. 反射：识别瓶颈
        reflection = cls._reflect(project_id, phase_scores, total_turns, channel)
        cls._reflections.append(reflection)

        # 2. 速率检查
        if not cls._check_rate_limit():
            logger.info("Evolution rate limit reached, skipping tune")
            return None

        # 3. 微调：只做 LOW 风险的阈值调整
        if reflection.bottleneck_phase and reflection.bottleneck_score < 0.4:
            record = cls._tune_threshold(
                reflection.bottleneck_phase,
                delta=-cls.THRESHOLD_DELTA,
                rationale=f"阶段 {reflection.bottleneck_phase} 平均完成度仅 {reflection.bottleneck_score:.0%}，降低前进阈值",
                metric_before=phase_scores,
            )
            if record:
                cls._evolution_log.append(record)
                cls._apply_change(record)
                logger.info(f"Auto-tuned: {record.description}")
                return record

        # 4. 如果所有阶段都很快完成，可以适当提高阈值
        if reflection.fast_phases and total_turns < 5:
            phase = reflection.fast_phases[0]
            record = cls._tune_threshold(
                phase,
                delta=cls.THRESHOLD_DELTA,
                rationale=f"阶段 {phase} 完成过快（{total_turns} 轮），提高前进阈值以获取更充分讨论",
                metric_before=phase_scores,
            )
            if record:
                cls._evolution_log.append(record)
                cls._apply_change(record)
                logger.info(f"Auto-tuned: {record.description}")
                return record

        return None

    @classmethod
    def _reflect(
        cls,
        project_id: str,
        phase_scores: Dict[str, float],
        total_turns: int,
        channel: str,
    ) -> ProjectReflection:
        """反射：从指标中识别瓶颈和改进点"""
        bottleneck_phase = ""
        bottleneck_score = 1.0
        fast_phases = []
        slow_phases = []

        for phase, score in phase_scores.items():
            if score < bottleneck_score:
                bottleneck_score = score
                bottleneck_phase = phase
            if score >= 0.8:
                fast_phases.append(phase)
            if score < 0.5:
                slow_phases.append(phase)

        suggestions = []
        if bottleneck_score < 0.4:
            suggestions.append(f"考虑降低 {bottleneck_phase} 的前进阈值")
        if total_turns > 20:
            suggestions.append("对话轮数偏多，考虑优化路由减少冗余阶段")
        if len(slow_phases) > 2:
            suggestions.append("多个阶段完成度低，考虑调整通道配置")

        return ProjectReflection(
            project_id=project_id,
            channel=channel,
            total_turns=total_turns,
            phase_scores=phase_scores,
            bottleneck_phase=bottleneck_phase,
            bottleneck_score=bottleneck_score,
            fast_phases=fast_phases,
            slow_phases=slow_phases,
            suggestions=suggestions,
        )

    @classmethod
    def _tune_threshold(
        cls,
        phase: str,
        delta: float,
        rationale: str,
        metric_before: Dict[str, float],
    ) -> Optional[EvolutionRecord]:
        """微调阈值 — LOW 风险，自动应用"""
        import uuid

        current = cls._current_config["advance_threshold"].get(phase, 0.5)
        new_value = max(0.3, min(0.9, current + delta))

        return EvolutionRecord(
            id=str(uuid.uuid4()),
            type=EvolutionType.THRESHOLD_ADJUSTMENT,
            risk=EvolutionRisk.LOW,
            description=f"调整 {phase} 前进阈值: {current:.2f} → {new_value:.2f}",
            rationale=rationale,
            before_state={"advance_threshold": {phase: current}},
            after_state={"advance_threshold": {phase: new_value}},
            metric_before=metric_before,
            auto_applied=True,
        )

    @classmethod
    def _apply_change(cls, record: EvolutionRecord) -> None:
        """执行微调变更"""
        if record.type == EvolutionType.THRESHOLD_ADJUSTMENT:
            new_thresholds = record.after_state.get("advance_threshold", {})
            cls._current_config["advance_threshold"].update(new_thresholds)
            from services.phase_gates import PhaseCompletionGate
            if cls._original_gates_snapshot is None:
                cls._original_gates_snapshot = copy.deepcopy(PhaseCompletionGate.GATES)
            for phase_key, threshold in new_thresholds.items():
                if phase_key in PhaseCompletionGate.GATES:
                    PhaseCompletionGate.GATES[phase_key]["advance_threshold"] = threshold

    @classmethod
    def _check_rate_limit(cls) -> bool:
        """检查速率限制"""
        now = datetime.now()
        recent = [
            r for r in cls._evolution_log
            if r.created_at
            and (now - datetime.fromisoformat(r.created_at)).total_seconds() < 86400
        ]
        if len(recent) >= cls.MAX_TUNES_PER_DAY:
            return False
        if recent:
            last = max(datetime.fromisoformat(r.created_at) for r in recent)
            if (now - last).total_seconds() < cls.COOLDOWN_MINUTES * 60:
                return False
        return True

    @classmethod
    def get_evolution_log(cls) -> List[Dict[str, Any]]:
        """获取进化日志（审计用）"""
        return [r.model_dump() for r in cls._evolution_log]

    @classmethod
    def get_reflections(cls, limit: int = 20) -> List[Dict[str, Any]]:
        """获取项目反思记录"""
        return [r.model_dump() for r in cls._reflections[-limit:]]

    @classmethod
    def get_current_config(cls) -> Dict[str, Any]:
        """获取当前配置"""
        return copy.deepcopy(cls._current_config)

    @classmethod
    def get_safety_report(cls) -> Dict[str, Any]:
        """获取安全报告"""
        return {
            "total_tunes": len(cls._evolution_log),
            "total_reflections": len(cls._reflections),
            "auto_applied": sum(1 for r in cls._evolution_log if r.auto_applied),
            "rate_limit_per_day": cls.MAX_TUNES_PER_DAY,
            "threshold_delta": cls.THRESHOLD_DELTA,
            "current_thresholds": copy.deepcopy(cls._current_config["advance_threshold"]),
        }

    @classmethod
    def reset_to_defaults(cls) -> None:
        """重置到默认配置"""
        cls._current_config = {
            "advance_threshold": {
                "qishu": 0.55,
                "tanyin": 0.5,
                "caiheng": 0.5,
                "zhenwei": 0.5,
                "ceshu": 0.5,
                "ningmo": 0.7,
            },
            "channel_config": {
                "fast": ["qishu", "caiheng", "ningmo"],
                "standard": ["qishu", "tanyin", "caiheng", "zhenwei", "ningmo"],
                "deep": ["qishu", "tanyin", "caiheng", "zhenwei", "ceshu", "powang", "ningmo"],
            },
        }
        if cls._original_gates_snapshot is not None:
            from services.phase_gates import PhaseCompletionGate
            PhaseCompletionGate.GATES = copy.deepcopy(cls._original_gates_snapshot)
            cls._original_gates_snapshot = None
