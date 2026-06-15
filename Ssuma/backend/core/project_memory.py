"""项目记忆卡 — 跨会话持久化的项目级记忆

三层记忆架构：
  第一层：工作记忆（ContextManager 滚动窗口）— 单次会话
  第二层：项目记忆（ProjectMemoryCard）— 跨会话持久化  ← 本文件
  第三层：进化记忆（EvolutionMemory）— 全局学习与微调

设计参考：
  - DeerFlow: LLM 驱动的长期记忆，每次对话结束自动总结
  - Agno: KnowledgeProtocol 知识协议，结构化存储+检索
  - Reflexion: 反思循环，从历史中提炼经验
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import json
import logging

logger = logging.getLogger('Ssuma.ProjectMemory')


class ProjectMemoryCard(BaseModel):
    """项目记忆卡 — 跨会话持久化的结构化项目记忆

    每个项目一张卡，在会话开始时加载、会话中更新、会话结束时持久化。
    """
    project_id: str
    project_name: str = ""

    # 需求摘要（探隐阶段产出）
    requirement_summary: str = ""
    core_features: List[str] = Field(default_factory=list)
    user_scenarios: List[str] = Field(default_factory=list)

    # 技术决策（裁衡/甄微阶段产出）
    tech_decisions: List[Dict[str, str]] = Field(default_factory=list)
    architecture_choices: List[str] = Field(default_factory=list)
    tech_stack: Dict[str, str] = Field(default_factory=dict)

    # 约束与承诺（策书阶段产出）
    commitments: List[Dict[str, str]] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)

    # 未解决问题
    open_questions: List[str] = Field(default_factory=list)

    # 流程元数据
    channel: str = "standard"
    phases_completed: List[str] = Field(default_factory=list)
    total_turns: int = 0
    last_phase: str = ""
    completion_scores: Dict[str, float] = Field(default_factory=dict)

    # 会话历史摘要
    session_summaries: List[Dict[str, str]] = Field(default_factory=list)

    # 时间戳
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def to_context_string(self) -> str:
        """生成供 LLM 使用的上下文字符串"""
        parts = [f"## 项目记忆卡: {self.project_name or self.project_id}"]

        if self.requirement_summary:
            parts.append(f"\n### 需求摘要\n{self.requirement_summary}")
        if self.core_features:
            parts.append(f"\n### 核心功能\n" + "\n".join(f"- {f}" for f in self.core_features[:10]))
        if self.tech_decisions:
            parts.append("\n### 技术决策")
            for d in self.tech_decisions[:5]:
                parts.append(f"- {d.get('decision', '')}: {d.get('rationale', '')}")
        if self.tech_stack:
            parts.append("\n### 技术栈")
            for k, v in self.tech_stack.items():
                parts.append(f"- {k}: {v}")
        if self.commitments:
            parts.append("\n### 承诺与约束")
            for c in self.commitments[:5]:
                parts.append(f"- [{c.get('category', '')}] {c.get('content', '')}")
        if self.constraints:
            parts.append("\n### 硬约束\n" + "\n".join(f"- {c}" for c in self.constraints[:5]))
        if self.open_questions:
            parts.append("\n### 待解决问题\n" + "\n".join(f"- {q}" for q in self.open_questions[:5]))
        if self.phases_completed:
            parts.append(f"\n### 已完成阶段: {', '.join(self.phases_completed)}")

        return "\n".join(parts)

    def update_from_artifact(self, phase: str, artifact: Dict[str, Any]) -> None:
        """从阶段产出更新记忆卡"""
        self.updated_at = datetime.now().isoformat()

        if phase == "tanyin":
            if artifact.get("summary"):
                self.requirement_summary = artifact["summary"]
            if artifact.get("decisions"):
                self.core_features = artifact["decisions"][:10]
            if artifact.get("open_questions"):
                self.open_questions = artifact["open_questions"][:5]

        elif phase == "caiheng":
            if artifact.get("decisions"):
                self.tech_decisions = [
                    {"decision": d, "rationale": ""} for d in artifact["decisions"][:5]
                ]
            if artifact.get("commitments"):
                self.commitments = artifact["commitments"][:5]

        elif phase == "zhenwei":
            if artifact.get("key_insights"):
                self.architecture_choices = artifact["key_insights"][:5]
            if artifact.get("decisions"):
                for d in artifact["decisions"][:3]:
                    self.tech_decisions.append({"decision": d, "rationale": "甄微阶段确认"})

        elif phase == "ceshu":
            if artifact.get("commitments"):
                self.constraints = [c.get("content", "") for c in artifact["commitments"][:5] if c.get("content")]

        if phase not in self.phases_completed:
            self.phases_completed.append(phase)

        if artifact.get("completion_score"):
            self.completion_scores[phase] = artifact["completion_score"]

    def add_session_summary(self, session_id: str, summary: str) -> None:
        """添加会话摘要"""
        self.session_summaries.append({
            "session_id": session_id,
            "summary": summary,
            "timestamp": datetime.now().isoformat(),
        })
        # 只保留最近 10 条会话摘要
        if len(self.session_summaries) > 10:
            self.session_summaries = self.session_summaries[-10:]
        self.updated_at = datetime.now().isoformat()


class ProjectMemoryStore:
    """项目记忆卡存储 — 基于 SQLite 持久化"""

    def __init__(self, db=None):
        self._db = db
        self._cache: Dict[str, ProjectMemoryCard] = {}

    def _get_db(self):
        if self._db is None:
            from db.sqlite import Database
            self._db = Database()
        return self._db

    def get(self, project_id: str) -> ProjectMemoryCard:
        """获取项目记忆卡，优先从缓存读取"""
        if project_id in self._cache:
            return self._cache[project_id]

        db = self._get_db()
        row = db.fetchone(
            "SELECT memory_data FROM project_memories WHERE project_id = ?",
            (project_id,)
        )
        if row:
            try:
                data = json.loads(row[0] if isinstance(row, tuple) else row["memory_data"])
                card = ProjectMemoryCard.model_validate(data)
                self._cache[project_id] = card
                return card
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to load memory card for {project_id}: {e}")

        # 创建空白记忆卡
        card = ProjectMemoryCard(project_id=project_id)
        self._cache[project_id] = card
        return card

    def save(self, card: ProjectMemoryCard) -> None:
        """持久化项目记忆卡"""
        self._cache[card.project_id] = card
        db = self._get_db()
        data = card.model_dump_json()

        try:
            existing = db.fetchone(
                "SELECT project_id FROM project_memories WHERE project_id = ?",
                (card.project_id,)
            )
            if existing:
                db.execute(
                    "UPDATE project_memories SET memory_data = ?, updated_at = ? WHERE project_id = ?",
                    (data, card.updated_at, card.project_id)
                )
            else:
                db.execute(
                    "INSERT INTO project_memories (project_id, memory_data, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (card.project_id, data, card.created_at, card.updated_at)
                )
        except Exception as e:
            logger.error(f"Failed to save memory card for {card.project_id}: {e}")

    def ensure_table(self) -> None:
        """确保 project_memories 表存在"""
        db = self._get_db()
        db.execute("""
            CREATE TABLE IF NOT EXISTS project_memories (
                project_id TEXT PRIMARY KEY,
                memory_data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
