import pytest
from services.questionnaire_service import (
    QuestionnaireState,
    QuestionnaireService,
    QuestionnaireStage,
    PlanningPhase,
    RequirementDimension,
    DIMENSION_LABELS,
    DIMENSION_WEIGHTS,
    COMPLETENESS_THRESHOLD,
)


@pytest.fixture(autouse=True)
def reset_questionnaire_state():
    yield
    for key in list(QuestionnaireService._instances.keys()):
        QuestionnaireService._instances.pop(key, None)


class TestQuestionnaireService:

    def test_questionnaire_state_init(self):
        state = QuestionnaireState("test-proj")
        
        assert state.project_id == "test-proj"
        assert state.current_stage == QuestionnaireStage.INITIAL
        assert state.planning_phase == PlanningPhase.QUESTIONNAIRE
        assert state.round == 0
        assert state.completed is False

    def test_dimension_labels(self):
        assert DIMENSION_LABELS[RequirementDimension.TARGET_USER] == "目标用户"
        assert DIMENSION_LABELS[RequirementDimension.CORE_PROBLEM] == "核心问题"
        assert DIMENSION_LABELS[RequirementDimension.KEY_FEATURES] == "关键功能"

    def test_dimension_weights(self):
        assert DIMENSION_WEIGHTS[RequirementDimension.CORE_PROBLEM] == 25
        assert DIMENSION_WEIGHTS[RequirementDimension.TARGET_USER] == 20

    def test_completeness_threshold(self):
        assert COMPLETENESS_THRESHOLD == 60

    def test_collect_info(self):
        state = QuestionnaireService.get_state("test-proj-2")
        state.collected_info["target_user"] = "开发者"
        state.collected_info["core_problem"] = "需要快速构建Web应用"
        
        assert state.collected_info["target_user"] == "开发者"
        assert state.collected_info["core_problem"] == "需要快速构建Web应用"

    def test_dimension_coverage_init(self):
        state = QuestionnaireService.get_state("test-proj-3")
        
        expected_dims = [
            "target_user", "core_problem", "key_features", 
            "success_criteria", "constraints", "tech_preference", "scope", "priority"
        ]
        for dim_key in expected_dims:
            assert state.dimension_coverage.get(dim_key) is False

    def test_stage_transitions(self):
        state = QuestionnaireService.get_state("test-proj-4")
        
        state.current_stage = QuestionnaireStage.EXPANSION
        assert state.current_stage == QuestionnaireStage.EXPANSION
        
        state.current_stage = QuestionnaireStage.CLARIFICATION
        assert state.current_stage == QuestionnaireStage.CLARIFICATION
        
        state.current_stage = QuestionnaireStage.COMPLETED
        assert state.current_stage == QuestionnaireStage.COMPLETED