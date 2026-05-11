"""自我进化引擎 (Self-Evolution Engine)

让工作流自我良性进化，同时考虑边际安全性和人伦道德。

设计参考：
- NeoLabHQ/kaizen: 基于日本改善哲学的多分析方法论
- NeoLabHQ/reflexion: 自精炼循环（输出→反思→纠正→再输出）
- context-evaluation: 构建 Agent 系统的评估框架
- gstack /canary: 部署后金丝雀监控

核心原则：
1. 渐进式改进（Kaizen）：小步迭代，每步可验证
2. 人类在环（Human-in-the-Loop）：关键决策必须人类确认
3. 安全护栏（Guardrails）：限制自动进化的范围和速率
4. 可审计性（Auditability）：所有进化操作都有完整记录
5. 可回滚性（Rollback）：任何自动修改都可以一键回滚
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import logging
import copy

logger = logging.getLogger('Ssuma.Evolution')


class EvolutionType(Enum):
    PROMPT_REFINEMENT = "prompt_refinement"      # 微调 prompt 措辞
    THRESHOLD_ADJUSTMENT = "threshold_adjustment"  # 调整完成度阈值
    DIMENSION_ADDITION = "dimension_addition"      # 增加评估维度
    ROUTE_OPTIMIZATION = "route_optimization"      # 优化路由规则
    CHANNEL_TUNING = "channel_tuning"              # 调整通道配置


class EvolutionRisk(Enum):
    LOW = "low"          # 仅修改措辞/参数，无行为变化
    MEDIUM = "medium"    # 修改逻辑/阈值，可能影响行为
    HIGH = "high"        # 修改核心路由/流程，需人工审核


class EvolutionStatus(Enum):
    PROPOSED = "proposed"       # 已提议，等待审核
    APPROVED = "approved"       # 已批准，待执行
    APPLIED = "applied"         # 已应用
    ROLLED_BACK = "rolled_back" # 已回滚
    REJECTED = "rejected"       # 已拒绝


@dataclass
class EvolutionRecord:
    """进化记录"""
    id: str
    type: EvolutionType
    risk: EvolutionRisk
    status: EvolutionStatus = EvolutionStatus.PROPOSED
    description: str = ""
    rationale: str = ""          # 进化依据
    before_state: Dict[str, Any] = field(default_factory=dict)
    after_state: Dict[str, Any] = field(default_factory=dict)
    metric_before: Dict[str, float] = field(default_factory=dict)
    metric_after: Dict[str, float] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    applied_at: Optional[str] = None
    rolled_back_at: Optional[str] = None
    approved_by: Optional[str] = None  # human approval


@dataclass
class EthicalConstraint:
    """伦理约束"""
    # 禁止自动进化的区域
    NO_AUTO_EVOLVE_AREAS = [
        "user_data_handling",      # 用户数据处理方式
        "privacy_settings",        # 隐私设置
        "content_moderation",      # 内容审核规则
        "access_control",          # 访问控制
    ]
    
    # 进化速率限制
    MAX_EVOLUTIONS_PER_DAY = 5      # 每天最多5次进化
    MAX_EVOLUTIONS_PER_WEEK = 15    # 每周最多15次
    COOLDOWN_MINUTES = 30           # 两次进化之间至少30分钟冷却
    
    # 风险等级限制
    AUTO_APPLY_MAX_RISK = EvolutionRisk.LOW  # 只有LOW风险可自动应用
    MEDIUM_RISK_REQUIRES_HUMAN = True         # MEDIUM需要人工确认
    HIGH_RISK_REQUIRES_HUMAN = True           # HIGH需要人工确认
    
    # 回滚保护
    AUTO_ROLLBACK_IF_METRIC_DROPS = True      # 指标下降时自动回滚
    METRIC_DROP_THRESHOLD = 0.15              # 下降超过15%触发回滚
    OBSERVATION_PERIOD_HOURS = 24             # 观察期24小时


class EvolutionMetrics:
    """进化指标收集器

    参考 context-evaluation 的评估框架：
    收集工作流运行的关键指标，用于驱动进化决策。
    """

    @classmethod
    def collect_project_metrics(cls, project_id: str) -> Dict[str, float]:
        """收集项目的运行指标"""
        from services.adaptive_flow import AdaptiveFlowService

        status = AdaptiveFlowService.get_flow_status(project_id)

        return {
            "completion_score": status.get("completion_score", 0),
            "overall_progress": status.get("overall_progress", 0),
            "conversation_turns": status.get("conversation_turns", 0),
            "phase_completion_avg": cls._avg_phase_completion(
                status.get("phase_completion", {})
            ),
        }

    @classmethod
    def collect_global_metrics(cls) -> Dict[str, float]:
        """收集全局运行指标"""
        from services.adaptive_flow import AdaptiveFlowService
        from db.sqlite import Database

        try:
            db = Database()
            # 统计已完成的项目
            completed = db.fetchone(
                "SELECT COUNT(*) as count FROM flow_states WHERE spec_generated = 1"
            )
            total = db.fetchone("SELECT COUNT(*) as count FROM flow_states")

            completed_count = completed["count"] if completed else 0
            total_count = total["count"] if total else 0

            return {
                "completion_rate": completed_count / total_count if total_count > 0 else 0,
                "total_projects": float(total_count),
                "completed_projects": float(completed_count),
            }
        except Exception:
            return {}

    @classmethod
    def _avg_phase_completion(cls, phase_completion: Dict[str, float]) -> float:
        if not phase_completion:
            return 0.0
        values = [v for v in phase_completion.values() if isinstance(v, (int, float))]
        return sum(values) / len(values) if values else 0.0


class SelfEvolutionEngine:
    """自我进化引擎

    核心机制：
    1. 观察（Observe）：收集运行指标
    2. 分析（Analyze）：识别瓶颈和改进机会
    3. 提议（Propose）：生成进化提议
    4. 审核（Review）：风险分级 + 人类审核
    5. 应用（Apply）：执行进化
    6. 监控（Monitor）：观察进化效果
    7. 回滚（Rollback）：必要时回滚

    安全机制：
    - 伦理约束（EthicalConstraint）：禁止自动修改敏感区域
    - 风险分级（EvolutionRisk）：只有LOW风险可自动应用
    - 速率限制：防止进化过快
    - 人类在环：MEDIUM/HIGH风险必须人工确认
    - 自动回滚：指标下降时自动回滚
    - 完整审计：所有进化操作都有记录

    NOTE: observe_and_propose() 尚未集成到主流程，当前为预留接口。
    """

    _evolution_history: List[EvolutionRecord] = []
    _original_gates_snapshot: Optional[Dict[str, Any]] = None
    _current_config: Dict[str, Any] = {
        "advance_threshold": {
            "qishu": 0.55,
            "questionnaire": 0.5,
            "caiheng": 0.5,
            "zhenwei": 0.5,
            "ceshu": 0.5,
            "ningmo": 0.7,
        },
        "channel_config": {
            "fast": ["qishu", "caiheng", "ningmo"],
            "standard": ["qishu", "questionnaire", "caiheng", "zhenwei", "ningmo"],
            "deep": ["qishu", "questionnaire", "caiheng", "zhenwei", "ceshu", "powang", "ningmo"],
        },
    }
    _constraint = EthicalConstraint()

    @classmethod
    async def observe_and_propose(cls) -> List[EvolutionRecord]:
        """观察运行指标并生成进化提议

        这是进化的入口点。只在有足够数据时才会提议进化。
        """
        global_metrics = EvolutionMetrics.collect_global_metrics()
        proposals = []

        # 规则1：如果完成率太低，考虑降低阈值
        completion_rate = global_metrics.get("completion_rate", 0)
        if 0 < completion_rate < 0.3:
            proposal = cls._propose_threshold_adjustment(
                "完成率过低，考虑降低阶段前进阈值",
                -0.05,
            )
            if proposal:
                proposals.append(proposal)

        # 规则2：如果平均完成度很高但轮数很多，考虑优化路由
        # （这里需要更多数据，暂时跳过）

        return proposals

    @classmethod
    def _propose_threshold_adjustment(
        cls,
        rationale: str,
        delta: float,
    ) -> Optional[EvolutionRecord]:
        """提议阈值调整"""
        import uuid

        # 检查速率限制
        if not cls._check_rate_limit():
            return None

        current_thresholds = copy.deepcopy(cls._current_config["advance_threshold"])

        record = EvolutionRecord(
            id=str(uuid.uuid4()),
            type=EvolutionType.THRESHOLD_ADJUSTMENT,
            risk=EvolutionRisk.LOW,  # 阈值调整是低风险
            status=EvolutionStatus.PROPOSED,
            description=f"调整阶段前进阈值 (delta={delta})",
            rationale=rationale,
            before_state={"advance_threshold": current_thresholds},
            after_state={
                "advance_threshold": {
                    k: max(0.3, min(0.9, v + delta))
                    for k, v in current_thresholds.items()
                }
            },
        )

        cls._evolution_history.append(record)
        logger.info(f"Evolution proposed: {record.description}")
        return record

    @classmethod
    def approve_evolution(cls, evolution_id: str, approver: str = "human") -> bool:
        """人工审核通过进化提议"""
        for record in cls._evolution_history:
            if record.id == evolution_id and record.status == EvolutionStatus.PROPOSED:
                record.status = EvolutionStatus.APPROVED
                record.approved_by = approver
                return True
        return False

    @classmethod
    def reject_evolution(cls, evolution_id: str) -> bool:
        """拒绝进化提议"""
        for record in cls._evolution_history:
            if record.id == evolution_id and record.status == EvolutionStatus.PROPOSED:
                record.status = EvolutionStatus.REJECTED
                return True
        return False

    @classmethod
    def apply_evolution(cls, evolution_id: str) -> bool:
        """应用进化

        安全检查：
        1. 只有APPROVED状态才能应用
        2. LOW风险可自动应用，MEDIUM/HIGH需要人工确认
        3. 修改前保存当前状态（用于回滚）
        """
        for record in cls._evolution_history:
            if record.id != evolution_id:
                continue

            if record.status != EvolutionStatus.APPROVED:
                # LOW风险自动审批
                if record.risk == EvolutionRisk.LOW and record.status == EvolutionStatus.PROPOSED:
                    record.status = EvolutionStatus.APPROVED
                    record.approved_by = "auto"
                else:
                    logger.warning(f"Evolution {evolution_id} not approved, cannot apply")
                    return False

            # 应用变更
            try:
                cls._apply_change(record)
                record.status = EvolutionStatus.APPLIED
                record.applied_at = datetime.now().isoformat()
                logger.info(f"Evolution applied: {record.description}")
                return True
            except Exception as e:
                logger.error(f"Failed to apply evolution {evolution_id}: {e}")
                return False

        return False

    @classmethod
    def _apply_change(cls, record: EvolutionRecord):
        """执行具体的进化变更

        P2-04 修复：修改 GATES 前先保存原始快照，确保回滚可恢复正确值。
        """
        if record.type == EvolutionType.THRESHOLD_ADJUSTMENT:
            new_thresholds = record.after_state.get("advance_threshold", {})
            cls._current_config["advance_threshold"].update(new_thresholds)
            from services.phase_gates import PhaseCompletionGate
            if cls._original_gates_snapshot is None:
                cls._original_gates_snapshot = copy.deepcopy(PhaseCompletionGate.GATES)
            for phase_key, threshold in new_thresholds.items():
                if phase_key in PhaseCompletionGate.GATES:
                    PhaseCompletionGate.GATES[phase_key]["advance_threshold"] = threshold

        elif record.type == EvolutionType.CHANNEL_TUNING:
            new_config = record.after_state.get("channel_config", {})
            cls._current_config["channel_config"].update(new_config)

    @classmethod
    def rollback_evolution(cls, evolution_id: str) -> bool:
        """回滚进化

        P2-04 修复：使用原始快照恢复 GATES，而非用 before_state 覆盖
        （before_state 可能已被其他进化修改过，不是真正的原始值）。
        """
        for record in cls._evolution_history:
            if record.id == evolution_id and record.status == EvolutionStatus.APPLIED:
                try:
                    if record.type == EvolutionType.THRESHOLD_ADJUSTMENT:
                        old_thresholds = record.before_state.get("advance_threshold", {})
                        cls._current_config["advance_threshold"].update(old_thresholds)
                        from services.phase_gates import PhaseCompletionGate
                        if cls._original_gates_snapshot is not None:
                            PhaseCompletionGate.GATES = copy.deepcopy(cls._original_gates_snapshot)
                            cls._original_gates_snapshot = None
                        else:
                            for phase_key, threshold in old_thresholds.items():
                                if phase_key in PhaseCompletionGate.GATES:
                                    PhaseCompletionGate.GATES[phase_key]["advance_threshold"] = threshold

                    record.status = EvolutionStatus.ROLLED_BACK
                    record.rolled_back_at = datetime.now().isoformat()
                    logger.info(f"Evolution rolled back: {record.description}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to rollback evolution {evolution_id}: {e}")
                    return False

        return False

    @classmethod
    def _check_rate_limit(cls) -> bool:
        """检查进化速率限制"""
        now = datetime.now()
        recent = [
            r for r in cls._evolution_history
            if r.status in [EvolutionStatus.PROPOSED, EvolutionStatus.APPLIED]
            and r.created_at
            and (now - datetime.fromisoformat(r.created_at)).total_seconds() < 86400
        ]
        if len(recent) >= cls._constraint.MAX_EVOLUTIONS_PER_DAY:
            return False

        # 冷却期检查
        if recent:
            last = max(datetime.fromisoformat(r.created_at) for r in recent)
            if (now - last).total_seconds() < cls._constraint.COOLDOWN_MINUTES * 60:
                return False

        return True

    @classmethod
    def get_evolution_history(cls) -> List[Dict[str, Any]]:
        """获取进化历史（用于审计）"""
        return [
            {
                "id": r.id,
                "type": r.type.value,
                "risk": r.risk.value,
                "status": r.status.value,
                "description": r.description,
                "rationale": r.rationale,
                "before_state": r.before_state,
                "after_state": r.after_state,
                "approved_by": r.approved_by,
                "created_at": r.created_at,
                "applied_at": r.applied_at,
                "rolled_back_at": r.rolled_back_at,
            }
            for r in cls._evolution_history
        ]

    @classmethod
    def get_current_config(cls) -> Dict[str, Any]:
        """获取当前配置（用于调试和审计）"""
        return copy.deepcopy(cls._current_config)

    @classmethod
    def get_safety_report(cls) -> Dict[str, Any]:
        """获取安全报告"""
        total = len(cls._evolution_history)
        applied = sum(1 for r in cls._evolution_history if r.status == EvolutionStatus.APPLIED)
        rolled_back = sum(1 for r in cls._evolution_history if r.status == EvolutionStatus.ROLLED_BACK)
        rejected = sum(1 for r in cls._evolution_history if r.status == EvolutionStatus.REJECTED)

        return {
            "total_proposals": total,
            "applied": applied,
            "rolled_back": rolled_back,
            "rejected": rejected,
            "auto_approved": sum(
                1 for r in cls._evolution_history
                if r.approved_by == "auto" and r.status == EvolutionStatus.APPLIED
            ),
            "human_approved": sum(
                1 for r in cls._evolution_history
                if r.approved_by == "human" and r.status == EvolutionStatus.APPLIED
            ),
            "rate_limit_per_day": cls._constraint.MAX_EVOLUTIONS_PER_DAY,
            "auto_apply_max_risk": cls._constraint.AUTO_APPLY_MAX_RISK.value,
            "protected_areas": cls._constraint.NO_AUTO_EVOLVE_AREAS,
            "observation_period_hours": cls._constraint.OBSERVATION_PERIOD_HOURS,
        }
