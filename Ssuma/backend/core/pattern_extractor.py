import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import Counter

logger = logging.getLogger('Ssuma.PatternExtractor')


class ProjectPattern:
    """项目模式"""
    def __init__(self, pattern_type: str, content: Dict[str, Any],
                 success_count: int = 1, quality_score: float = 1.0):
        self.pattern_type = pattern_type
        self.content = content
        self.success_count = success_count
        self.quality_score = quality_score
        self.last_used = datetime.now().isoformat()
        self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_type": self.pattern_type,
            "content": self.content,
            "success_count": self.success_count,
            "quality_score": self.quality_score,
            "last_used": self.last_used,
            "created_at": self.created_at
        }


class PatternExtractor:
    """项目基因库 - 提取和管理成功项目模式

    已合并到 ssuma.db，通过 Database 单例访问。
    """

    def __init__(self, db=None):
        self._db = db
        self.patterns: Dict[str, List[ProjectPattern]] = {}
        self._load_patterns()

    def _get_db(self):
        if self._db is None:
            from db.sqlite import Database
            self._db = Database()
        return self._db

    def _load_patterns(self):
        try:
            db = self._get_db()
            rows = db.fetchall("""
                SELECT pattern_type, content, success_count, quality_score, last_used, created_at
                FROM project_patterns
                WHERE quality_score >= 0.7
                ORDER BY success_count DESC, quality_score DESC
            """)

            for row in rows:
                pattern_type, content_str, success_count, quality_score, last_used, created_at = row
                try:
                    content = json.loads(content_str)
                    pattern = ProjectPattern(
                        pattern_type, content, success_count, quality_score
                    )
                    pattern.last_used = last_used or pattern.last_used
                    pattern.created_at = created_at or pattern.created_at

                    if pattern_type not in self.patterns:
                        self.patterns[pattern_type] = []
                    self.patterns[pattern_type].append(pattern)
                except json.JSONDecodeError:
                    continue

            logger.info(f"Loaded {sum(len(v) for v in self.patterns.values())} patterns")

        except Exception as e:
            logger.error(f"Error loading patterns: {e}")

    def extract_from_project(self, project_data: Dict[str, Any]) -> List[ProjectPattern]:
        extracted = []

        tech_stack = self._extract_tech_stack(project_data)
        if tech_stack:
            pattern = ProjectPattern(
                pattern_type="tech_stack",
                content=tech_stack,
                success_count=1,
                quality_score=self._assess_pattern_quality("tech_stack", tech_stack)
            )
            extracted.append(pattern)

        architecture = self._extract_architecture(project_data)
        if architecture:
            pattern = ProjectPattern(
                pattern_type="architecture",
                content=architecture,
                success_count=1,
                quality_score=self._assess_pattern_quality("architecture", architecture)
            )
            extracted.append(pattern)

        requirements = self._extract_requirements(project_data)
        if requirements:
            pattern = ProjectPattern(
                pattern_type="requirements",
                content=requirements,
                success_count=1,
                quality_score=self._assess_pattern_quality("requirements", requirements)
            )
            extracted.append(pattern)

        return extracted

    def _extract_tech_stack(self, project_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        tech_info = project_data.get("tech_stack", {})
        if not tech_info:
            return None

        return {
            "frontend": tech_info.get("frontend"),
            "backend": tech_info.get("backend"),
            "database": tech_info.get("database"),
            "deployment": tech_info.get("deployment"),
            "key_libraries": tech_info.get("key_libraries", [])
        }

    def _extract_architecture(self, project_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        arch_info = project_data.get("architecture", {})
        if not arch_info:
            return None

        return {
            "pattern": arch_info.get("pattern"),
            "layers": arch_info.get("layers", []),
            "key_components": arch_info.get("key_components", []),
            "data_flow": arch_info.get("data_flow")
        }

    def _extract_requirements(self, project_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        req_info = project_data.get("requirements", {})
        if not req_info:
            return None

        return {
            "domain": req_info.get("domain"),
            "core_features": req_info.get("core_features", []),
            "user_roles": req_info.get("user_roles", []),
            "complexity": req_info.get("complexity", "medium")
        }

    def _assess_pattern_quality(self, pattern_type: str, content: Dict[str, Any]) -> float:
        score = 1.0

        if pattern_type == "tech_stack":
            if not content.get("frontend") or not content.get("backend"):
                score -= 0.3
            if not content.get("database"):
                score -= 0.2

        elif pattern_type == "architecture":
            if not content.get("pattern"):
                score -= 0.3
            if not content.get("key_components"):
                score -= 0.3

        elif pattern_type == "requirements":
            if not content.get("domain"):
                score -= 0.2
            if not content.get("core_features"):
                score -= 0.3

        return max(0.0, score)

    def save_pattern(self, pattern: ProjectPattern):
        try:
            db = self._get_db()
            db.execute("""
                INSERT OR REPLACE INTO project_patterns
                (pattern_type, content, success_count, quality_score, last_used, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                pattern.pattern_type,
                json.dumps(pattern.content, ensure_ascii=False),
                pattern.success_count,
                pattern.quality_score,
                pattern.last_used,
                pattern.created_at
            ))

            if pattern.pattern_type not in self.patterns:
                self.patterns[pattern.pattern_type] = []
            self.patterns[pattern.pattern_type].append(pattern)

            logger.info(f"Saved pattern: {pattern.pattern_type}")

        except Exception as e:
            logger.error(f"Error saving pattern: {e}")

    def get_patterns(self, pattern_type: str = None,
                    min_quality: float = 0.7) -> List[ProjectPattern]:
        if pattern_type:
            patterns = self.patterns.get(pattern_type, [])
        else:
            patterns = [p for patterns in self.patterns.values() for p in patterns]

        return [p for p in patterns if p.quality_score >= min_quality]

    def find_similar_patterns(self, project_data: Dict[str, Any],
                             threshold: float = 0.6) -> List[ProjectPattern]:
        similar = []

        for pattern_type, patterns in self.patterns.items():
            type_data = project_data.get(pattern_type, {})
            if not type_data:
                continue
            for pattern in patterns:
                similarity = self._calculate_similarity(
                    type_data,
                    pattern.content
                )
                if similarity >= threshold:
                    similar.append(pattern)

        return similar

    def _extract_features(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        features = {}

        tech_stack = project_data.get("tech_stack", {})
        if tech_stack:
            features["tech_stack"] = tech_stack

        requirements = project_data.get("requirements", {})
        if requirements:
            features["requirements"] = requirements

        return features

    def _calculate_similarity(self, features1: Dict[str, Any],
                             features2: Dict[str, Any]) -> float:
        if not features1 or not features2:
            return 0.0

        common_fields = 0
        total_fields = 0

        for key in set(list(features1.keys()) + list(features2.keys())):
            total_fields += 1
            if key in features1 and key in features2:
                if str(features1[key]) == str(features2[key]):
                    common_fields += 1

        return common_fields / total_fields if total_fields > 0 else 0.0

    def update_pattern_usage(self, pattern: ProjectPattern):
        pattern.success_count += 1
        pattern.last_used = datetime.now().isoformat()
        self.save_pattern(pattern)

    def get_pattern_stats(self) -> Dict[str, Any]:
        stats = {
            "total_patterns": sum(len(v) for v in self.patterns.values()),
            "by_type": {
                pattern_type: len(patterns)
                for pattern_type, patterns in self.patterns.items()
            },
            "avg_quality": 0.0,
            "most_used": None
        }

        all_patterns = [p for patterns in self.patterns.values() for p in patterns]
        if all_patterns:
            stats["avg_quality"] = sum(p.quality_score for p in all_patterns) / len(all_patterns)

            most_used = max(all_patterns, key=lambda p: p.success_count)
            stats["most_used"] = {
                "type": most_used.pattern_type,
                "success_count": most_used.success_count
            }

        return stats
