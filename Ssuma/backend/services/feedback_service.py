import logging
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from core.quality_gate import QualityGate, DataQuality
from core.garbage_detector import GarbageDetector
from core.state_repository import StateRepository

logger = logging.getLogger('Ssuma.FeedbackService')

STATE_SERVICE_NAME = "feedback"

@dataclass
class UserFeedback:
    project_id: str
    turn: int
    rating: int
    feedback_text: str
    ai_response: str
    phase: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "turn": self.turn,
            "rating": self.rating,
            "feedback_text": self.feedback_text,
            "ai_response": self.ai_response,
            "phase": self.phase,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserFeedback":
        return cls(
            project_id=data.get("project_id", ""),
            turn=data.get("turn", 0),
            rating=data.get("rating", 0),
            feedback_text=data.get("feedback_text", ""),
            ai_response=data.get("ai_response", ""),
            phase=data.get("phase", ""),
            created_at=data.get("created_at", ""),
        )

class FeedbackService:
    """Track user satisfaction and AI response quality."""
    
    _feedback_store: Dict[str, List[UserFeedback]] = {}

    @classmethod
    def _load_from_repo(cls, project_id: str) -> List[UserFeedback]:
        """从 StateRepository 加载反馈数据"""
        data = StateRepository.load(STATE_SERVICE_NAME, project_id)
        if data is not None:
            return [UserFeedback.from_dict(f) for f in data]
        return []

    @classmethod
    def _save_to_repo(cls, project_id: str):
        """将反馈数据保存到 StateRepository"""
        feedbacks = cls._feedback_store.get(project_id, [])
        StateRepository.save(
            STATE_SERVICE_NAME,
            project_id,
            [f.to_dict() for f in feedbacks]
        )

    @classmethod
    def _ensure_loaded(cls, project_id: str):
        """确保项目数据已从 StateRepository 加载"""
        if project_id not in cls._feedback_store:
            cls._feedback_store[project_id] = cls._load_from_repo(project_id)

    @classmethod
    def add_feedback(
        cls,
        project_id: str,
        turn: int,
        rating: int,
        feedback_text: str,
        ai_response: str,
        phase: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """添加反馈，并检测质量"""
        cls._ensure_loaded(project_id)
        
        # 1. 用 QualityGate 评估反馈质量
        feedback_data = {
            "score": rating / 5.0,  # 转换为 0-1
            "comments": feedback_text
        }
        should_learn, reason = QualityGate.should_learn(
            feedback_data, data_type="feedback"
        )
        
        # 2. 用 GarbageDetector 检测 AI 回复
        is_garbage, details = GarbageDetector.detect(ai_response)
        suggestions = GarbageDetector.get_improvement_suggestions(details) if is_garbage else []
        
        feedback = UserFeedback(
            project_id=project_id,
            turn=turn,
            rating=rating,
            feedback_text=feedback_text,
            ai_response=ai_response,
            phase=phase,
            created_at=datetime.now().isoformat()
        )
        cls._feedback_store[project_id].append(feedback)
        
        cls._persist_to_db(project_id, feedback)
        cls._save_to_repo(project_id)
        
        return True, {
            "should_learn": should_learn,
            "quality_reason": reason,
            "is_garbage": is_garbage,
            "garbage_details": details,
            "improvement_suggestions": suggestions
        }

    @classmethod
    def _persist_to_db(cls, project_id: str, feedback: UserFeedback):
        try:
            from db.sqlite import Database
            db = Database()
            db.execute(
                """INSERT INTO user_feedback 
                   (project_id, turn, rating, feedback_text, ai_response, phase, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (project_id, feedback.turn, feedback.rating, feedback.feedback_text,
                 feedback.ai_response, feedback.phase, feedback.created_at)
            )
        except Exception as e:
            logger.error(f"Failed to persist feedback: {e}")

    @classmethod
    def get_recent_rating(cls, project_id: str) -> Optional[int]:
        cls._ensure_loaded(project_id)
        feedbacks = cls._feedback_store.get(project_id, [])
        if feedbacks:
            return feedbacks[-1].rating
        return None

    @classmethod
    def get_satisfaction_trend(cls, project_id: str) -> Dict:
        cls._ensure_loaded(project_id)
        feedbacks = cls._feedback_store.get(project_id, [])
        if not feedbacks:
            return {"average": 0, "trend": "neutral", "count": 0}
        
        ratings = [f.rating for f in feedbacks]
        avg = sum(ratings) / len(ratings)
        
        if len(ratings) >= 2:
            trend = "improving" if ratings[-1] > ratings[0] else "declining" if ratings[-1] < ratings[0] else "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "average": round(avg, 2),
            "trend": trend,
            "count": len(ratings),
            "latest": ratings[-1]
        }

    @classmethod
    def get_low_rated_turns(cls, project_id: str) -> List[int]:
        cls._ensure_loaded(project_id)
        feedbacks = cls._feedback_store.get(project_id, [])
        return [f.turn for f in feedbacks if f.rating <= 2]

    @classmethod
    def reset(cls, project_id: str):
        if project_id in cls._feedback_store:
            del cls._feedback_store[project_id]
        StateRepository.delete(STATE_SERVICE_NAME, project_id)

    @classmethod
    def restore_from_repo(cls):
        """启动时从 StateRepository 恢复所有反馈数据"""
        all_states = StateRepository.load_all(STATE_SERVICE_NAME)
        for project_id, data_list in all_states.items():
            cls._feedback_store[project_id] = [UserFeedback.from_dict(f) for f in data_list]
        logger.info(f"FeedbackService restored {len(all_states)} projects from StateRepository")