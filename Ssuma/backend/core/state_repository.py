"""统一状态持久化仓库

将散落在各类变量中的服务状态统一持久化到 SQLite，
解决重启后状态丢失的核心问题。

设计原则：
1. Write-Through：写入时同时更新内存缓存和DB，读取优先命中缓存
2. 逐服务迁移：每个服务可独立启用/禁用持久化
3. 秒级回退：STATE_REPO_ENABLED=False 可立即回退到纯内存模式
4. JSON 序列化：所有状态以 JSON 存储，dataclass 需实现 to_dict()/from_dict()
"""
import os
import json
import logging
import sqlite3
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger('Ssuma.StateRepository')

# 全局开关：设为 False 可秒级回退到纯内存模式
STATE_REPO_ENABLED = os.environ.get("STATE_REPO_ENABLED", "true").lower() == "true"


class StateRepository:
    _db_path: str = ""
    _cache: Dict[str, Dict[str, Any]] = {}
    _initialized: bool = False
    _max_entries_per_service: int = 500
    _access_order: Dict[str, List[str]] = {}

    @classmethod
    def initialize(cls, db_path: Optional[str] = None):
        if cls._initialized:
            return

        if db_path is None:
            from core.config import Config
            config = Config()
            db_path = config.storage.get("db_path", "./ssuma.db")

        cls._db_path = db_path
        cls._ensure_table()
        cls._initialized = True
        logger.info(f"StateRepository initialized (enabled={STATE_REPO_ENABLED}, db={db_path})")

    @classmethod
    def _ensure_table(cls):
        """确保 service_states 表存在"""
        conn = cls._get_connection()
        cursor = conn.cursor()
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
        conn.commit()
        conn.close()

    @classmethod
    def _get_connection(cls) -> sqlite3.Connection:
        db_dir = Path(cls._db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(cls._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def save(cls, service_name: str, project_id: str, state_data: Any) -> bool:
        if service_name not in cls._cache:
            cls._cache[service_name] = {}
        cls._cache[service_name][project_id] = state_data

        if service_name not in cls._access_order:
            cls._access_order[service_name] = []
        if project_id in cls._access_order[service_name]:
            cls._access_order[service_name].remove(project_id)
        cls._access_order[service_name].append(project_id)

        if len(cls._cache[service_name]) > cls._max_entries_per_service:
            cls._evict_lru(service_name)

        if not STATE_REPO_ENABLED:
            return True

        try:
            from datetime import datetime
            json_data = json.dumps(state_data, ensure_ascii=False, default=str)
            conn = cls._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO service_states (service_name, project_id, state_data, updated_at)
                VALUES (?, ?, ?, ?)
            """, (service_name, project_id, json_data, datetime.now().isoformat()))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"StateRepository.save failed: service={service_name}, project={project_id}, error={e}")
            return False

    @classmethod
    def _evict_lru(cls, service_name: str):
        """LRU 淘汰：移除最久未访问的缓存条目（仅移除内存缓存，DB保留）"""
        evict_count = len(cls._cache[service_name]) - cls._max_entries_per_service + 50
        if evict_count <= 0:
            return

        order = cls._access_order.get(service_name, [])
        for i in range(min(evict_count, len(order))):
            old_id = order[i]
            if old_id in cls._cache[service_name]:
                del cls._cache[service_name][old_id]

        cls._access_order[service_name] = order[evict_count:]
        logger.info(f"StateRepository LRU evicted {evict_count} entries for service={service_name}")

    @classmethod
    def load(cls, service_name: str, project_id: str) -> Optional[Any]:
        """加载服务状态（优先命中缓存）

        Args:
            service_name: 服务标识
            project_id: 项目ID

        Returns:
            状态数据（反序列化后的 Python 对象），不存在返回 None
        """
        # 1. 命中缓存
        if service_name in cls._cache and project_id in cls._cache[service_name]:
            return cls._cache[service_name][project_id]

        if not STATE_REPO_ENABLED:
            return None

        # 2. 从DB加载
        try:
            conn = cls._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT state_data FROM service_states WHERE service_name = ? AND project_id = ?",
                (service_name, project_id)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                data = json.loads(row["state_data"])
                # 回填缓存
                if service_name not in cls._cache:
                    cls._cache[service_name] = {}
                cls._cache[service_name][project_id] = data
                return data
            return None
        except Exception as e:
            logger.error(f"StateRepository.load failed: service={service_name}, project={project_id}, error={e}")
            return None

    @classmethod
    def load_all(cls, service_name: str) -> Dict[str, Any]:
        """加载某个服务的所有项目状态

        Returns:
            {project_id: state_data} 字典
        """
        # 1. 从缓存中获取已有的
        cached = cls._cache.get(service_name, {})

        if not STATE_REPO_ENABLED:
            return dict(cached)

        # 2. 从DB加载（合并，DB为准）
        try:
            conn = cls._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT project_id, state_data FROM service_states WHERE service_name = ?",
                (service_name,)
            )
            rows = cursor.fetchall()
            conn.close()

            result = {}
            for row in rows:
                result[row["project_id"]] = json.loads(row["state_data"])

            # 回填缓存
            cls._cache[service_name] = result
            return result
        except Exception as e:
            logger.error(f"StateRepository.load_all failed: service={service_name}, error={e}")
            return dict(cached)

    @classmethod
    def delete(cls, service_name: str, project_id: str) -> bool:
        """删除某项目在某服务下的状态"""
        # 1. 清除缓存
        if service_name in cls._cache and project_id in cls._cache[service_name]:
            del cls._cache[service_name][project_id]

        if not STATE_REPO_ENABLED:
            return True

        # 2. 删除DB记录
        try:
            conn = cls._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM service_states WHERE service_name = ? AND project_id = ?",
                (service_name, project_id)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"StateRepository.delete failed: service={service_name}, project={project_id}, error={e}")
            return False

    @classmethod
    def delete_all(cls, project_id: str) -> bool:
        """删除某项目在所有服务下的状态"""
        # 1. 清除缓存
        for service_name in cls._cache:
            if project_id in cls._cache[service_name]:
                del cls._cache[service_name][project_id]

        if not STATE_REPO_ENABLED:
            return True

        # 2. 删除DB记录
        try:
            conn = cls._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM service_states WHERE project_id = ?",
                (project_id,)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"StateRepository.delete_all failed: project={project_id}, error={e}")
            return False

    @classmethod
    def restore_all_services(cls) -> Dict[str, int]:
        """启动时恢复所有服务的状态

        Returns:
            {service_name: restored_count} 各服务恢复的项目数
        """
        if not STATE_REPO_ENABLED:
            return {}

        try:
            conn = cls._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT service_name FROM service_states")
            services = [row["service_name"] for row in cursor.fetchall()]
            conn.close()

            result = {}
            for service_name in services:
                all_states = cls.load_all(service_name)
                result[service_name] = len(all_states)

            total = sum(result.values())
            logger.info(f"StateRepository restored {total} states across {len(result)} services: {result}")
            return result
        except Exception as e:
            logger.error(f"StateRepository.restore_all_services failed: {e}")
            return {}
