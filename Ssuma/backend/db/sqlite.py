import sqlite3
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from core.config import Config


class Database:
    _instance = None
    _local = threading.local()
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_connection(self):
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            config = Config()
            db_path = config.storage.get("db_path", "./ssuma.db")
            db_dir = Path(db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

            self._local.conn = sqlite3.connect(db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn.execute("PRAGMA cache_size=-64000")
            self._create_tables()
            self._run_migrations()
        return self._local.conn

    def _init_db(self):
        self._get_connection()

    def _create_tables(self):
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                skill_used TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                content TEXT,
                content_length INTEGER DEFAULT 0,
                summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS specs (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flow_states (
                project_id TEXT PRIMARY KEY,
                current_phase TEXT NOT NULL DEFAULT 'intent_detection',
                intent_data TEXT,
                clarity_level TEXT,
                confidence REAL,
                workflow_history TEXT,
                conversation_turns INTEGER DEFAULT 0,
                questionnaire_completed BOOLEAN DEFAULT 0,
                analysis_completed BOOLEAN DEFAULT 0,
                plan_completed BOOLEAN DEFAULT 0,
                spec_generated BOOLEAN DEFAULT 0,
                collected_info TEXT,
                dimension_coverage TEXT,
                original_message TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                turn INTEGER DEFAULT 0,
                rating INTEGER NOT NULL,
                feedback_text TEXT,
                ai_response TEXT,
                phase TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS local_config (
                id INTEGER PRIMARY KEY DEFAULT 1,
                device_id TEXT NOT NULL,
                cloud_account TEXT,
                sync_enabled INTEGER DEFAULT 0,
                last_sync_at TIMESTAMP,
                global_version TEXT DEFAULT '0.1.0',
                llm_config TEXT,
                user_settings TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY DEFAULT 1,
                display_name TEXT DEFAULT '用户',
                expression_style TEXT,
                decision_style TEXT,
                detail_preference TEXT,
                modification_tendency TEXT,
                llm_tier TEXT DEFAULT 'unknown',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_knowledge (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                source_project_id TEXT,
                quality_score REAL DEFAULT 0,
                usage_count INTEGER DEFAULT 0,
                sync_status TEXT DEFAULT 'local',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classical_culture (
                id TEXT PRIMARY KEY,
                original TEXT NOT NULL,
                source TEXT NOT NULL,
                english TEXT,
                tags TEXT,
                usage_count INTEGER DEFAULT 0,
                rating REAL DEFAULT 0,
                version_added TEXT DEFAULT '0.1.0'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS penalty_records (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                offense_count INTEGER DEFAULT 1,
                penalty_until TIMESTAMP,
                last_offense_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evolution_logs (
                id TEXT PRIMARY KEY,
                zone TEXT NOT NULL,
                change_type TEXT NOT NULL,
                content TEXT NOT NULL,
                trigger_reason TEXT,
                approval_status TEXT,
                effect_score REAL,
                rolled_back INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_records (
                id TEXT PRIMARY KEY,
                direction TEXT NOT NULL,
                content_type TEXT NOT NULL,
                content_id TEXT,
                status TEXT DEFAULT 'pending',
                server_response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_annotations (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                content TEXT NOT NULL,
                author TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            )
        """)

        cursor.execute("""
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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT NOT NULL,
                satisfaction REAL NOT NULL,
                timestamp TEXT,
                user_comment TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metacognition_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                analysis_data TEXT NOT NULL,
                evolution_triggered INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
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

        conn = self._get_connection()
        conn.commit()

        try:
            cursor.execute("ALTER TABLE documents ADD COLUMN content_length INTEGER DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError:
            pass

        self._create_indexes()

    def _create_indexes(self):
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_project_id
            ON messages(project_id, timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_project_id
            ON documents(project_id, created_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_specs_project_id
            ON specs(project_id, created_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_projects_status
            ON projects(status, created_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_learning_entries_skill
            ON learning_entries(skill_name, validated, quality_score)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_learning_feedback_skill
            ON learning_feedback(skill_name, timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_metacognition_timestamp
            ON metacognition_analysis(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_project_patterns_type
            ON project_patterns(pattern_type, quality_score)
        """)

        conn.commit()

    def _run_migrations(self):
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
        """)
        conn.commit()

        for migration in MIGRATIONS:
            cursor.execute(
                "SELECT 1 FROM schema_migrations WHERE version = ?",
                (migration["version"],)
            )
            if cursor.fetchone() is None:
                try:
                    migration["up"](cursor)
                    cursor.execute(
                        "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                        (migration["version"], migration["name"], datetime.now().isoformat())
                    )
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    import logging
                    logging.getLogger('Ssuma.Database').error(
                        f"Migration v{migration['version']} failed: {e}"
                    )
                    raise

    def execute(self, query: str, params: tuple = ()):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor

    def fetchone(self, query: str, params: tuple = ()):
        cursor = self.execute(query, params)
        return cursor.fetchone()

    def fetchall(self, query: str, params: tuple = ()):
        cursor = self.execute(query, params)
        return cursor.fetchall()

    def execute_many(self, query: str, params_list: list):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        conn.commit()
        return cursor

    def transaction(self):
        return TransactionContext(self)

    def close(self):
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


class TransactionContext:
    def __init__(self, db: Database):
        self.db = db

    def __enter__(self):
        conn = self.db._get_connection()
        conn.execute("BEGIN")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        conn = self.db._get_connection()
        if exc_type is None:
            conn.commit()
        else:
            conn.rollback()
        return False

    def execute(self, query: str, params: tuple = ()):
        conn = self.db._get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor

    def fetchone(self, query: str, params: tuple = ()):
        cursor = self.execute(query, params)
        return cursor.fetchone()

    def fetchall(self, query: str, params: tuple = ()):
        cursor = self.execute(query, params)
        return cursor.fetchall()


def _migration_v1(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS service_states (
            service_name TEXT NOT NULL,
            project_id TEXT NOT NULL,
            state_data TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (service_name, project_id)
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_service_states_service
        ON service_states(service_name)
    """)


def _migration_v2(cursor):
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_feedback_project
        ON user_feedback(project_id, created_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_evolution_logs_zone
        ON evolution_logs(zone, created_at)
    """)


def _migration_v3(cursor):
    cursor.execute("""
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS learning_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_name TEXT NOT NULL,
            satisfaction REAL NOT NULL,
            timestamp TEXT,
            user_comment TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metacognition_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            analysis_data TEXT NOT NULL,
            evolution_triggered INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
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
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_learning_entries_skill
        ON learning_entries(skill_name, validated, quality_score)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_learning_feedback_skill
        ON learning_feedback(skill_name, timestamp)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_metacognition_timestamp
        ON metacognition_analysis(timestamp)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_project_patterns_type
        ON project_patterns(pattern_type, quality_score)
    """)


MIGRATIONS = [
    {"version": 1, "name": "add_service_states", "up": _migration_v1},
    {"version": 2, "name": "add_missing_indexes", "up": _migration_v2},
    {"version": 3, "name": "add_learning_tables", "up": _migration_v3},
]
