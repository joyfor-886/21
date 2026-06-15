import pytest
from services.response_validator import ResponseValidator
from domain.enums import FlowPhase

def test_validate_qishu_too_many_questions():
    response = "What do you think? How should we do this? Which approach is best? When can we start?"
    result = ResponseValidator.validate(response, "qishu")
    # Issues should be detected
    assert len(result.issues) > 0
    assert "question" in str(result.issues).lower() or "question" in result.suggestion.lower()

def test_should_remind_next_phase():
    reminder = ResponseValidator.generate_reminder("qishu")
    assert "阶段" in reminder
    assert len(reminder) > 0