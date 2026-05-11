import json
import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from core.state_repository import StateRepository

logger = logging.getLogger('Ssuma.FactChecker')

STATE_SERVICE_COMMITMENTS = "fact_checker_commitments"
STATE_SERVICE_STATEMENTS = "fact_checker_statements"

@dataclass
class Commitment:
    category: str  # tech_stack, feature, constraint, decision, user_info
    content: str
    evidence: str  # source message
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "content": self.content,
            "evidence": self.evidence,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Commitment":
        return cls(
            category=data.get("category", "decision"),
            content=data.get("content", ""),
            evidence=data.get("evidence", ""),
            confidence=data.get("confidence", 1.0),
        )

@dataclass
class FactCheckResult:
    is_consistent: bool
    issues: List[str]
    warnings: List[str]
    missed_commitments: List[str]
    confidence_score: float

class FactChecker:
    """Verify AI responses against earlier commitments/facts."""
    
    _commitments: Dict[str, List[Commitment]] = {}
    _last_ai_statements: Dict[str, str] = {}

    @classmethod
    def _ensure_commitments_loaded(cls, project_id: str):
        """确保项目承诺数据已从 StateRepository 加载"""
        if project_id not in cls._commitments:
            data = StateRepository.load(STATE_SERVICE_COMMITMENTS, project_id)
            if data is not None:
                cls._commitments[project_id] = [Commitment.from_dict(c) for c in data]
            else:
                cls._commitments[project_id] = []

    @classmethod
    def _ensure_statements_loaded(cls, project_id: str):
        """确保项目AI声明数据已从 StateRepository 加载"""
        if project_id not in cls._last_ai_statements:
            data = StateRepository.load(STATE_SERVICE_STATEMENTS, project_id)
            if data is not None:
                cls._last_ai_statements[project_id] = data
            else:
                cls._last_ai_statements[project_id] = ""

    @classmethod
    def _save_commitments(cls, project_id: str):
        """保存承诺数据到 StateRepository"""
        commitments = cls._commitments.get(project_id, [])
        StateRepository.save(
            STATE_SERVICE_COMMITMENTS,
            project_id,
            [c.to_dict() for c in commitments]
        )

    @classmethod
    def _save_statements(cls, project_id: str):
        """保存AI声明数据到 StateRepository"""
        statement = cls._last_ai_statements.get(project_id, "")
        StateRepository.save(STATE_SERVICE_STATEMENTS, project_id, statement)
    
    @classmethod
    async def extract_commitments(cls, project_id: str, conversation: str) -> List[Commitment]:
        """Extract key commitments/facts from conversation using LLM."""
        cls._ensure_commitments_loaded(project_id)
        from core.llm_factory import LLMFactory
        
        prompt = f"""从以下对话中提取关键承诺、决策、事实和需求。
每个承诺必须属于以下类别之一：tech_stack, feature, constraint, decision, user_info

对话：
{conversation}

请以JSON格式输出：
{{
    "commitments": [
        {{"category": "tech_stack", "content": "使用PostgreSQL", "evidence": "用户说要用PostgreSQL"}},
        {{"category": "feature", "content": "用户认证功能", "evidence": "需要登录功能"}}
    ]
}}

只输出JSON。"""

        try:
            provider = LLMFactory.get_provider()
            response = await provider.chat(
                [{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.3
            )
            data = json.loads(response.strip().strip("```json").strip("```").strip())
            
            commitments = []
            for c in data.get("commitments", []):
                commitments.append(Commitment(
                    category=c.get("category", "decision"),
                    content=c.get("content", ""),
                    evidence=c.get("evidence", ""),
                    confidence=c.get("confidence", 0.8)
                ))
            
            cls._commitments[project_id] = commitments
            cls._save_commitments(project_id)
            logger.info(f"Extracted {len(commitments)} commitments for {project_id}")
            return commitments
        except Exception as e:
            logger.error(f"Failed to extract commitments: {e}")
            return cls._commitments.get(project_id, [])

    @classmethod
    async def verify_response(
        cls, 
        project_id: str, 
        response: str,
        conversation: str = ""
    ) -> FactCheckResult:
        """Verify AI response against known commitments."""
        cls._ensure_commitments_loaded(project_id)
        issues = []
        warnings = []
        missed = []
        
        commitments = cls._commitments.get(project_id, [])
        
        if not commitments and conversation:
            commitments = await cls.extract_commitments(project_id, conversation)
        
        if not commitments:
            return FactCheckResult(
                is_consistent=True,
                issues=[],
                warnings=["No commitments to verify against"],
                missed_commitments=[],
                confidence_score=1.0
            )
        
        response_lower = response.lower()
        
        for commitment in commitments:
            content_lower = commitment.content.lower()
            
            # Check for contradictions
            if commitment.category == "tech_stack":
                # Check if tech mentioned matches
                if any(tech in response_lower for tech in ["postgres", "postgresql", "mysql", "mongodb", "supabase"]):
                    if commitment.content.lower() not in response_lower:
                        # Tech was mentioned but different from commitment
                        warnings.append(f"可能使用了不同的技术栈: {commitment.content}")
            
            # Check for feature promises
            if commitment.category == "feature":
                if "功能" in content_lower or "feature" in content_lower:
                    if content_lower not in response_lower:
                        missed.append(f"承诺的功能未实现: {commitment.content}")
            
            # Check for constraints
            if commitment.category == "constraint":
                negations = ["不需要", "不用", "没有", "not need", "don't need", "without"]
                if any(neg in response_lower for neg in negations):
                    if commitment.content.lower() in response_lower:
                        issues.append(f"违反约束: {commitment.content}")
        
        is_consistent = len(issues) == 0
        confidence = max(0.5, 1.0 - (len(issues) * 0.2) - (len(warnings) * 0.1))
        
        return FactCheckResult(
            is_consistent=is_consistent,
            issues=issues,
            warnings=warnings,
            missed_commitments=missed,
            confidence_score=confidence
        )

    @classmethod
    def add_commitment(cls, project_id: str, commitment: Commitment):
        """Manually add a commitment."""
        cls._ensure_commitments_loaded(project_id)
        if project_id not in cls._commitments:
            cls._commitments[project_id] = []
        
        # Avoid duplicates
        existing = [c.content for c in cls._commitments[project_id]]
        if commitment.content not in existing:
            cls._commitments[project_id].append(commitment)
            cls._save_commitments(project_id)
            logger.info(f"Added commitment for {project_id}: {commitment.content}")

    @classmethod
    def get_commitments(cls, project_id: str) -> List[Dict]:
        """Get all commitments for a project."""
        cls._ensure_commitments_loaded(project_id)
        commitments = cls._commitments.get(project_id, [])
        return [
            {"category": c.category, "content": c.content, "evidence": c.evidence}
            for c in commitments
        ]

    @classmethod
    def clear_commitments(cls, project_id: str):
        """Clear commitments for a project."""
        if project_id in cls._commitments:
            del cls._commitments[project_id]
        StateRepository.delete(STATE_SERVICE_COMMITMENTS, project_id)

    @classmethod
    def generate_consistency_reminder(cls, project_id: str) -> str:
        """Generate a reminder to be consistent with past commitments."""
        commitments = cls.get_commitments(project_id)
        if not commitments:
            return ""
        
        lines = ["## 请确保遵循以下承诺:"]
        for c in commitments[:5]:  # Limit to 5
            lines.append(f"- [{c['category']}] {c['content']}")
        
        return "\n".join(lines)