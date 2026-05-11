from typing import Dict, Any, List, Optional
from enum import Enum
import json
import logging
from core.state_repository import StateRepository

logger = logging.getLogger(__name__)

STATE_SERVICE_NAME = "questionnaire"


class PlanningPhase(Enum):
    QUESTIONNAIRE = "questionnaire"
    ANALYSIS = "analysis"
    UNDERSTANDING = "understanding"
    PLANNING = "planning"
    COMPLETED = "completed"


class QuestionnaireStage(Enum):
    INITIAL = "initial"
    EXPANSION = "expansion"
    CLARIFICATION = "clarification"
    COMPLETED = "completed"


class RequirementDimension:
    TARGET_USER = "target_user"
    CORE_PROBLEM = "core_problem"
    KEY_FEATURES = "key_features"
    SUCCESS_CRITERIA = "success_criteria"
    CONSTRAINTS = "constraints"
    TECH_PREFERENCE = "tech_preference"
    SCOPE = "scope"
    PRIORITY = "priority"


DIMENSION_LABELS = {
    RequirementDimension.TARGET_USER: "目标用户",
    RequirementDimension.CORE_PROBLEM: "核心问题",
    RequirementDimension.KEY_FEATURES: "关键功能",
    RequirementDimension.SUCCESS_CRITERIA: "成功标准",
    RequirementDimension.CONSTRAINTS: "约束条件",
    RequirementDimension.TECH_PREFERENCE: "技术偏好",
    RequirementDimension.SCOPE: "项目范围",
    RequirementDimension.PRIORITY: "优先级",
}

DIMENSION_WEIGHTS = {
    RequirementDimension.TARGET_USER: 20,
    RequirementDimension.CORE_PROBLEM: 25,
    RequirementDimension.KEY_FEATURES: 20,
    RequirementDimension.SUCCESS_CRITERIA: 15,
    RequirementDimension.CONSTRAINTS: 5,
    RequirementDimension.TECH_PREFERENCE: 5,
    RequirementDimension.SCOPE: 5,
    RequirementDimension.PRIORITY: 5,
}

COMPLETENESS_THRESHOLD = 60


class QuestionnaireState:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.current_stage = QuestionnaireStage.INITIAL
        self.planning_phase = PlanningPhase.QUESTIONNAIRE
        self.round = 0
        self.max_rounds = 3
        self.collected_info: Dict[str, Any] = {}
        self.dimension_coverage: Dict[str, bool] = {
            RequirementDimension.TARGET_USER: False,
            RequirementDimension.CORE_PROBLEM: False,
            RequirementDimension.KEY_FEATURES: False,
            RequirementDimension.SUCCESS_CRITERIA: False,
            RequirementDimension.CONSTRAINTS: False,
            RequirementDimension.TECH_PREFERENCE: False,
            RequirementDimension.SCOPE: False,
            RequirementDimension.PRIORITY: False,
        }
        self.original_message: str = ""
        self.completed = False
        self.history: List[Dict[str, Any]] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "current_stage": self.current_stage.value,
            "planning_phase": self.planning_phase.value,
            "round": self.round,
            "max_rounds": self.max_rounds,
            "collected_info": self.collected_info,
            "dimension_coverage": {k: v for k, v in self.dimension_coverage.items()},
            "original_message": self.original_message,
            "completed": self.completed,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuestionnaireState":
        state = cls(data.get("project_id", ""))
        state.current_stage = QuestionnaireStage(data.get("current_stage", "initial"))
        state.planning_phase = PlanningPhase(data.get("planning_phase", "questionnaire"))
        state.round = data.get("round", 0)
        state.max_rounds = data.get("max_rounds", 3)
        state.collected_info = data.get("collected_info", {})
        dim_cov = data.get("dimension_coverage", {})
        state.dimension_coverage = {
            RequirementDimension.TARGET_USER: dim_cov.get(RequirementDimension.TARGET_USER, False),
            RequirementDimension.CORE_PROBLEM: dim_cov.get(RequirementDimension.CORE_PROBLEM, False),
            RequirementDimension.KEY_FEATURES: dim_cov.get(RequirementDimension.KEY_FEATURES, False),
            RequirementDimension.SUCCESS_CRITERIA: dim_cov.get(RequirementDimension.SUCCESS_CRITERIA, False),
            RequirementDimension.CONSTRAINTS: dim_cov.get(RequirementDimension.CONSTRAINTS, False),
            RequirementDimension.TECH_PREFERENCE: dim_cov.get(RequirementDimension.TECH_PREFERENCE, False),
            RequirementDimension.SCOPE: dim_cov.get(RequirementDimension.SCOPE, False),
            RequirementDimension.PRIORITY: dim_cov.get(RequirementDimension.PRIORITY, False),
        }
        state.original_message = data.get("original_message", "")
        state.completed = data.get("completed", False)
        state.history = data.get("history", [])
        return state


class QuestionnaireService:
    _instances: Dict[str, QuestionnaireState] = {}

    @classmethod
    def _ensure_loaded(cls, project_id: str):
        """确保项目数据已从 StateRepository 加载"""
        if project_id not in cls._instances:
            data = StateRepository.load(STATE_SERVICE_NAME, project_id)
            if data is not None:
                cls._instances[project_id] = QuestionnaireState.from_dict(data)
            else:
                cls._instances[project_id] = QuestionnaireState(project_id)

    @classmethod
    def _save_to_repo(cls, project_id: str):
        """保存到 StateRepository"""
        state = cls._instances.get(project_id)
        if state:
            StateRepository.save(STATE_SERVICE_NAME, project_id, state.to_dict())

    @classmethod
    def get_state(cls, project_id: str) -> QuestionnaireState:
        cls._ensure_loaded(project_id)
        if project_id not in cls._instances:
            cls._instances[project_id] = QuestionnaireState(project_id)
        return cls._instances[project_id]

    @classmethod
    def reset_state(cls, project_id: str):
        if project_id in cls._instances:
            del cls._instances[project_id]
        StateRepository.delete(STATE_SERVICE_NAME, project_id)

    @classmethod
    def should_trigger_questionnaire(cls, project_id: str, message: str) -> Dict[str, Any]:
        state = cls.get_state(project_id)

        if state.completed:
            return {"should_trigger": False, "reason": "already_completed"}

        if state.planning_phase != PlanningPhase.QUESTIONNAIRE:
            return {"should_trigger": False, "reason": "wrong_phase"}

        if state.round >= state.max_rounds:
            return {"should_trigger": False, "reason": "max_rounds_reached"}

        trigger_keywords = [
            "我想做", "我要做", "帮我做", "做一个", "开发一个", "创建一个",
            "帮我设计", "帮我规划", "我想开发", "我要开发", "项目",
        ]
        has_trigger = any(kw in message for kw in trigger_keywords)

        if state.round == 0 and has_trigger:
            state.original_message = message
            return {"should_trigger": True, "reason": "initial_trigger"}

        if state.round > 0:
            return {"should_trigger": True, "reason": "continue_questionnaire"}

        return {"should_trigger": False, "reason": "no_trigger"}

    @classmethod
    def get_questionnaire_prompt(cls, project_id: str, message: str) -> str:
        state = cls.get_state(project_id)

        if not state.original_message:
            state.original_message = message

        stage_prompts = {
            QuestionnaireStage.INITIAL: cls._get_initial_stage_prompt,
            QuestionnaireStage.EXPANSION: cls._get_expansion_stage_prompt,
            QuestionnaireStage.CLARIFICATION: cls._get_clarification_stage_prompt,
        }

        prompt_func = stage_prompts.get(
            state.current_stage, cls._get_initial_stage_prompt
        )
        return prompt_func(message, state)

    @classmethod
    def _get_initial_stage_prompt(cls, message: str, state: QuestionnaireState) -> str:
        return f"""你是一位资深的产品顾问。用户提出了以下项目想法：

"{message}"

请基于这个想法，设计一份启发性问卷来帮助用户深入思考项目的关键维度。

问卷设计原则：
1. 每个问题都应引导用户深入思考，而非简单收集信息
2. 选择题的选项应覆盖常见场景，同时提供"其他"选项
3. 开放式问题应具有启发性，帮助用户发现未考虑的方面
4. 问题顺序应从宏观到微观，从用户价值到技术实现

必须覆盖以下维度（每个维度至少1个问题）：
- 目标用户：谁会使用这个产品？他们的特征是什么？
- 核心问题：这个产品解决什么痛点？为什么现有方案不够好？
- 关键功能：最核心的3-5个功能是什么？
- 成功标准：如何衡量这个项目的成功？

问卷格式（JSON数组）:
[
  {{
    "id": "q1",
    "type": "single",
    "title": "问题标题（具有启发性）",
    "description": "为什么问这个问题（帮助用户理解意图）",
    "options": ["选项1（具体描述）", "选项2（具体描述）", "其他"],
    "required": true,
    "dimension": "target_user"
  }},
  {{
    "id": "q2",
    "type": "text",
    "title": "启发性开放问题",
    "description": "提示用户思考的方向",
    "required": true,
    "dimension": "core_problem"
  }}
]

type可选值：single（单选）、multiple（多选）、text（文本输入）
dimension可选值：target_user, core_problem, key_features, success_criteria, constraints, tech_preference, scope, priority

只输出JSON数组，不要其他内容。"""

    @classmethod
    def _get_expansion_stage_prompt(cls, message: str, state: QuestionnaireState) -> str:
        collected_context = cls._format_collected_info(state)
        uncovered = cls._get_uncovered_dimensions(state)

        return f"""用户的项目想法：{state.original_message}

已收集的信息：
{collected_context}

尚未覆盖的关键维度：{', '.join([DIMENSION_LABELS[d] for d in uncovered])}

请设计第{state.round + 1}轮问卷，重点关注未覆盖的维度，同时深入挖掘已收集信息的细节。

设计原则：
1. 不要重复已问过的问题
2. 针对未覆盖维度设计启发性问题
3. 对已有信息进行深入追问
4. 帮助用户思考他们可能忽略的方面

问卷格式（JSON数组）:
[
  {{
    "id": "q1",
    "type": "single",
    "title": "问题标题",
    "description": "为什么问这个问题",
    "options": ["选项1", "选项2", "其他"],
    "required": true,
    "dimension": "constraints"
  }}
]

只输出JSON数组，不要其他内容。"""

    @classmethod
    def _get_clarification_stage_prompt(cls, message: str, state: QuestionnaireState) -> str:
        collected_context = cls._format_collected_info(state)

        return f"""这是最后一轮问卷（第{state.round + 1}轮）。

用户的项目想法：{state.original_message}

已收集的信息：
{collected_context}

请设计2-3个确认性问题，确保关键信息准确且完整。

设计原则：
1. 确认核心需求是否理解正确
2. 询问是否有遗漏的重要方面
3. 让用户补充任何他们觉得重要的信息

问卷格式（JSON数组）:
[
  {{
    "id": "q1",
    "type": "single",
    "title": "确认问题",
    "description": "说明",
    "options": ["是", "否"],
    "required": true,
    "dimension": "scope"
  }}
]

只输出JSON数组，不要其他内容。"""

    @classmethod
    def _format_collected_info(cls, state: QuestionnaireState) -> str:
        lines = []
        for key, value in state.collected_info.items():
            dim_label = DIMENSION_LABELS.get(key, key)
            lines.append(f"- {dim_label}: {value}")
        return "\n".join(lines) if lines else "暂无"

    @classmethod
    def _get_uncovered_dimensions(cls, state: QuestionnaireState) -> List[str]:
        return [
            dim
            for dim, covered in state.dimension_coverage.items()
            if not covered
        ]

    @classmethod
    def record_answers(cls, project_id: str, answers: Dict[str, Any], dimensions: Dict[str, str] = None):
        state = cls.get_state(project_id)

        for key, value in answers.items():
            if isinstance(value, list):
                state.collected_info[key] = ", ".join(str(v) for v in value)
            else:
                state.collected_info[key] = str(value)

            if dimensions and key in dimensions:
                state.dimension_coverage[dimensions[key]] = True

        state.history.append(
            {
                "round": state.round,
                "stage": state.current_stage.value,
                "answers": answers,
            }
        )

        state.round += 1

        if state.round == 1:
            state.current_stage = QuestionnaireStage.EXPANSION
        elif state.round == 2:
            state.current_stage = QuestionnaireStage.CLARIFICATION
        elif state.round >= state.max_rounds:
            state.current_stage = QuestionnaireStage.COMPLETED

        cls._save_to_repo(project_id)

        logger.info(
            f"问卷回答记录: project={project_id}, round={state.round}, "
            f"stage={state.current_stage.value}, "
            f"completeness={cls.calculate_completeness(project_id)}%"
        )

    @classmethod
    def calculate_completeness(cls, project_id: str) -> int:
        state = cls.get_state(project_id)
        total_weight = sum(DIMENSION_WEIGHTS.values())
        covered_weight = sum(
            DIMENSION_WEIGHTS[dim]
            for dim, covered in state.dimension_coverage.items()
            if covered
        )
        return int((covered_weight / total_weight) * 100)

    @classmethod
    def get_completeness_detail(cls, project_id: str) -> Dict[str, Any]:
        state = cls.get_state(project_id)
        overall = cls.calculate_completeness(project_id)
        dimensions = {}
        for dim, covered in state.dimension_coverage.items():
            dimensions[dim] = {
                "label": DIMENSION_LABELS.get(dim, dim),
                "covered": covered,
                "weight": DIMENSION_WEIGHTS.get(dim, 0),
            }
        return {
            "overall_percentage": overall,
            "is_sufficient": overall >= COMPLETENESS_THRESHOLD,
            "threshold": COMPLETENESS_THRESHOLD,
            "dimensions": dimensions,
        }

    @classmethod
    def should_complete_questionnaire(cls, project_id: str) -> bool:
        state = cls.get_state(project_id)

        if state.round >= state.max_rounds:
            return True

        completeness = cls.calculate_completeness(project_id)
        if completeness >= COMPLETENESS_THRESHOLD and state.round >= 2:
            return True

        return False

    @classmethod
    def complete_questionnaire(cls, project_id: str):
        state = cls.get_state(project_id)
        state.completed = True
        state.current_stage = QuestionnaireStage.COMPLETED
        state.planning_phase = PlanningPhase.ANALYSIS
        cls._save_to_repo(project_id)

        try:
            from services.intent_analyzer import IntentAnalyzer
            IntentAnalyzer.update_state(project_id, {
                "questionnaire_completed": True,
                "analysis_completed": True,
            })
        except Exception as e:
            logger.warning(f"Failed to sync questionnaire state to IntentAnalyzer: {e}")

        logger.info(f"问卷阶段完成: project={project_id}, completeness={cls.calculate_completeness(project_id)}%")

    @classmethod
    def get_context_for_ai(cls, project_id: str) -> str:
        state = cls.get_state(project_id)

        if not state.collected_info:
            return ""

        lines = ["[用户需求信息 - 以下信息来自问卷收集，请在分析时充分参考]"]
        lines.append(f"原始想法: {state.original_message}")
        lines.append("")

        for key, value in state.collected_info.items():
            dim_label = DIMENSION_LABELS.get(key, key)
            lines.append(f"- {dim_label}: {value}")

        completeness = cls.calculate_completeness(project_id)
        lines.append(f"\n需求理解完成度: {completeness}%")

        uncovered = cls._get_uncovered_dimensions(state)
        if uncovered:
            uncovered_labels = [DIMENSION_LABELS[d] for d in uncovered]
            lines.append(f"未覆盖维度: {', '.join(uncovered_labels)}")

        return "\n".join(lines)

    @classmethod
    def get_analysis_prompt(cls, project_id: str) -> str:
        state = cls.get_state(project_id)
        context = cls.get_context_for_ai(project_id)
        completeness = cls.get_completeness_detail(project_id)

        return f"""你是一位资深的AI项目规划专家。请基于以下用户需求信息，进行深入的需求分析和理解。

{context}

需求理解完成度: {completeness['overall_percentage']}%
{'已达到充分理解标准' if completeness['is_sufficient'] else '部分维度信息不足，但基于已有信息进行分析'}

请完成以下分析：

## 1. 需求理解总结
用你自己的话重新描述用户的需求，确保你真正理解了用户想要什么。

## 2. 核心洞察
- 用户真正想要解决的问题是什么？（可能和用户说的不一样）
- 目标用户的核心痛点是什么？
- 什么功能是必须的，什么是锦上添花的？

## 3. 风险与挑战
- 技术风险
- 产品风险
- 资源风险

## 4. 建议方案方向
基于分析，提出2-3个可能的方案方向，并说明各自的优劣。

## 5. 下一步建议
你认为接下来应该做什么？是继续深入某个方面，还是可以开始正式的项目规划？

请确保分析具有深度和洞察力，不要只是重复用户说的话。"""

    @classmethod
    def get_summary(cls, project_id: str) -> str:
        state = cls.get_state(project_id)
        completeness = cls.calculate_completeness(project_id)

        lines = ["## 需求收集摘要\n"]
        lines.append(f"**原始想法**: {state.original_message}\n")
        lines.append(f"**需求理解完成度**: {completeness}%\n")

        if state.collected_info:
            lines.append("### 已收集的信息\n")
            for key, value in state.collected_info.items():
                dim_label = DIMENSION_LABELS.get(key, key)
                lines.append(f"- **{dim_label}**: {value}")

        uncovered = cls._get_uncovered_dimensions(state)
        if uncovered:
            uncovered_labels = [DIMENSION_LABELS[d] for d in uncovered]
            lines.append(f"\n### 未覆盖的维度\n")
            lines.append(f"{', '.join(uncovered_labels)}")

        lines.append(f"\n- 问卷轮次: {state.round}/{state.max_rounds}")

        return "\n".join(lines)

    @classmethod
    def get_phase_transition(cls, project_id: str) -> Dict[str, Any]:
        state = cls.get_state(project_id)
        completeness = cls.get_completeness_detail(project_id)
        summary = cls.get_summary(project_id)

        return {
            "should_transition": True,
            "current_phase": state.planning_phase.value,
            "next_phase": PlanningPhase.ANALYSIS.value,
            "completeness": completeness,
            "summary": summary,
            "message": f"需求信息收集完成！理解完成度: {completeness['overall_percentage']}%\n\n{summary}\n\n正在进入需求分析阶段...",
        }
