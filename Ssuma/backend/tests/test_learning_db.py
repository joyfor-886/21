import json
import pytest
from datetime import datetime
from core.learning_db import LearningDB


class MockDB:
    def __init__(self):
        import sqlite3
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._pending_rowcount = 0

    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS learning_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                phase TEXT,
                satisfaction REAL DEFAULT 0,
                success INTEGER DEFAULT 0,
                quality_score REAL DEFAULT 0,
                timestamp TEXT,
                validated INTEGER DEFAULT 0,
                meta_info TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS learning_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT NOT NULL,
                satisfaction REAL NOT NULL,
                timestamp TEXT,
                user_comment TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS metacognition_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                analysis_data TEXT NOT NULL,
                evolution_triggered INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

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


def make_quality_response():
    return (
        "分析当前需求后发现，核心痛点在于数据处理效率低下。"
        "建议在 src/services/processor.py 中实现并行处理方案，"
        "同时在服务端支持批量操作，确保系统吞吐量。"
        "测试结果显示该方案可将处理时间从 30 秒降低到 2 秒以内。"
        "具体实现可参考以下代码：\n\n"
        "```python\n"
        "from concurrent.futures import ThreadPoolExecutor\n\n"
        "def process_items(items):\n"
        "    with ThreadPoolExecutor(max_workers=4) as executor:\n"
        "        results = list(executor.map(process_one, items))\n"
        "    return results\n"
        "```\n\n"
        "以上方案覆盖了项目的核心功能需求。"
    )


@pytest.fixture
def mock_db():
    db = MockDB()
    yield db
    db.close()


@pytest.fixture
def learning_db(mock_db):
    return LearningDB(db=mock_db)


class TestLearningDB:

    def test_add_learning_entry_approved(self, learning_db, mock_db):
        response = make_quality_response()
        result = learning_db.add_learning_entry(
            prompt="分析需求",
            response=response,
            skill_name="zhenwei",
            phase="analysis",
            satisfaction=0.9,
            success=True,
        )
        assert result is True

        row = mock_db.fetchone("SELECT * FROM learning_entries WHERE skill_name = ?", ("zhenwei",))
        assert row is not None
        assert row["prompt"] == "分析需求"
        assert row["validated"] == 1

    def test_add_learning_entry_rejected_short(self, learning_db):
        result = learning_db.add_learning_entry(
            prompt="hello",
            response="好的",
            skill_name="qishu",
        )
        assert result is False

    def test_add_learning_entry_rejected_garbage(self, learning_db):
        response = "好的，我来帮你分析一下。" + "a" * 200
        result = learning_db.add_learning_entry(
            prompt="test",
            response=response,
            skill_name="qishu",
        )
        assert result is False

    def test_get_skill_stats_empty(self, learning_db):
        stats = learning_db.get_skill_stats("qishu")
        assert stats == {}

    def test_get_skill_stats_with_data(self, learning_db, mock_db):
        response = make_quality_response()
        ts = datetime.now().isoformat()
        mock_db.execute("""
            INSERT INTO learning_entries (prompt, response, skill_name, phase, satisfaction, success, quality_score, timestamp, validated, meta_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("p1", response, "qishu", "analysis", 0.9, 1, 0.8, ts, 1, "{}"))
        mock_db.execute("""
            INSERT INTO learning_entries (prompt, response, skill_name, phase, satisfaction, success, quality_score, timestamp, validated, meta_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("p2", response, "qishu", "analysis", 0.8, 1, 0.75, ts, 1, "{}"))

        stats = learning_db.get_skill_stats("qishu")
        assert stats["total_calls"] == 2
        assert abs(stats["avg_satisfaction"] - 0.85) < 0.01
        assert stats["success_rate"] == 1.0

    def test_get_skill_stats_counts_unvalidated(self, learning_db, mock_db):
        ts = datetime.now().isoformat()
        mock_db.execute("""
            INSERT INTO learning_entries (prompt, response, skill_name, phase, satisfaction, success, quality_score, timestamp, validated, meta_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("p1", "good", "caiheng", "review", 0.9, 1, 0.8, ts, 1, "{}"))
        mock_db.execute("""
            INSERT INTO learning_entries (prompt, response, skill_name, phase, satisfaction, success, quality_score, timestamp, validated, meta_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("p2", "bad", "caiheng", "review", 0.3, 0, 0.2, ts, 0, "{}"))

        stats = learning_db.get_skill_stats("caiheng")
        assert stats["total_calls"] == 1
        assert stats["success_rate"] == 1.0

    def test_get_learning_stats(self, learning_db, mock_db):
        response = make_quality_response()
        ts = datetime.now().isoformat()
        mock_db.execute("""
            INSERT INTO learning_entries (prompt, response, skill_name, phase, satisfaction, success, quality_score, timestamp, validated, meta_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("p1", response, "qishu", "a", 0.9, 1, 0.8, ts, 1, "{}"))
        mock_db.execute("""
            INSERT INTO learning_entries (prompt, response, skill_name, phase, satisfaction, success, quality_score, timestamp, validated, meta_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("p2", "short", "caiheng", "b", 0.5, 0, 0.3, ts, 0, "{}"))

        stats = learning_db.get_learning_stats()
        assert stats["total_entries"] == 2
        assert stats["high_quality_entries"] == 1
        assert stats["quality_ratio"] == 0.5

    def test_add_feedback(self, learning_db, mock_db):
        learning_db.add_feedback(
            skill_name="zhenwei",
            satisfaction=0.85,
            user_comment="分析很到位",
        )
        row = mock_db.fetchone("SELECT * FROM learning_feedback WHERE skill_name = ?", ("zhenwei",))
        assert row is not None
        assert row["satisfaction"] == 0.85
        assert row["user_comment"] == "分析很到位"

    def test_add_feedback_no_comment(self, learning_db, mock_db):
        learning_db.add_feedback("qishu", 0.9)
        row = mock_db.fetchone("SELECT * FROM learning_feedback WHERE skill_name = ?", ("qishu",))
        assert row is not None

    def test_get_recent_feedbacks(self, learning_db, mock_db):
        ts = datetime.now().isoformat()
        mock_db.execute("""
            INSERT INTO learning_feedback (skill_name, satisfaction, timestamp, user_comment)
            VALUES (?, ?, ?, ?)
        """, ("qishu", 0.9, ts, "good"))
        mock_db.execute("""
            INSERT INTO learning_feedback (skill_name, satisfaction, timestamp, user_comment)
            VALUES (?, ?, ?, ?)
        """, ("caiheng", 0.8, ts, "nice"))

        feedbacks = learning_db.get_recent_feedbacks(limit=10)
        assert len(feedbacks) == 2
        assert feedbacks[0]["skill_name"] in ("qishu", "caiheng")

    def test_save_metacognition_analysis(self, learning_db, mock_db):
        analysis = {
            "timestamp": "2024-01-01T00:00:00",
            "evolution_needed": True,
            "skill_analysis": {"qishu": {"grade": "C"}},
        }
        learning_db.save_metacognition_analysis(analysis)

        row = mock_db.fetchone("SELECT * FROM metacognition_analysis")
        assert row is not None
        assert row["evolution_triggered"] == 1
        saved = json.loads(row["analysis_data"])
        assert saved["skill_analysis"]["qishu"]["grade"] == "C"

    def test_save_metacognition_analysis_no_evolution(self, learning_db, mock_db):
        analysis = {
            "timestamp": "2024-01-01T00:00:00",
            "evolution_needed": False,
        }
        learning_db.save_metacognition_analysis(analysis)

        row = mock_db.fetchone("SELECT * FROM metacognition_analysis")
        assert row["evolution_triggered"] == 0

    def test_get_learning_entries_by_skill(self, learning_db, mock_db):
        response = make_quality_response()
        ts = datetime.now().isoformat()
        mock_db.execute("""
            INSERT INTO learning_entries (prompt, response, skill_name, phase, satisfaction, success, quality_score, timestamp, validated, meta_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("p1", response, "qishu", "a", 0.9, 1, 0.9, ts, 1, "{}"))
        mock_db.execute("""
            INSERT INTO learning_entries (prompt, response, skill_name, phase, satisfaction, success, quality_score, timestamp, validated, meta_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("p2", response, "caiheng", "b", 0.8, 1, 0.8, ts, 1, "{}"))

        entries = learning_db.get_learning_entries(skill_name="qishu")
        assert len(entries) == 1
        assert entries[0]["skill_name"] == "qishu"

    def test_get_learning_entries_all(self, learning_db, mock_db):
        response = make_quality_response()
        ts = datetime.now().isoformat()
        mock_db.execute("""
            INSERT INTO learning_entries (prompt, response, skill_name, phase, satisfaction, success, quality_score, timestamp, validated, meta_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("p1", response, "qishu", "a", 0.9, 1, 0.9, ts, 1, "{}"))
        mock_db.execute("""
            INSERT INTO learning_entries (prompt, response, skill_name, phase, satisfaction, success, quality_score, timestamp, validated, meta_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("p2", response, "caiheng", "b", 0.8, 1, 0.8, ts, 1, "{}"))

        entries = learning_db.get_learning_entries()
        assert len(entries) == 2

    def test_get_learning_entries_min_quality(self, learning_db, mock_db):
        response = make_quality_response()
        ts = datetime.now().isoformat()
        mock_db.execute("""
            INSERT INTO learning_entries (prompt, response, skill_name, phase, satisfaction, success, quality_score, timestamp, validated, meta_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("p1", response, "qishu", "a", 0.9, 1, 0.9, ts, 1, "{}"))
        mock_db.execute("""
            INSERT INTO learning_entries (prompt, response, skill_name, phase, satisfaction, success, quality_score, timestamp, validated, meta_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("p2", response, "qishu", "b", 0.9, 1, 0.6, ts, 1, "{}"))

        entries = learning_db.get_learning_entries(skill_name="qishu", min_quality=0.8)
        assert len(entries) == 1
        assert entries[0]["quality_score"] == 0.9

    def test_cleanup_low_quality(self, learning_db, mock_db):
        ts = datetime.now().isoformat()
        mock_db.execute("""
            INSERT INTO learning_entries (prompt, response, skill_name, phase, satisfaction, success, quality_score, timestamp, validated, meta_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("p1", "good", "qishu", "a", 0.9, 1, 0.9, ts, 0, "{}"))
        mock_db.execute("""
            INSERT INTO learning_entries (prompt, response, skill_name, phase, satisfaction, success, quality_score, timestamp, validated, meta_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("p2", "bad", "qishu", "b", 0.3, 0, 0.3, ts, 0, "{}"))
        mock_db.execute("""
            INSERT INTO learning_entries (prompt, response, skill_name, phase, satisfaction, success, quality_score, timestamp, validated, meta_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("p3", "good", "qishu", "c", 0.9, 1, 0.9, ts, 1, "{}"))

        deleted = learning_db.cleanup_low_quality(threshold=0.5)
        assert deleted == 1

        remaining = mock_db.fetchall("SELECT * FROM learning_entries")
        assert len(remaining) == 2

    def test_add_learning_entry_twice(self, learning_db, mock_db):
        response = make_quality_response()
        r1 = learning_db.add_learning_entry("p", response, "qishu", "a", 0.9, True)
        r2 = learning_db.add_learning_entry("p", response, "qishu", "a", 0.9, True)
        assert r1 is True
        assert r2 is True

        rows = mock_db.fetchall("SELECT * FROM learning_entries")
        assert len(rows) == 2

    def test_get_learning_stats_by_skill(self, learning_db, mock_db):
        response = make_quality_response()
        ts = datetime.now().isoformat()
        for skill in ("qishu", "caiheng", "zhenwei"):
            mock_db.execute("""
                INSERT INTO learning_entries (prompt, response, skill_name, phase, satisfaction, success, quality_score, timestamp, validated, meta_info)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (f"p_{skill}", response, skill, "a", 0.85, 1, 0.8, ts, 1, "{}"))

        stats = learning_db.get_learning_stats()
        assert stats["total_entries"] == 3
        assert len(stats["by_skill"]) == 3
        skill_names = {s["skill_name"] for s in stats["by_skill"]}
        assert skill_names == {"qishu", "caiheng", "zhenwei"}
