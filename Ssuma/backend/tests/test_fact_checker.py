import pytest
from services.fact_checker import FactChecker, Commitment, FactCheckResult


class TestFactChecker:

    def test_add_commitment(self):
        FactChecker.add_commitment(
            "test-proj",
            Commitment(
                category="tech_stack",
                content="使用PostgreSQL",
                evidence="用户说要用PostgreSQL"
            )
        )
        
        commitments = FactChecker.get_commitments("test-proj")
        
        assert len(commitments) == 1
        assert commitments[0]["content"] == "使用PostgreSQL"
        assert commitments[0]["category"] == "tech_stack"

    def test_get_commitments_empty(self):
        commitments = FactChecker.get_commitments("non-existent-proj")
        
        assert commitments == []

    def test_clear_commitments(self):
        FactChecker.add_commitment(
            "test-proj-2",
            Commitment(category="feature", content="用户登录", evidence="需要登录")
        )
        
        FactChecker.clear_commitments("test-proj-2")
        commitments = FactChecker.get_commitments("test-proj-2")
        
        assert commitments == []

    def test_no_duplicates(self):
        FactChecker.add_commitment(
            "test-proj-3",
            Commitment(category="tech_stack", content="使用React", evidence="用React")
        )
        FactChecker.add_commitment(
            "test-proj-3",
            Commitment(category="tech_stack", content="使用React", evidence="用React")
        )
        
        commitments = FactChecker.get_commitments("test-proj-3")
        
        assert len(commitments) == 1

    def test_generate_consistency_reminder_empty(self):
        reminder = FactChecker.generate_consistency_reminder("non-existent")
        
        assert reminder == ""

    def test_generate_consistency_reminder(self):
        FactChecker.add_commitment(
            "test-proj-4",
            Commitment(category="tech_stack", content="PostgreSQL", evidence="pg")
        )
        FactChecker.add_commitment(
            "test-proj-4",
            Commitment(category="feature", content="用户认证", evidence="auth")
        )
        
        reminder = FactChecker.generate_consistency_reminder("test-proj-4")
        
        assert "PostgreSQL" in reminder
        assert "用户认证" in reminder
        assert "[tech_stack]" in reminder