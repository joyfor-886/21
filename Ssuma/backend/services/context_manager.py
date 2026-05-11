import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from core.state_repository import StateRepository

logger = logging.getLogger('Ssuma.ContextManager')

STATE_SERVICE_NAME = "context_window"

DEFAULT_MAX_RECENT_MESSAGES = 10
DEFAULT_MAX_CONTEXT_CHARS = 8000
DEFAULT_SUMMARY_TRIGGER_CHARS = 5000
MAX_INMEMORY_WINDOWS = 200

MAX_RECENT_MESSAGES = DEFAULT_MAX_RECENT_MESSAGES
MAX_CONTEXT_CHARS = DEFAULT_MAX_CONTEXT_CHARS
SUMMARY_TRIGGER_CHARS = DEFAULT_SUMMARY_TRIGGER_CHARS


def configure_context_limits(
    max_recent: int = None,
    max_chars: int = None,
    summary_trigger: int = None,
):
    global MAX_RECENT_MESSAGES, MAX_CONTEXT_CHARS, SUMMARY_TRIGGER_CHARS
    if max_recent is not None:
        MAX_RECENT_MESSAGES = max_recent
    if max_chars is not None:
        MAX_CONTEXT_CHARS = max_chars
    if summary_trigger is not None:
        SUMMARY_TRIGGER_CHARS = summary_trigger


def auto_configure_context_limits():
    """根据模型能力自动调整上下文阈值"""
    try:
        from core.llm_adapter import get_llm_adapter
        from core.llm_factory import LLMFactory
        from domain.enums import ModelTier

        adapter = get_llm_adapter()
        provider_name = LLMFactory.get_default_provider()
        provider = LLMFactory.get_provider(provider_name)
        model_name = getattr(provider, "model", "")

        tier = adapter.detect_tier(model_name)

        if tier == ModelTier.INSUFFICIENT:
            configure_context_limits(
                max_recent=5,
                max_chars=4000,
                summary_trigger=2500,
            )
            logger.info("Context limits adjusted for INSUFFICIENT model tier")
        elif tier == ModelTier.BASIC:
            configure_context_limits(
                max_recent=8,
                max_chars=6000,
                summary_trigger=4000,
            )
            logger.info("Context limits adjusted for BASIC model tier")
        else:
            configure_context_limits(
                max_recent=DEFAULT_MAX_RECENT_MESSAGES,
                max_chars=DEFAULT_MAX_CONTEXT_CHARS,
                summary_trigger=DEFAULT_SUMMARY_TRIGGER_CHARS,
            )
            logger.info("Context limits set to defaults for ADEQUATE model tier")
    except Exception as e:
        logger.warning(f"Auto-configure context limits failed: {e}")


@dataclass
class ContextWindow:
    summary: str = ""
    recent_messages: List[Dict[str, str]] = field(default_factory=list)
    key_decisions: List[str] = field(default_factory=list)
    total_chars: int = 0
    max_recent_messages: int = DEFAULT_MAX_RECENT_MESSAGES
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS
    summary_trigger_chars: int = DEFAULT_SUMMARY_TRIGGER_CHARS

    def add_message(self, role: str, content: str):
        self.recent_messages.append({"role": role, "content": content})
        self.total_chars += len(content)
        
        if len(self.recent_messages) > self.max_recent_messages:
            self.recent_messages.pop(0)
        
        self._trim_to_size()

    def _trim_to_size(self):
        while self.total_chars > self.max_context_chars and self.recent_messages:
            removed = self.recent_messages.pop(0)
            self.total_chars -= len(removed["content"])

    def needs_summary(self) -> bool:
        return self.total_chars > self.summary_trigger_chars

    def to_context_string(self) -> str:
        parts = []
        
        if self.summary:
            parts.append(f"## 之前对话摘要\n{self.summary}\n")
        
        if self.key_decisions:
            parts.append("## 关键决策\n" + "\n".join(f"- {d}" for d in self.key_decisions) + "\n")
        
        if self.recent_messages:
            parts.append("## 最近对话\n" + "\n".join(
                f"{msg['role']}: {msg['content']}" for msg in self.recent_messages
            ))
        
        return "\n".join(parts)

    def to_messages_format(self) -> List[Dict[str, str]]:
        messages = []
        
        if self.summary or self.key_decisions:
            context_parts = []
            if self.summary:
                context_parts.append(f"之前对话摘要：\n{self.summary}")
            if self.key_decisions:
                context_parts.append(f"关键决策：\n{chr(10).join(self.key_decisions)}")
            
            messages.append({
                "role": "system",
                "content": "以下是之前对话的上下文，请在此基础上继续：\n\n" + "\n\n".join(context_parts)
            })
        
        messages.extend(self.recent_messages)
        return messages

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "recent_messages": self.recent_messages,
            "key_decisions": self.key_decisions,
            "total_chars": self.total_chars,
            "max_recent_messages": self.max_recent_messages,
            "max_context_chars": self.max_context_chars,
            "summary_trigger_chars": self.summary_trigger_chars,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextWindow":
        return cls(
            summary=data.get("summary", ""),
            recent_messages=data.get("recent_messages", []),
            key_decisions=data.get("key_decisions", []),
            total_chars=data.get("total_chars", 0),
            max_recent_messages=data.get("max_recent_messages", DEFAULT_MAX_RECENT_MESSAGES),
            max_context_chars=data.get("max_context_chars", DEFAULT_MAX_CONTEXT_CHARS),
            summary_trigger_chars=data.get("summary_trigger_chars", DEFAULT_SUMMARY_TRIGGER_CHARS),
        )


class ContextManager:
    """Manages conversation context with rolling summaries."""
    
    _instances: Dict[str, ContextWindow] = {}

    @classmethod
    def _ensure_loaded(cls, project_id: str):
        """确保项目数据已从 StateRepository 加载"""
        if project_id not in cls._instances:
            data = StateRepository.load(STATE_SERVICE_NAME, project_id)
            if data is not None:
                cls._instances[project_id] = ContextWindow.from_dict(data)
            else:
                window = ContextWindow()
                window.max_recent_messages = MAX_RECENT_MESSAGES
                window.max_context_chars = MAX_CONTEXT_CHARS
                window.summary_trigger_chars = SUMMARY_TRIGGER_CHARS
                cls._instances[project_id] = window
            cls._evict_if_needed()

    @classmethod
    def _evict_if_needed(cls):
        if len(cls._instances) <= MAX_INMEMORY_WINDOWS:
            return
        evict_count = len(cls._instances) - MAX_INMEMORY_WINDOWS + 10
        keys_to_evict = list(cls._instances.keys())[:evict_count]
        for key in keys_to_evict:
            del cls._instances[key]
        logger.info(f"Evicted {len(keys_to_evict)} context windows from memory")

    @classmethod
    def _save_to_repo(cls, project_id: str):
        """保存到 StateRepository"""
        window = cls._instances.get(project_id)
        if window:
            StateRepository.save(STATE_SERVICE_NAME, project_id, window.to_dict())

    @classmethod
    def get_window(cls, project_id: str) -> ContextWindow:
        cls._ensure_loaded(project_id)
        if project_id not in cls._instances:
            cls._instances[project_id] = ContextWindow()
        return cls._instances[project_id]

    @classmethod
    def add_message(cls, project_id: str, role: str, content: str):
        window = cls.get_window(project_id)
        window.add_message(role, content)
        cls._save_to_repo(project_id)

    @classmethod
    def add_decision(cls, project_id: str, decision: str):
        window = cls.get_window(project_id)
        if decision not in window.key_decisions:
            window.key_decisions.append(decision)
        cls._save_to_repo(project_id)

    @classmethod
    async def summarize_context(cls, project_id: str, llm_provider) -> str:
        window = cls.get_window(project_id)
        
        if not window.needs_summary():
            return window.summary
        
        conversation_text = "\n".join(
            f"{msg['role']}: {msg['content']}" for msg in window.recent_messages
        )
        
        prompt = f"""请将以下对话历史总结为 200 字以内的摘要，保留关键信息、用户需求和做出的决策。

对话历史：
{conversation_text}

当前已有摘要：
{window.summary or "无"}

请结合当前摘要和新对话，生成一份更新后的完整摘要。只输出摘要内容。"""

        try:
            new_summary = await llm_provider.chat(
                [{"role": "user", "content": prompt}],
                max_tokens=512,
                temperature=0.3
            )
            
            old_summary = window.summary
            window.summary = new_summary.strip()
            window.total_chars = sum(len(msg["content"]) for msg in window.recent_messages)
            window.recent_messages = window.recent_messages[-3:]
            
            cls._save_to_repo(project_id)
            logger.info(f"Context summarized: project={project_id}, old_len={len(old_summary)}, new_len={len(new_summary)}")
            return window.summary
        except Exception as e:
            logger.error(f"Context summarization failed: {e}")
            return window.summary

    @classmethod
    def reset(cls, project_id: str):
        if project_id in cls._instances:
            del cls._instances[project_id]
        StateRepository.delete(STATE_SERVICE_NAME, project_id)

    @classmethod
    def clear_window(cls, project_id: str):
        if project_id in cls._instances:
            del cls._instances[project_id]
        StateRepository.delete(STATE_SERVICE_NAME, project_id)

    @classmethod
    def get_status(cls, project_id: str) -> Dict[str, Any]:
        window = cls.get_window(project_id)
        return {
            "summary_length": len(window.summary),
            "recent_messages_count": len(window.recent_messages),
            "key_decisions_count": len(window.key_decisions),
            "total_chars": window.total_chars,
            "needs_summary": window.needs_summary(),
        }

    # ===== P0-04: 统一上下文构建入口 =====

    @classmethod
    def build_conversation_string(
        cls,
        project_id: str,
        db=None,
        max_chars: int = 10000,
        recent_n: int = 10,
    ) -> str:
        """统一的对话字符串构建入口

        将 DB 历史消息 + ContextManager 摘要合并为纯文本字符串，
        供需要 conversation: str 参数的路径使用（如 IntentAnalyzer、Skill.run）。

        Args:
            project_id: 项目ID
            db: Database 实例（可选，不传则纯用 ContextManager）
            max_chars: 最大字符数
            recent_n: 从 DB 取最近 N 条消息

        Returns:
            格式如 "user: xxx\nassistant: yyy" 的纯文本字符串
        """
        window = cls.get_window(project_id)
        parts = []

        # 1. 优先使用 ContextManager 的摘要（若 DB 不可用）
        if window.summary:
            parts.append(f"[对话摘要] {window.summary}")

        # 2. 从 DB 获取历史消息（若有 DB 实例）
        if db is not None:
            try:
                rows = db.fetchall(
                    "SELECT role, content FROM messages WHERE project_id = ? ORDER BY timestamp ASC",
                    (project_id,)
                )
                if rows:
                    recent_rows = rows[-recent_n:]
                    for row in recent_rows:
                        parts.append(f"{row['role']}: {row['content']}")
            except Exception as e:
                logger.warning(f"build_conversation_string: DB read failed, falling back to context window: {e}")
                # 降级：使用 ContextManager 的 recent_messages
                for msg in window.recent_messages:
                    parts.append(f"{msg['role']}: {msg['content']}")
        else:
            # 无 DB，使用 ContextManager 的 recent_messages
            for msg in window.recent_messages:
                parts.append(f"{msg['role']}: {msg['content']}")

        text = "\n".join(parts)
        if len(text) > max_chars:
            text = text[-max_chars:]
        return text

    @classmethod
    def build_llm_messages(
        cls,
        project_id: str,
        new_message: str,
        db=None,
        system_prompt: str = "",
        max_history: int = 10,
    ) -> List[Dict[str, str]]:
        """统一的结构化消息列表构建入口

        构建 LLM chat() 所需的 messages 列表：
        [system_prompt, ...context_messages, ...db_history, user_new_message]

        Args:
            project_id: 项目ID
            new_message: 当前用户消息
            db: Database 实例（可选）
            system_prompt: 系统提示词
            max_history: 从 DB 取的最大历史消息数

        Returns:
            适合传给 LLM provider.chat() 的 messages 列表
        """
        window = cls.get_window(project_id)
        messages: List[Dict[str, str]] = []

        # 1. 系统提示词
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 2. ContextManager 的摘要 + 关键决策（作为系统上下文注入）
        context_parts = []
        if window.summary:
            context_parts.append(f"之前对话摘要：\n{window.summary}")
        if window.key_decisions:
            context_parts.append(f"关键决策：\n{chr(10).join(window.key_decisions)}")

        if context_parts:
            messages.append({
                "role": "system",
                "content": "以下是之前对话的上下文，请在此基础上继续：\n\n" + "\n\n".join(context_parts)
            })

        # 3. 从 DB 加载历史对话消息（比 ContextManager.recent_messages 更完整）
        if db is not None:
            try:
                rows = db.fetchall(
                    "SELECT role, content FROM messages WHERE project_id = ? ORDER BY timestamp ASC",
                    (project_id,)
                )
                if rows:
                    recent_rows = rows[-max_history:]
                    for row in recent_rows:
                        messages.append({"role": row["role"], "content": row["content"]})
            except Exception as e:
                logger.warning(f"build_llm_messages: DB read failed, falling back to context window: {e}")
                messages.extend(window.recent_messages)
        else:
            messages.extend(window.recent_messages)

        # 4. 当前用户消息
        messages.append({"role": "user", "content": new_message})

        return messages
