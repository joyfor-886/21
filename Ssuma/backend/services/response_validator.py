import re
import logging
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from core.garbage_detector import GarbageDetector

logger = logging.getLogger('Ssuma.ResponseValidator')

REMIND_ROUNDS = {
    "qishu": [3, 5, 7],
    "tanyin": [2, 4, 6],
    "caiheng": [2, 4],
    "zhenwei": [2, 4],
    "ceshu": [2, 3],
    "ningmo": [1],
}


@dataclass
class ValidationResult:
    is_valid: bool
    issues: List[str]
    score: float
    suggestion: str


class ResponseValidator:
    """Validate AI responses against phase constraints."""

    @classmethod
    def validate(cls, response: str, phase) -> ValidationResult:
        issues = []
        score = 1.0
        phase_value = getattr(phase, 'value', str(phase))

        if phase_value == "qishu":
            issues, score = cls._validate_qishu(response)
        elif phase_value == "caiheng":
            issues, score = cls._validate_caiheng(response)
        elif phase_value == "zhenwei":
            issues, score = cls._validate_zhenwei(response)
        elif phase_value == "ceshu":
            issues, score = cls._validate_ceshu(response)
        elif phase_value == "ningmo":
            issues, score = cls._validate_ningmo(response)

        # Add garbage detection
        is_garbage, details = GarbageDetector.detect(response)
        if is_garbage:
            issues.append(f"Detected low-quality output (score: {details.get('final_score', 'N/A')})")
            score -= 0.3
            suggestions = GarbageDetector.get_improvement_suggestions(details)
            issues.extend(suggestions)

        is_valid = score >= 0.6 and len(issues) <= 2
        suggestion = cls._get_suggestion(issues, phase_value)

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            score=max(0.0, score),
            suggestion=suggestion
        )

    @classmethod
    def _count_questions(cls, response: str) -> int:
        question_marks = response.count("?") + response.count("？")
        question_patterns = len(re.findall(r'(?:what|how|why|which|where|when|是否|什么|如何|为什么|哪个|哪里|何时)', response, re.IGNORECASE))
        return max(question_marks, question_patterns)

    @classmethod
    def _validate_qishu(cls, response: str) -> tuple:
        issues = []
        score = 1.0

        question_count = cls._count_questions(response)
        if question_count > 3:
            issues.append(f"AI asked {question_count} questions at once (max 3)")
            score -= 0.3

        if len(response) > 500:
            issues.append("Response too long for qishu (max 500 chars)")
            score -= 0.1

        return issues, max(score, 0.0)

    @classmethod
    def _validate_caiheng(cls, response: str) -> tuple:
        issues = []
        score = 1.0

        has_challenge = any(kw in response.lower() for kw in ["挑战", "假设", "question", "challenge", "是否考虑"])
        if not has_challenge:
            issues.append("No core assumption challenged")
            score -= 0.2

        has_value = any(kw in response.lower() for kw in ["价值", "value", "核心", "core"])
        if not has_value:
            issues.append("No value proposition mentioned")
            score -= 0.2

        return issues, max(score, 0.0)

    @classmethod
    def _validate_zhenwei(cls, response: str) -> tuple:
        issues = []
        score = 1.0

        has_architecture = any(kw in response.lower() for kw in ["架构", "architecture", "系统", "system", "技术选型"])
        if not has_architecture:
            issues.append("No architecture discussion")
            score -= 0.2

        has_data = any(kw in response.lower() for kw in ["数据", "data", "数据库", "database", "存储"])
        if not has_data:
            issues.append("No data model mentioned")
            score -= 0.2

        return issues, max(score, 0.0)

    @classmethod
    def _validate_ceshu(cls, response: str) -> tuple:
        issues = []
        score = 1.0

        has_files = bool(re.search(r'(?:create|modify|create:|modify:|文件|`.*\.\w+`)', response, re.IGNORECASE))
        if not has_files:
            issues.append("No file paths specified")
            score -= 0.3

        has_tdd = bool(re.search(r'(?:test|测试|assert)', response, re.IGNORECASE))
        if not has_tdd:
            issues.append("No test coverage mentioned (TDD required)")
            score -= 0.2

        return issues, max(score, 0.0)

    @classmethod
    def _validate_ningmo(cls, response: str) -> tuple:
        issues = []
        score = 1.0

        required_sections = ["产品概述", "产品愿景", "技术方案", "实施计划"]
        found_sections = [s for s in required_sections if s in response]
        missing = len(required_sections) - len(found_sections)

        if missing > 0:
            issues.append(f"Missing {missing} required sections")
            score -= 0.15 * missing

        return issues, max(score, 0.0)

    @classmethod
    def _get_suggestion(cls, issues: list, phase_value: str) -> str:
        if not issues:
            return ""

        suggestions = {
            "qishu": "请一次只问一个问题，保持回答简洁",
            "caiheng": "请挑战核心假设并明确产品价值",
            "zhenwei": "请包含架构设计和数据模型讨论",
            "ceshu": "请指定文件路径并遵循TDD原则",
            "ningmo": "请确保包含所有必需的章节",
        }
        return suggestions.get(phase_value, "")

    @classmethod
    def should_remind_next_phase(cls, phase, current_turns: int) -> bool:
        phase_value = getattr(phase, 'value', str(phase))
        return current_turns in REMIND_ROUNDS.get(phase_value, [])

    @classmethod
    def generate_reminder(cls, phase) -> str:
        phase_value = getattr(phase, 'value', str(phase))
        reminders = {
            "qishu": "我们已经讨论了几轮，需求逐渐清晰。您觉得是否需要进入下一个阶段？可以从 CEO 视角审视产品价值，或者直接生成项目方案。",
            "tanyin": "我们已经收集了不少信息。您觉得是否需要进入下一个阶段？",
            "caiheng": "产品视角的讨论已经比较充分。是否要进入技术评审阶段，讨论具体的实现方案？",
            "zhenwei": "技术讨论已经比较深入。是否要生成完整的实施计划，或者直接生成项目方案？",
            "ceshu": "任务分解已经完成。是否要生成最终的项目方案？",
            "ningmo": "方案已生成。是否要下载上下文文件和项目脚手架？",
        }
        return reminders.get(phase_value, "")
