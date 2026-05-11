import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from core.quality_gate import QualityGate

logger = logging.getLogger('Ssuma.LearningDB')


class LearningDB:
    """学习数据库 - 存储和管理学习数据

    已合并到 ssuma.db，通过 Database 单例访问。
    表名映射：feedback -> learning_feedback（避免与 user_feedback 冲突）
    """

    def __init__(self, db=None):
        self._db = db
        self.quality_gate = QualityGate()

    def _get_db(self):
        if self._db is None:
            from db.sqlite import Database
            self._db = Database()
        return self._db

    def add_learning_entry(self, prompt: str, response: str,
                           skill_name: str, phase: str = None,
                           satisfaction: float = 0,
                           success: bool = False) -> bool:
        try:
            should_learn, reason = self.quality_gate.should_learn(
                data={"text": response, "prompt": prompt, "skill_name": skill_name, "phase": phase},
                data_type="response"
            )

            if not should_learn:
                logger.info(f"Learning entry rejected by QualityGate: {reason}")
                return False

            quality_score = 0.8 if should_learn else 0.0

            db = self._get_db()
            db.execute("""
                INSERT INTO learning_entries
                (prompt, response, skill_name, phase, satisfaction, success,
                 quality_score, timestamp, validated, meta_info)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prompt,
                response,
                skill_name,
                phase,
                satisfaction,
                int(success),
                quality_score,
                datetime.now().isoformat(),
                int(should_learn),
                json.dumps({"passed": should_learn, "reason": reason}, ensure_ascii=False)
            ))

            logger.info(f"Learning entry added for {skill_name}")
            return True

        except Exception as e:
            logger.error(f"Error adding learning entry: {e}")
            return False

    def get_skill_stats(self, skill_name: str) -> Dict[str, Any]:
        try:
            db = self._get_db()
            row = db.fetchone("""
                SELECT COUNT(*), AVG(satisfaction), AVG(quality_score),
                       SUM(success), AVG(quality_score) * AVG(satisfaction) as weighted_score
                FROM learning_entries
                WHERE skill_name = ? AND validated = 1
            """, (skill_name,))

            if not row or row[0] == 0:
                return {}

            total_calls, avg_satisfaction, avg_quality, success_count, weighted_score = row

            return {
                "total_calls": total_calls,
                "avg_satisfaction": avg_satisfaction or 0,
                "avg_quality_score": avg_quality or 0,
                "success_count": success_count or 0,
                "success_rate": (success_count / total_calls) if total_calls > 0 else 0,
                "weighted_score": weighted_score or 0
            }

        except Exception as e:
            logger.error(f"Error getting skill stats: {e}")
            return {}

    def get_learning_stats(self) -> Dict[str, Any]:
        try:
            db = self._get_db()

            total = db.fetchone("SELECT COUNT(*) FROM learning_entries")[0]
            high_quality = db.fetchone("SELECT COUNT(*) FROM learning_entries WHERE validated = 1")[0]

            rows = db.fetchall("""
                SELECT skill_name, COUNT(*), AVG(satisfaction), AVG(quality_score)
                FROM learning_entries
                WHERE validated = 1
                GROUP BY skill_name
            """)

            by_skill = []
            for row in rows:
                skill_name, count, avg_sat, avg_qual = row
                by_skill.append({
                    "skill_name": skill_name,
                    "count": count,
                    "avg_satisfaction": avg_sat or 0,
                    "avg_quality": avg_qual or 0
                })

            return {
                "total_entries": total,
                "high_quality_entries": high_quality,
                "quality_ratio": high_quality / total if total > 0 else 0,
                "by_skill": by_skill
            }

        except Exception as e:
            logger.error(f"Error getting learning stats: {e}")
            return {}

    def get_recent_feedbacks(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            db = self._get_db()
            rows = db.fetchall("""
                SELECT skill_name, satisfaction, timestamp, user_comment
                FROM learning_feedback
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            feedbacks = []
            for row in rows:
                skill_name, satisfaction, timestamp, user_comment = row
                feedbacks.append({
                    "skill_name": skill_name,
                    "satisfaction": satisfaction,
                    "timestamp": timestamp,
                    "user_comment": user_comment
                })

            return feedbacks

        except Exception as e:
            logger.error(f"Error getting recent feedbacks: {e}")
            return []

    def add_feedback(self, skill_name: str, satisfaction: float,
                     user_comment: str = None):
        try:
            db = self._get_db()
            db.execute("""
                INSERT INTO learning_feedback (skill_name, satisfaction, timestamp, user_comment)
                VALUES (?, ?, ?, ?)
            """, (skill_name, satisfaction, datetime.now().isoformat(), user_comment))

            logger.info(f"Feedback added for {skill_name}")

        except Exception as e:
            logger.error(f"Error adding feedback: {e}")

    def save_metacognition_analysis(self, analysis: Dict[str, Any]):
        try:
            db = self._get_db()
            db.execute("""
                INSERT INTO metacognition_analysis (timestamp, analysis_data, evolution_triggered)
                VALUES (?, ?, ?)
            """, (
                analysis.get("timestamp"),
                json.dumps(analysis, ensure_ascii=False),
                int(analysis.get("evolution_needed", False))
            ))

            logger.info("Metacognition analysis saved")

        except Exception as e:
            logger.error(f"Error saving metacognition analysis: {e}")

    def get_learning_entries(self, skill_name: str = None,
                            min_quality: float = 0.7,
                            limit: int = 100) -> List[Dict[str, Any]]:
        try:
            db = self._get_db()

            if skill_name:
                rows = db.fetchall("""
                    SELECT id, prompt, response, skill_name, phase, satisfaction,
                           quality_score, timestamp
                    FROM learning_entries
                    WHERE skill_name = ? AND validated = 1 AND quality_score >= ?
                    ORDER BY quality_score DESC
                    LIMIT ?
                """, (skill_name, min_quality, limit))
            else:
                rows = db.fetchall("""
                    SELECT id, prompt, response, skill_name, phase, satisfaction,
                           quality_score, timestamp
                    FROM learning_entries
                    WHERE validated = 1 AND quality_score >= ?
                    ORDER BY quality_score DESC
                    LIMIT ?
                """, (min_quality, limit))

            entries = []
            for row in rows:
                id_, prompt, response, skill, phase, satisfaction, quality, timestamp = row
                entries.append({
                    "id": id_,
                    "prompt": prompt,
                    "response": response,
                    "skill_name": skill,
                    "phase": phase,
                    "satisfaction": satisfaction,
                    "quality_score": quality,
                    "timestamp": timestamp
                })

            return entries

        except Exception as e:
            logger.error(f"Error getting learning entries: {e}")
            return []

    def cleanup_low_quality(self, threshold: float = 0.5) -> int:
        try:
            db = self._get_db()
            cursor = db.execute("""
                DELETE FROM learning_entries
                WHERE quality_score < ? AND validated = 0
            """, (threshold,))

            deleted = cursor.rowcount
            logger.info(f"Cleaned up {deleted} low-quality entries")
            return deleted

        except Exception as e:
            logger.error(f"Error cleaning up: {e}")
            return 0
