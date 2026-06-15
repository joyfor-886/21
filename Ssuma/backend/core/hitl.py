"""Human-in-the-Loop (HITL) — 人工干预机制

参考 LangGraph 的 interrupt/resume 模式和 Pydantic AI 的 ApprovalRequired 模式，
为 Ssuma 提供在关键阶段暂停等待人工确认的能力。

设计原则：
1. 非阻塞 — 暂停时不阻塞服务器，而是将中断状态持久化，等待前端响应
2. 可配置 — 每个阶段可独立配置是否需要人工确认
3. 多种响应 — 支持 accept/ignore/response/edit 四种人工响应
4. 自动触发 — 在裁衡、甄微等关键决策点自动触发

触发条件（默认）：
  - 裁衡(caiheng)：产品价值评审结论需确认
  - 甄微(zhenwei)：技术选型方案需确认
  - 凝墨(ningmo)：最终方案产出需确认
  - MCP 工具调用：高风险操作需确认

数据流：
  1. EvaluationMiddleware 检测到需要 HITL → 创建 HumanInterrupt 记录
  2. process_message_stream 返回 interrupt 信息给前端
  3. 前端展示确认界面，用户操作后调用 /mcp/hitl/respond API
  4. FlowService 恢复流程，将人工响应注入上下文继续生成
"""

from __future__ import annotations

import json
import time
import logging
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field
from core.state_repository import StateRepository

logger = logging.getLogger('Ssuma.HITL')


# ===== 数据模型 =====


class HITLConfig(BaseModel):
    """HITL 配置 — 每个阶段的确认策略"""
    # 阶段级开关
    phases: Dict[str, bool] = Field(default_factory=lambda: {
        "caiheng": True,   # 裁衡：产品价值评审
        "zhenwei": True,   # 甄微：技术选型
        "ningmo": True,    # 凝墨：最终方案
    })
    # MCP 工具调用确认
    mcp_tool_approval: bool = True
    # 完成度阈值 — 只有完成度超过此值才触发确认
    completion_threshold: float = 0.5
    # 超时（秒）— 超时后自动继续
    timeout_seconds: int = 0  # 0 = 不超时


class HumanInterrupt(BaseModel):
    """人工中断记录 — 表示一个等待人工响应的暂停点"""
    id: str = Field(default_factory=lambda: f"hitl_{int(time.time()*1000)}")
    project_id: str
    phase: str
    reason: str  # 为什么需要人工确认
    content: str  # 需要确认的内容摘要
    options: List[str] = Field(default_factory=lambda: ["accept", "ignore", "response"])
    # 允许的操作
    allow_accept: bool = True
    allow_ignore: bool = True
    allow_response: bool = True
    allow_edit: bool = False
    # 状态
    status: Literal["pending", "responded", "expired"] = "pending"
    # 人工响应
    response_type: Optional[Literal["accept", "ignore", "response", "edit"]] = None
    response_content: Optional[str] = None
    # 时间
    created_at: float = Field(default_factory=time.time)
    responded_at: Optional[float] = None
    # 关联的流程上下文
    flow_context_snapshot: Optional[Dict[str, Any]] = None

    @property
    def is_pending(self) -> bool:
        return self.status == "pending"

    def respond(
        self,
        response_type: Literal["accept", "ignore", "response", "edit"],
        content: Optional[str] = None,
    ):
        """记录人工响应"""
        self.status = "responded"
        self.response_type = response_type
        self.response_content = content
        self.responded_at = time.time()


class HITLStore:
    """HITL 状态持久化 — 基于 StateRepository"""

    STATE_KEY = "hitl_interrupts"
    _known_projects: set = set()

    @classmethod
    def save_interrupt(cls, interrupt: HumanInterrupt):
        """保存中断记录"""
        cls._known_projects.add(interrupt.project_id)
        data = StateRepository.load(cls.STATE_KEY, interrupt.project_id) or {}
        interrupts = data.get("interrupts", {})
        interrupts[interrupt.id] = interrupt.model_dump()
        StateRepository.save(cls.STATE_KEY, interrupt.project_id, {
            "interrupts": interrupts
        })

    @classmethod
    def get_interrupt(cls, interrupt_id: str) -> Optional[HumanInterrupt]:
        """获取中断记录 — 遍历所有项目的持久化数据查找"""
        # StateRepository 不支持全局 list_all，所以按项目查找
        # 从 interrupt_id 中提取可能的 project_id（hitl_{timestamp} 格式无法提取）
        # 改为：从所有已知项目中搜索
        from core.state_repository import StateRepository

        # 尝试从内存缓存中查找
        for project_id_key in getattr(cls, '_known_projects', set()):
            data = StateRepository.load(cls.STATE_KEY, project_id_key)
            if data:
                for int_data in data.get("interrupts", {}).values():
                    if int_data.get("id") == interrupt_id:
                        return HumanInterrupt.model_validate(int_data)
        return None

    @classmethod
    def get_pending_for_project(cls, project_id: str) -> Optional[HumanInterrupt]:
        """获取项目的待处理中断"""
        data = StateRepository.load(cls.STATE_KEY, project_id)
        if not data:
            return None
        interrupts = data.get("interrupts", {})
        for int_data in interrupts.values():
            interrupt = HumanInterrupt.model_validate(int_data)
            if interrupt.is_pending:
                return interrupt
        return None

    @classmethod
    def update_interrupt(cls, interrupt: HumanInterrupt):
        """更新中断记录"""
        cls.save_interrupt(interrupt)

    @classmethod
    def clear_for_project(cls, project_id: str):
        """清除项目的所有中断"""
        cls._known_projects.discard(project_id)
        StateRepository.delete(cls.STATE_KEY, project_id)


# ===== HITL 决策逻辑 =====


class HITLDecider:
    """HITL 决策器 — 判断是否需要触发人工确认"""

    def __init__(self, config: Optional[HITLConfig] = None):
        self.config = config or HITLConfig()

    def should_interrupt(
        self,
        phase: str,
        completion_score: float,
        is_mcp_tool_call: bool = False,
    ) -> Optional[str]:
        """判断是否需要中断

        Returns:
            None = 不需要中断
            str = 需要中断的原因
        """
        # MCP 工具调用确认
        if is_mcp_tool_call and self.config.mcp_tool_approval:
            return "MCP 工具调用需要人工确认"

        # 阶段级确认
        if phase in self.config.phases and self.config.phases[phase]:
            if completion_score >= self.config.completion_threshold:
                phase_labels = {
                    "caiheng": "裁衡·审视",
                    "zhenwei": "甄微·评审",
                    "ningmo": "凝墨·成案",
                }
                label = phase_labels.get(phase, phase)
                return f"{label}阶段结论需要人工确认（完成度 {completion_score:.0%}）"

        return None

    def get_interrupt_options(self, phase: str) -> List[str]:
        """获取该阶段允许的响应选项"""
        options = []
        if self.config.phases.get(phase, False):
            options.extend(["accept", "ignore", "response"])
        return options or ["accept", "ignore", "response"]


# ===== 全局配置 =====

_global_config: Optional[HITLConfig] = None


def get_hitl_config() -> HITLConfig:
    """获取全局 HITL 配置"""
    global _global_config
    if _global_config is None:
        try:
            from core.config import Config
            hitl_conf = Config().get("hitl", {})
            _global_config = HITLConfig(**hitl_conf) if hitl_conf else HITLConfig()
        except Exception:
            _global_config = HITLConfig()
    return _global_config


def get_hitl_decider() -> HITLDecider:
    """获取 HITL 决策器"""
    return HITLDecider(get_hitl_config())
