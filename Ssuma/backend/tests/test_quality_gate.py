import pytest
from core.quality_gate import QualityGate, DataQuality


class TestQualityGate:

    def test_evaluate_feedback_approved(self):
        feedback = {"score": 0.9, "comments": "非常满意，回答准确专业"}
        result = QualityGate.evaluate_feedback(feedback)
        assert result == DataQuality.APPROVED

    def test_evaluate_feedback_rejected_low_score(self):
        feedback = {"score": 0.3, "comments": "不满意"}
        result = QualityGate.evaluate_feedback(feedback)
        assert result == DataQuality.REJECTED

    def test_evaluate_feedback_pending_no_comments(self):
        feedback = {"score": 0.85, "comments": "好"}
        result = QualityGate.evaluate_feedback(feedback)
        assert result == DataQuality.PENDING

    def test_evaluate_response_too_short(self):
        result = QualityGate.evaluate_response("好的", {})
        assert result == DataQuality.REJECTED

    def test_evaluate_response_too_long(self):
        result = QualityGate.evaluate_response("x" * 20000, {})
        assert result == DataQuality.REJECTED

    def test_evaluate_response_garbage_keyword(self):
        text = "好的，我来帮你分析一下。" + "a" * 200
        result = QualityGate.evaluate_response(text, {})
        assert result == DataQuality.REJECTED

    def test_evaluate_response_code_block(self):
        text = (
            "分析当前需求后，以下是一段参考代码实现：\n\n"
            "```python\ndef hello():\n    print('hello world')\n\n"
            "def process_data(items):\n    return [x * 2 for x in items]\n```\n\n"
            "以上代码实现了核心数据处理功能，满足业务需求。"
            "如果需要进一步优化，可以添加异步处理和缓存机制。"
        )
        result = QualityGate.evaluate_response(text, {})
        assert result == DataQuality.APPROVED, f"Expected approved, got {result}"

    def test_evaluate_response_analysis_text(self):
        text = (
            "分析用户需求后发现，核心痛点在于数据同步效率低。"
            "建议在 src/services/sync.py 中实现增量同步方案，"
            "同时在服务端支持冲突解决算法，确保数据一致性。"
            "测试结果显示该方案可将同步延迟从 30 秒降低到 2 秒以内。"
        )
        result = QualityGate.evaluate_response(text, {})
        assert result == DataQuality.APPROVED

    def test_evaluate_pattern_low_success(self):
        result = QualityGate.evaluate_pattern({"success_rate": 0.5, "usage_count": 10, "avg_satisfaction": 0.9})
        assert result == DataQuality.REJECTED

    def test_evaluate_pattern_pending_low_usage(self):
        result = QualityGate.evaluate_pattern({"success_rate": 0.95, "usage_count": 2, "avg_satisfaction": 0.9})
        assert result == DataQuality.PENDING

    def test_evaluate_pattern_approved(self):
        result = QualityGate.evaluate_pattern({"success_rate": 0.95, "usage_count": 10, "avg_satisfaction": 0.9})
        assert result == DataQuality.APPROVED

    def test_should_learn_approved_feedback(self):
        should, reason = QualityGate.should_learn(
            {"score": 0.85, "comments": "非常专业的分析报告，给出了详细的技术方案和实施步骤"},
            data_type="feedback"
        )
        assert should == True, f"Expected True, got False: {reason}"

    def test_should_learn_rejected_feedback(self):
        should, reason = QualityGate.should_learn(
            {"score": 0.5, "comments": "不满意"},
            data_type="feedback"
        )
        assert should == False

    def test_should_learn_unknown_type(self):
        should, reason = QualityGate.should_learn({}, data_type="unknown")
        assert should == False

    def test_should_learn_response_with_code(self):
        text = (
            "分析需求后给出以下代码实现：\n\n"
            "```\nconst greeting = (name) => {\n"
            "  return `Hello, ${name}!`;\n"
            "};\n```\n\n"
            "以上代码实现了用户认证功能，满足安全性和性能要求。"
            "需要部署到生产环境前还需要添加单元测试和集成测试。"
        )
        should, reason = QualityGate.should_learn({"text": text}, data_type="response")
        assert should == True

    def test_should_learn_garbage_response(self):
        should, reason = QualityGate.should_learn({"text": "好的"}, data_type="response")
        assert should == False
