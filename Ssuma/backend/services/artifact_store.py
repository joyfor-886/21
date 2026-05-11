"""上下文物件(Artifact)系统 — 阶段间的结构化传递

核心思想：每个阶段产出不仅是文本回复，还有一个结构化的上下文物件，
传递给下一阶段。参考 context-engineering 社区的上下文物件模式。

借鉴来源:
- context-fundamentals: 理解上下文的解剖
- context-compression: 长会话压缩策略
- NeoLabHQ/reflexion: 自精炼循环（输出→反思→纠正→再输出）
- Dean Peters/opportunity-solution-tree: 假设驱动发现流程
"""
from typing import Dict, Any, List, Optional
import logging
from core.state_repository import StateRepository
from domain.results import PhaseArtifact

logger = logging.getLogger('Ssuma.Artifact')

STATE_SERVICE_NAME = "artifact"


class ArtifactStore:
    """跨阶段的上下文物件存储

    使用项目ID作为key，存储该项目所有阶段的产出。
    设计参考:
    - memory-systems: 短期/长期/基于图的内存架构
    - context-optimization: compaction + masking + caching
    """

    _artifacts: Dict[str, List[PhaseArtifact]] = {}

    @classmethod
    def _ensure_loaded(cls, project_id: str):
        """确保项目数据已从 StateRepository 加载"""
        if project_id not in cls._artifacts:
            data = StateRepository.load(STATE_SERVICE_NAME, project_id)
            if data is not None:
                cls._artifacts[project_id] = [PhaseArtifact.from_dict(a) for a in data]
            else:
                cls._artifacts[project_id] = []

    @classmethod
    def _save_to_repo(cls, project_id: str):
        """保存到 StateRepository"""
        artifacts = cls._artifacts.get(project_id, [])
        StateRepository.save(
            STATE_SERVICE_NAME,
            project_id,
            [a.to_dict() for a in artifacts]
        )

    @classmethod
    def add(cls, project_id: str, artifact: PhaseArtifact):
        cls._ensure_loaded(project_id)
        if project_id not in cls._artifacts:
            cls._artifacts[project_id] = []
        cls._artifacts[project_id].append(artifact)
        cls._save_to_repo(project_id)
        logger.info(f"Artifact added: project={project_id}, phase={artifact.phase}")

    @classmethod
    def get_all(cls, project_id: str) -> List[PhaseArtifact]:
        cls._ensure_loaded(project_id)
        return cls._artifacts.get(project_id, [])

    @classmethod
    def get_latest(cls, project_id: str) -> Optional[PhaseArtifact]:
        cls._ensure_loaded(project_id)
        artifacts = cls._artifacts.get(project_id, [])
        return artifacts[-1] if artifacts else None

    @classmethod
    def get_by_phase(cls, project_id: str, phase: str) -> Optional[PhaseArtifact]:
        """获取指定阶段的最新物件"""
        cls._ensure_loaded(project_id)
        artifacts = cls._artifacts.get(project_id, [])
        for artifact in reversed(artifacts):
            if artifact.phase == phase:
                return artifact
        return None

    @classmethod
    def build_context_for_phase(cls, project_id: str, target_phase: str) -> str:
        """为指定阶段构建前置上下文

        参考 context-compression 策略：
        - 不传递全部原始输出（太长）
        - 只传递结构化的决策、约束、洞察
        - 按时间顺序排列，最近的最详细
        """
        artifacts = cls.get_all(project_id)
        if not artifacts:
            return ""

        parts = ["## 前序阶段的讨论成果\n"]

        for artifact in artifacts:
            # 跳过与目标阶段相同的阶段（避免循环引用）
            if artifact.phase == target_phase:
                continue

            parts.append(f"### {artifact.phase} 阶段")
            parts.append(artifact.to_compact_context())
            parts.append("")

        return "\n".join(parts)

    @classmethod
    def clear(cls, project_id: str):
        """清除项目的所有物件"""
        if project_id in cls._artifacts:
            del cls._artifacts[project_id]
        StateRepository.delete(STATE_SERVICE_NAME, project_id)

    @classmethod
    def get_all_decisions(cls, project_id: str) -> List[str]:
        """获取项目所有阶段的关键决策（用于一致性检查）"""
        decisions = []
        for artifact in cls.get_all(project_id):
            decisions.extend(artifact.decisions)
        return decisions

    @classmethod
    def get_all_open_questions(cls, project_id: str) -> List[str]:
        """获取所有未解决的问题"""
        questions = []
        for artifact in cls.get_all(project_id):
            questions.extend(artifact.open_questions)
        return questions


async def extract_artifact_from_response(
    phase: str,
    response: str,
    conversation: str = "",
    completion_result=None,
) -> PhaseArtifact:
    from services.artifact_extractor import ArtifactExtractor
    return await ArtifactExtractor.extract(phase, response, conversation, completion_result)
