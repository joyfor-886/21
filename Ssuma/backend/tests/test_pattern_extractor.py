import json
import pytest
from datetime import datetime
from core.pattern_extractor import PatternExtractor, ProjectPattern


class MockDB:
    def __init__(self):
        import sqlite3
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS project_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                content TEXT NOT NULL,
                success_count INTEGER DEFAULT 1,
                quality_score REAL DEFAULT 1.0,
                last_used TEXT,
                created_at TEXT,
                UNIQUE(pattern_type, content)
            )
        """)
        self.conn.commit()
        self._pending_rowcount = 0

    def execute(self, query, params=()):
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        self._pending_rowcount = cursor.rowcount
        return cursor

    def fetchone(self, query, params=()):
        cursor = self.conn.execute(query, params)
        return cursor.fetchone()

    def fetchall(self, query, params=()):
        cursor = self.conn.execute(query, params)
        return cursor.fetchall()

    def close(self):
        self.conn.close()


@pytest.fixture
def mock_db():
    db = MockDB()
    yield db
    db.close()


@pytest.fixture
def extractor(mock_db):
    return PatternExtractor(db=mock_db)


class TestProjectPattern:

    def test_creation(self):
        pattern = ProjectPattern(
            pattern_type="tech_stack",
            content={"frontend": "React", "backend": "FastAPI"},
        )
        assert pattern.pattern_type == "tech_stack"
        assert pattern.content["frontend"] == "React"
        assert pattern.success_count == 1
        assert pattern.quality_score == 1.0
        assert pattern.last_used is not None
        assert pattern.created_at is not None

    def test_custom_values(self):
        pattern = ProjectPattern(
            pattern_type="architecture",
            content={"pattern": "microservices"},
            success_count=5,
            quality_score=0.8,
        )
        assert pattern.success_count == 5
        assert pattern.quality_score == 0.8

    def test_to_dict(self):
        content = {"frontend": "Vue", "backend": "Django"}
        pattern = ProjectPattern("tech_stack", content)
        d = pattern.to_dict()
        assert d["pattern_type"] == "tech_stack"
        assert d["content"] == content
        assert d["success_count"] == 1
        assert d["quality_score"] == 1.0


class TestPatternExtractor:

    def test_initialization_empty(self, extractor):
        assert extractor._db is not None
        assert extractor.patterns == {}

    def test_extract_from_project_full(self, extractor):
        project_data = {
            "tech_stack": {
                "frontend": "React",
                "backend": "FastAPI",
                "database": "PostgreSQL",
                "deployment": "Docker",
                "key_libraries": ["pydantic", "sqlalchemy"],
            },
            "architecture": {
                "pattern": "layered",
                "layers": ["api", "service", "data"],
                "key_components": ["router", "handler", "repository"],
                "data_flow": "REST",
            },
            "requirements": {
                "domain": "e-commerce",
                "core_features": ["user auth", "product catalog", "checkout"],
                "user_roles": ["admin", "customer"],
                "complexity": "high",
            },
        }
        patterns = extractor.extract_from_project(project_data)
        assert len(patterns) == 3

        types = {p.pattern_type for p in patterns}
        assert types == {"tech_stack", "architecture", "requirements"}

        for p in patterns:
            assert p.quality_score > 0

    def test_extract_tech_stack_incomplete(self, extractor):
        project_data = {
            "tech_stack": {
                "frontend": "React",
            }
        }
        patterns = extractor.extract_from_project(project_data)
        assert len(patterns) == 1
        assert patterns[0].pattern_type == "tech_stack"
        assert patterns[0].quality_score < 1.0

    def test_extract_from_project_empty(self, extractor):
        patterns = extractor.extract_from_project({})
        assert patterns == []

    def test_extract_from_project_partial(self, extractor):
        project_data = {
            "tech_stack": {"frontend": "React", "backend": "Node"},
            "requirements": {"domain": "finance"},
        }
        patterns = extractor.extract_from_project(project_data)
        assert len(patterns) == 2
        types = {p.pattern_type for p in patterns}
        assert types == {"tech_stack", "requirements"}

    def test_assess_quality_tech_stack_complete(self):
        content = {"frontend": "React", "backend": "FastAPI", "database": "PostgreSQL"}
        score = PatternExtractor._assess_pattern_quality(None, "tech_stack", content)
        assert score == 1.0

    def test_assess_quality_tech_stack_missing(self):
        content = {"frontend": "React"}
        score = PatternExtractor._assess_pattern_quality(None, "tech_stack", content)
        assert score < 1.0
        assert abs(score - 0.5) < 0.01

    def test_assess_quality_architecture_missing_pattern(self):
        content = {"key_components": ["router"]}
        score = PatternExtractor._assess_pattern_quality(None, "architecture", content)
        assert abs(score - 0.7) < 0.01

    def test_assess_quality_requirements_missing_features(self):
        content = {"domain": "finance"}
        score = PatternExtractor._assess_pattern_quality(None, "requirements", content)
        assert abs(score - 0.7) < 0.01

    def test_save_and_get_patterns(self, extractor):
        pattern = ProjectPattern("tech_stack", {"frontend": "React", "backend": "FastAPI"})
        extractor.save_pattern(pattern)

        loaded = extractor.get_patterns()
        assert len(loaded) == 1
        assert loaded[0].pattern_type == "tech_stack"
        assert loaded[0].content["frontend"] == "React"

    def test_save_and_get_patterns_by_type(self, extractor):
        p1 = ProjectPattern("tech_stack", {"frontend": "React"})
        p2 = ProjectPattern("architecture", {"pattern": "microservices"})
        extractor.save_pattern(p1)
        extractor.save_pattern(p2)

        tech_patterns = extractor.get_patterns(pattern_type="tech_stack")
        assert len(tech_patterns) == 1
        assert tech_patterns[0].pattern_type == "tech_stack"

    def test_get_patterns_with_min_quality(self, extractor):
        p1 = ProjectPattern("tech_stack", {"frontend": "React"}, quality_score=0.9)
        p2 = ProjectPattern("tech_stack", {"frontend": "Vue"}, quality_score=0.5)
        extractor.save_pattern(p1)
        extractor.save_pattern(p2)

        high_quality = extractor.get_patterns(min_quality=0.8)
        assert len(high_quality) == 1
        assert high_quality[0].content["frontend"] == "React"

    def test_save_pattern_persists_to_db(self, extractor, mock_db):
        pattern = ProjectPattern("tech_stack", {"frontend": "React", "backend": "FastAPI"})
        extractor.save_pattern(pattern)

        row = mock_db.fetchone(
            "SELECT * FROM project_patterns WHERE pattern_type = ?",
            ("tech_stack",)
        )
        assert row is not None
        content = json.loads(row["content"])
        assert content["frontend"] == "React"

    def test_find_similar_patterns(self, extractor):
        p1 = ProjectPattern("tech_stack", {"frontend": "React", "backend": "FastAPI"}, quality_score=0.9)
        extractor.save_pattern(p1)

        similar = extractor.find_similar_patterns(
            {"tech_stack": {"frontend": "React", "backend": "FastAPI"}},
            threshold=0.5,
        )
        assert len(similar) == 1

    def test_find_similar_patterns_no_match(self, extractor):
        p1 = ProjectPattern("tech_stack", {"frontend": "React"})
        extractor.save_pattern(p1)

        similar = extractor.find_similar_patterns(
            {"tech_stack": {"frontend": "Vue"}},
            threshold=0.9,
        )
        assert similar == []

    def test_calculate_similarity_exact(self, extractor):
        score = extractor._calculate_similarity(
            {"frontend": "React", "backend": "Node"},
            {"frontend": "React", "backend": "Node"},
        )
        assert score == 1.0

    def test_calculate_similarity_partial(self, extractor):
        score = extractor._calculate_similarity(
            {"frontend": "React", "backend": "Node"},
            {"frontend": "Vue", "backend": "Node"},
        )
        assert score == 0.5

    def test_calculate_similarity_no_match(self, extractor):
        score = extractor._calculate_similarity(
            {"frontend": "React"},
            {"backend": "Node"},
        )
        assert score == 0.0

    def test_calculate_similarity_empty(self, extractor):
        score = extractor._calculate_similarity({}, {})
        assert score == 0.0

    def test_update_pattern_usage(self, extractor):
        pattern = ProjectPattern("tech_stack", {"frontend": "React"})
        extractor.save_pattern(pattern)

        old_count = pattern.success_count
        extractor.update_pattern_usage(pattern)
        assert pattern.success_count == old_count + 1

    def test_get_pattern_stats_empty(self, extractor):
        stats = extractor.get_pattern_stats()
        assert stats["total_patterns"] == 0
        assert stats["avg_quality"] == 0.0
        assert stats["most_used"] is None

    def test_get_pattern_stats_with_data(self, extractor):
        p1 = ProjectPattern("tech_stack", {"f": "React"}, success_count=10, quality_score=0.9)
        p2 = ProjectPattern("tech_stack", {"f": "Vue"}, success_count=5, quality_score=0.8)
        p3 = ProjectPattern("architecture", {"p": "micro"}, success_count=3, quality_score=0.7)
        extractor.save_pattern(p1)
        extractor.save_pattern(p2)
        extractor.save_pattern(p3)

        stats = extractor.get_pattern_stats()
        assert stats["total_patterns"] == 3
        assert stats["by_type"]["tech_stack"] == 2
        assert stats["by_type"]["architecture"] == 1
        assert stats["most_used"]["type"] == "tech_stack"
        assert stats["most_used"]["success_count"] == 10

    def test_extract_tech_stack_none(self, extractor):
        result = extractor._extract_tech_stack({})
        assert result is None

    def test_extract_architecture_none(self, extractor):
        result = extractor._extract_architecture({})
        assert result is None

    def test_extract_requirements_none(self, extractor):
        result = extractor._extract_requirements({})
        assert result is None

    def test_load_patterns_from_db(self, mock_db):
        mock_db.execute("""
            INSERT INTO project_patterns (pattern_type, content, success_count, quality_score, last_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("tech_stack", json.dumps({"f": "React"}), 5, 0.9, "2024-01-01", "2024-01-01"))

        extractor = PatternExtractor(db=mock_db)
        patterns = extractor.get_patterns()
        assert len(patterns) == 1
        assert patterns[0].pattern_type == "tech_stack"

    def test_load_patterns_filters_low_quality(self, mock_db):
        mock_db.execute("""
            INSERT INTO project_patterns (pattern_type, content, success_count, quality_score)
            VALUES (?, ?, ?, ?)
        """, ("tech_stack", json.dumps({"f": "React"}), 5, 0.6))
        mock_db.execute("""
            INSERT INTO project_patterns (pattern_type, content, success_count, quality_score)
            VALUES (?, ?, ?, ?)
        """, ("tech_stack", json.dumps({"f": "Vue"}), 3, 0.8))

        extractor = PatternExtractor(db=mock_db)
        patterns = extractor.get_patterns()
        assert len(patterns) == 1
        assert patterns[0].content["f"] == "Vue"
