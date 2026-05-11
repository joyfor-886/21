"""阶段完成度评估器 — Phase Completion Gate

核心思想：每个阶段定义明确的完成条件，基于内容覆盖度而非轮数。
参考 Garry Tan /gstack 的角色分离模式 + NeoLabHQ/reflexion 自精炼循环。
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
import re

logger = logging.getLogger('Ssuma.PhaseGates')


@dataclass
class CompletionResult:
    """阶段完成度评估结果"""
    phase: str
    score: float  # 0.0 - 1.0
    dimensions_covered: List[str] = field(default_factory=list)
    dimensions_missing: List[str] = field(default_factory=list)
    should_advance: bool = False
    reasoning: str = ""
    next_questions: List[str] = field(default_factory=list)


class PhaseCompletionGate:
    """阶段完成度评估器

    借鉴 gstack 的三重审查模式（CEO/Eng/Design Review），
    每个阶段定义必须覆盖的维度，未达标不允许前进。
    """

    # 每个阶段的必需维度定义
    GATES = {
        "qishu": {
            "required_dimensions": {
                "demand_reality": {
                    "label": "真实需求",
                    "description": "是否找到了真实需求的证据？（付费意愿/愤怒/痛点）",
                    "keywords": ["付费", "痛点", "需求", "问题", "愿望", "愤怒", "困扰", "麻烦", "需求证据"],
                    "weight": 0.25,
                },
                "status_quo": {
                    "label": "现状方案",
                    "description": "是否了解了用户当前的解决方案？",
                    "keywords": ["现在", "目前", "替代", "现状", "解决方案", "现有", "手动", "Excel", "手动操作"],
                    "weight": 0.20,
                },
                "narrowest_wedge": {
                    "label": "最窄切入点",
                    "description": "是否确定了最小切入点/MVP？",
                    "keywords": ["最小", "MVP", "切入点", "最简", "核心功能", "第一版", "先做", "最小版本"],
                    "weight": 0.25,
                },
                "target_user": {
                    "label": "目标用户",
                    "description": "是否明确了具体的目标用户？",
                    "keywords": ["用户", "目标", "受众", "客户", "谁", "群体", "角色", "具体"],
                    "weight": 0.15,
                },
                "desperate_specificity": {
                    "label": "极度特异性",
                    "description": "是否能够说出一个具体的人名/职位？",
                    "keywords": ["具体", "名字", "职位", "场景", "案例", "举例", "比如"],
                    "weight": 0.15,
                },
            },
            "min_dimensions_covered": 2,
            "min_conversation_turns": 2,
            "advance_threshold": 0.55,
        },
        "questionnaire": {
            "required_dimensions": {
                "basic_info": {"label": "基本信息", "keywords": ["名称", "项目", "类型"], "weight": 0.2},
                "target_audience": {"label": "目标受众", "keywords": ["用户", "受众", "客户"], "weight": 0.2},
                "core_features": {"label": "核心功能", "keywords": ["功能", "特性", "需求"], "weight": 0.3},
                "constraints": {"label": "约束条件", "keywords": ["预算", "时间", "技术", "限制"], "weight": 0.15},
                "success_criteria": {"label": "成功标准", "keywords": ["指标", "目标", "成功", "KPI"], "weight": 0.15},
            },
            "min_dimensions_covered": 3,
            "min_conversation_turns": 2,
            "advance_threshold": 0.5,
        },
        "caiheng": {
            "required_dimensions": {
                "scope_decision": {"label": "范围决策", "keywords": ["范围", "scope", "缩减", "扩展", "保持"], "weight": 0.25},
                "risk_list": {"label": "风险清单", "keywords": ["风险", "隐患", "失败", "问题", "挑战"], "weight": 0.25},
                "value_proposition": {"label": "价值主张", "keywords": ["价值", "核心", "差异化", "独特", "竞争力"], "weight": 0.25},
                "edge_cases": {"label": "边缘情况", "keywords": ["边缘", "异常", "极端", "边界", "空值"], "weight": 0.25},
            },
            "min_dimensions_covered": 2,
            "min_conversation_turns": 2,
            "advance_threshold": 0.5,
        },
        "zhenwei": {
            "required_dimensions": {
                "architecture": {"label": "架构设计", "keywords": ["架构", "系统", "组件", "模块", "分层"], "weight": 0.25},
                "data_model": {"label": "数据模型", "keywords": ["数据", "模型", "数据库", "表", "字段", "Schema"], "weight": 0.20},
                "error_map": {"label": "错误映射", "keywords": ["错误", "异常", "恢复", "重试", "降级"], "weight": 0.20},
                "api_spec": {"label": "接口规范", "keywords": ["API", "接口", "端点", "请求", "响应", "路由"], "weight": 0.20},
                "security": {"label": "安全考量", "keywords": ["安全", "注入", "认证", "授权", "XSS", "CSRF"], "weight": 0.15},
            },
            "min_dimensions_covered": 2,
            "min_conversation_turns": 2,
            "advance_threshold": 0.5,
        },
        "ceshu": {
            "required_dimensions": {
                "task_list": {"label": "任务列表", "keywords": ["Task", "任务", "步骤", "阶段"], "weight": 0.30},
                "file_paths": {"label": "文件路径", "keywords": ["文件", "path", "创建", "修改", "NEW", "MODIFY"], "weight": 0.25},
                "tdd_steps": {"label": "TDD步骤", "keywords": ["测试", "test", "断言", "assert", "验证"], "weight": 0.25},
                "verification": {"label": "验证标准", "keywords": ["验证", "通过", "成功", "确认", "检查"], "weight": 0.20},
            },
            "min_dimensions_covered": 2,
            "min_conversation_turns": 1,
            "advance_threshold": 0.5,
        },
        "ningmo": {
            "required_dimensions": {
                "product_definition": {"label": "产品定义", "keywords": ["产品", "核心问题", "切入点", "目标"], "weight": 0.25},
                "architecture_design": {"label": "架构设计", "keywords": ["架构", "数据模型", "API", "技术"], "weight": 0.25},
                "risk_mitigation": {"label": "风险缓解", "keywords": ["风险", "缓解", "规避", "方案"], "weight": 0.25},
                "execution_plan": {"label": "执行步骤", "keywords": ["Task", "步骤", "TDD", "测试"], "weight": 0.25},
            },
            "min_dimensions_covered": 3,
            "min_conversation_turns": 0,
            "advance_threshold": 0.7,
        },
    }

    @classmethod
    def evaluate(
        cls,
        phase: str,
        conversation: str,
        conversation_turns: int = 0,
    ) -> CompletionResult:
        """基于规则评估当前阶段的完成度

        不依赖额外 LLM 调用，纯规则匹配 + 权重计算，
        确保低延迟、可预测、可调试。
        """
        gate = cls.GATES.get(phase)
        if not gate:
            return CompletionResult(
                phase=phase,
                score=1.0,
                should_advance=True,
                reasoning="未定义完成条件的阶段，默认通过",
            )

        dimensions_covered = []
        dimensions_missing = []
        dimension_scores = {}

        for dim_key, dim_config in gate["required_dimensions"].items():
            score = cls._evaluate_dimension(conversation, dim_config)
            dimension_scores[dim_key] = score
            if score >= 0.3:  # 一个维度至少匹配到一些关键词才算覆盖
                dimensions_covered.append(dim_key)
            else:
                dimensions_missing.append(dim_key)

        # 加权总分
        total_score = sum(
            dimension_scores.get(k, 0) * v["weight"]
            for k, v in gate["required_dimensions"].items()
        )

        # 轮数惩罚：如果轮数不足，压低分数
        if conversation_turns < gate["min_conversation_turns"]:
            turn_penalty = 0.15 * (gate["min_conversation_turns"] - conversation_turns)
            total_score = max(0, total_score - turn_penalty)

        # 覆盖维度数不足，也压低
        if len(dimensions_covered) < gate["min_dimensions_covered"]:
            total_score *= 0.7

        should_advance = (
            total_score >= gate["advance_threshold"]
            and len(dimensions_covered) >= gate["min_dimensions_covered"]
            and conversation_turns >= gate["min_conversation_turns"]
        )

        reasoning = cls._build_reasoning(
            phase, total_score, dimensions_covered, dimensions_missing, dimension_scores, gate
        )
        next_questions = cls._suggest_next_questions(phase, dimensions_missing)

        return CompletionResult(
            phase=phase,
            score=round(total_score, 3),
            dimensions_covered=dimensions_covered,
            dimensions_missing=dimensions_missing,
            should_advance=should_advance,
            reasoning=reasoning,
            next_questions=next_questions,
        )

    @classmethod
    def _evaluate_dimension(cls, conversation: str, dim_config: dict) -> float:
        """评估单个维度的覆盖度"""
        conv_lower = conversation.lower()
        keywords = dim_config.get("keywords", [])

        if not keywords:
            return 0.0

        matches = sum(1 for kw in keywords if kw.lower() in conv_lower)
        # 至少匹配2个关键词才算较好覆盖
        if matches == 0:
            return 0.0
        elif matches == 1:
            return 0.3
        elif matches == 2:
            return 0.6
        elif matches == 3:
            return 0.8
        else:
            return 1.0

    @classmethod
    def _build_reasoning(
        cls, phase, total_score, covered, missing, dim_scores, gate
    ) -> str:
        parts = [f"阶段 {phase} 完成度: {total_score:.0%}"]
        parts.append(f"已覆盖维度: {', '.join(covered) if covered else '无'}")
        if missing:
            parts.append(f"未覆盖维度: {', '.join(missing)}")
        parts.append(
            f"前进条件: 覆盖 ≥{gate['min_dimensions_covered']}个维度, "
            f"分数 ≥{gate['advance_threshold']:.0%}"
        )
        return " | ".join(parts)

    @classmethod
    def _suggest_next_questions(cls, phase: str, missing_dims: List[str]) -> List[str]:
        """为缺失的维度建议下一个问题（参考 YC Office Hours 风格）"""
        suggestions = {
            "qishu": {
                "demand_reality": "你的用户目前为解决这个痛点花了多少时间/金钱？",
                "status_quo": "用户现在是用什么蹩脚的方法在解决这个问题？",
                "narrowest_wedge": "如果本周就要让一个人付费，最小版本长什么样？",
                "target_user": "能否说出一个具体的人名和职位，ta 就是你的第一批用户？",
                "desperate_specificity": "给我一个具体的场景——谁、在什么时候、遇到了什么问题？",
            },
            "caiheng": {
                "scope_decision": "这个产品的范围应该扩大、缩减还是保持？为什么？",
                "risk_list": "列举 2-3 个最大的产品/技术风险。",
                "value_proposition": "一句话说清楚：你的产品为什么比现有方案好 10 倍？",
                "edge_cases": "如果用户输入为空、超长、或含特殊字符，系统会怎样？",
            },
            "zhenwei": {
                "architecture": "请描述系统的高层架构和核心组件。",
                "data_model": "请给出核心数据模型/数据库表结构。",
                "error_map": "每个外部调用失败时，用户看到什么？系统如何恢复？",
                "api_spec": "请列出核心 API 端点和请求/响应格式。",
                "security": "有哪些注入/认证/授权风险？",
            },
            "ceshu": {
                "task_list": "请将方案拆分为具体的开发任务。",
                "file_paths": "每个任务涉及哪些文件？请给出完整路径。",
                "tdd_steps": "每个任务的测试先行步骤是什么？",
                "verification": "如何验证每个任务正确完成？",
            },
            "ningmo": {
                "product_definition": "请确认产品的核心问题和切入点。",
                "architecture_design": "请确认系统架构和数据模型设计。",
                "risk_mitigation": "请确认风险缓解策略。",
                "execution_plan": "请确认执行步骤和TDD计划。",
            },
        }
        phase_suggestions = suggestions.get(phase, {})
        return [phase_suggestions.get(d, f"请补充 {d} 相关的信息") for d in missing_dims]
