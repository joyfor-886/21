from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging
import threading

from domain.results import SkillResult

logger = logging.getLogger('Ssuma.SkillRegistry')


class Skill(ABC):
    """Skill 基类

    参考 gstack 的角色分离模式：每个 Skill 扮演一个明确角色。
    参考 Dean Peters 的假设驱动发现：每个 Skill 有明确的必需输出维度。
    """
    name: str = ""
    description: str = ""
    trigger: str = ""
    required_outputs: List[str] = []

    @abstractmethod
    async def run(self, conversation: str, context: Dict[str, Any] = None) -> SkillResult:
        pass

    async def run_with_artifacts(
        self,
        conversation: str,
        artifact_context: str = "",
        context: Dict[str, Any] = None
    ) -> SkillResult:
        if artifact_context:
            enriched_conversation = f"{artifact_context}\n\n---\n\n{conversation}"
        else:
            enriched_conversation = conversation
        return await self.run(enriched_conversation, context)

    def get_required_outputs(self) -> List[str]:
        return self.required_outputs

    def build_chat_messages(
        self,
        system_prompt: str,
        conversation: str,
        context: Dict[str, Any] = None,
    ) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": system_prompt}]

        turns = self._parse_conversation_turns(conversation)
        if turns:
            messages.extend(turns)
        else:
            messages.append({"role": "user", "content": conversation})

        if context and context.get("artifact_context"):
            artifact_text = context["artifact_context"]
            if artifact_text and artifact_text.strip():
                messages.append({
                    "role": "system",
                    "content": f"【项目已有信息】\n{artifact_text}"
                })

        return messages

    def _parse_conversation_turns(self, text: str) -> List[Dict[str, str]]:
        if not text or not text.strip():
            return []

        turns = []

        if "【对话历史】" in text:
            history_lines = []
            current_msg_lines = []
            section = ""

            for line in text.split("\n"):
                stripped = line.strip()
                if stripped == "【对话历史】":
                    section = "history"
                    continue
                elif stripped == "【当前用户消息】":
                    section = "current"
                    continue
                elif stripped.startswith("【") and stripped.endswith("】"):
                    section = ""
                    continue

                if section == "history":
                    history_lines.append(line)
                elif section == "current":
                    current_msg_lines.append(line)

            for line in history_lines:
                s = line.strip()
                if not s:
                    continue
                if s.startswith("用户: ") or s.startswith("用户："):
                    turns.append({"role": "user", "content": s[3:].strip()})
                elif s.startswith("助手: ") or s.startswith("助手："):
                    turns.append({"role": "assistant", "content": s[3:].strip()})

            current_msg = "\n".join(current_msg_lines).strip()
            if current_msg:
                if not (turns and turns[-1]["role"] == "user" and turns[-1]["content"] == current_msg):
                    turns.append({"role": "user", "content": current_msg})

        elif "用户:" in text or "助手:" in text or "user:" in text.lower() or "assistant:" in text.lower():
            for line in text.strip().split("\n"):
                s = line.strip()
                if not s:
                    continue
                if s.startswith("用户: ") or s.startswith("用户："):
                    turns.append({"role": "user", "content": s[3:].strip()})
                elif s.startswith("助手: ") or s.startswith("助手："):
                    turns.append({"role": "assistant", "content": s[3:].strip()})
                elif s.startswith("user: ") or s.startswith("User: "):
                    turns.append({"role": "user", "content": s[6:].strip()})
                elif s.startswith("assistant: ") or s.startswith("Assistant: "):
                    turns.append({"role": "assistant", "content": s[11:].strip()})

        return turns


class SkillRegistry:
    _skills: Dict[str, Skill] = {}
    _lock = threading.Lock()

    @classmethod
    def register(cls, skill: Skill):
        with cls._lock:
            if skill.name in cls._skills:
                logger.warning(f"Skill '{skill.name}' already registered, skipping duplicate")
                return
            cls._skills[skill.name] = skill

    @classmethod
    def get_skill(cls, name: str) -> Optional[Skill]:
        with cls._lock:
            return cls._skills.get(name)

    @classmethod
    def list_skills(cls) -> List[Dict[str, Any]]:
        with cls._lock:
            return [
                {
                    "name": s.name,
                    "description": s.description,
                    "trigger": s.trigger,
                    "required_outputs": s.get_required_outputs(),
                }
                for s in cls._skills.values()
            ]

    @classmethod
    def detect_skill(cls, message: str) -> Optional[str]:
        message_lower = message.lower()

        negation_prefixes = ("不", "不要", "不用", "无需", "别", "no ", "don't", "not ")

        with cls._lock:
            candidates = []
            for name, skill in cls._skills.items():
                if not skill.trigger:
                    continue

                trigger_lower = skill.trigger.lower()
                if trigger_lower not in message_lower:
                    continue

                skip = False
                for prefix in negation_prefixes:
                    idx = message_lower.find(trigger_lower)
                    while idx >= 0:
                        prefix_start = max(0, idx - len(prefix))
                        if message_lower[prefix_start:idx] == prefix:
                            skip = True
                            break
                        idx = message_lower.find(trigger_lower, idx + 1)
                    if skip:
                        break
                if skip:
                    continue

                trigger_words = trigger_lower.split()
                message_words = message_lower.split()

                if len(trigger_words) > 1:
                    word_matches = sum(1 for w in trigger_words if w in message_lower)
                    word_ratio = word_matches / len(trigger_words)
                    confidence = word_ratio * 0.8
                else:
                    for mw in message_words:
                        if trigger_lower in mw:
                            confidence = min(1.0, len(trigger_lower) / max(len(mw), 1))
                            break
                    else:
                        confidence = 0.3

                if confidence >= 0.5:
                    candidates.append((name, confidence, len(skill.trigger)))

        if not candidates:
            return None

        candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)

        if len(candidates) > 1:
            top_conf = candidates[0][1]
            second_conf = candidates[1][1]
            if top_conf - second_conf < 0.1:
                logger.info(
                    f"Skill detection conflict: {candidates[0][0]}({top_conf:.2f}) "
                    f"vs {candidates[1][0]}({second_conf:.2f}), "
                    f"selecting longer trigger"
                )
                candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)

        return candidates[0][0]

    @classmethod
    def get_all_skills(cls) -> Dict[str, Skill]:
        with cls._lock:
            return dict(cls._skills)
