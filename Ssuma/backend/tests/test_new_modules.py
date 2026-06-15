"""Ssuma 新模块综合测试

覆盖模块：
  - FlowGraph (services/flow/graph.py)
  - ProjectMemoryCard & ProjectMemoryStore (core/project_memory.py)
  - Reflexion (services/reflexion.py)
  - MCP Client (core/mcp_client.py)
  - HITL (core/hitl.py)
  - Middlewares (services/flow/middlewares.py)
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from domain.enums import (
    FlowPhase,
    UserIntent,
    ClarityLevel,
    CHANNEL_PHASES,
)
from domain.results import IntentAnalysisResult


# ============================================================
#  FlowGraph 测试
# ============================================================


class TestFlowGraph:
    """FlowGraph 声明式阶段路由图测试"""

    def setup_method(self):
        from services.flow.graph import FlowGraph
        self.graph = FlowGraph()

    # --- DEFAULT_PROGRESSION ---

    def test_default_progression_qishu_to_caiheng(self):
        """启枢默认前进到裁衡"""
        from services.flow.graph import FlowGraph
        assert FlowGraph.DEFAULT_PROGRESSION[FlowPhase.QISHU] == FlowPhase.CAIHENG

    def test_default_progression_tanyin_to_caiheng(self):
        """探隐默认前进到裁衡"""
        from services.flow.graph import FlowGraph
        assert FlowGraph.DEFAULT_PROGRESSION[FlowPhase.TANYIN] == FlowPhase.CAIHENG

    def test_default_progression_caiheng_to_zhenwei(self):
        """裁衡默认前进到甄微"""
        from services.flow.graph import FlowGraph
        assert FlowGraph.DEFAULT_PROGRESSION[FlowPhase.CAIHENG] == FlowPhase.ZHENWEI

    def test_default_progression_zhenwei_to_ceshu(self):
        """甄微默认前进到策书"""
        from services.flow.graph import FlowGraph
        assert FlowGraph.DEFAULT_PROGRESSION[FlowPhase.ZHENWEI] == FlowPhase.CESHU

    def test_default_progression_ceshu_to_ningmo(self):
        """策书默认前进到凝墨"""
        from services.flow.graph import FlowGraph
        assert FlowGraph.DEFAULT_PROGRESSION[FlowPhase.CESHU] == FlowPhase.NINGMO

    def test_default_progression_ningmo_to_completed(self):
        """凝墨默认前进到完成"""
        from services.flow.graph import FlowGraph
        assert FlowGraph.DEFAULT_PROGRESSION[FlowPhase.NINGMO] == FlowPhase.COMPLETED

    def test_default_progression_powang_to_jianyan(self):
        """破妄默认前进到渐衍"""
        from services.flow.graph import FlowGraph
        assert FlowGraph.DEFAULT_PROGRESSION[FlowPhase.POWANG] == FlowPhase.JIANYAN

    def test_default_progression_jianyan_to_completed(self):
        """渐衍默认前进到完成"""
        from services.flow.graph import FlowGraph
        assert FlowGraph.DEFAULT_PROGRESSION[FlowPhase.JIANYAN] == FlowPhase.COMPLETED

    def test_default_progression_completed_stays(self):
        """完成阶段保持不变"""
        from services.flow.graph import FlowGraph
        assert FlowGraph.DEFAULT_PROGRESSION[FlowPhase.COMPLETED] == FlowPhase.COMPLETED

    # --- route() 方法 ---

    def test_route_force_workflow(self):
        """强制工作流时直接跳转到目标阶段"""
        from services.flow.graph import TransitionReason
        intent_result = IntentAnalysisResult(
            intent=UserIntent.CHAT, clarity=ClarityLevel.CLEAR, confidence=0.9
        )
        next_phase, reason = self.graph.route(
            FlowPhase.QISHU, intent_result, "standard", {}, force_workflow="ceshu"
        )
        assert next_phase == FlowPhase.CESHU
        assert reason == TransitionReason.FORCE_WORKFLOW

    def test_route_force_workflow_chat_maps_to_qishu(self):
        """强制工作流 chat 映射到启枢"""
        from services.flow.graph import TransitionReason
        intent_result = IntentAnalysisResult(
            intent=UserIntent.CHAT, clarity=ClarityLevel.CLEAR, confidence=0.9
        )
        next_phase, reason = self.graph.route(
            FlowPhase.INTENT_DETECTION, intent_result, "standard", {}, force_workflow="chat"
        )
        assert next_phase == FlowPhase.QISHU
        assert reason == TransitionReason.FORCE_WORKFLOW

    def test_route_intent_detection_direct_intent(self):
        """意图检测阶段：直接意图映射到目标阶段"""
        from services.flow.graph import TransitionReason
        intent_result = IntentAnalysisResult(
            intent=UserIntent.CAIHENG, clarity=ClarityLevel.CLEAR, confidence=0.9
        )
        next_phase, reason = self.graph.route(
            FlowPhase.INTENT_DETECTION, intent_result, "standard", {}
        )
        assert next_phase == FlowPhase.CAIHENG
        assert reason == TransitionReason.INTENT_DIRECT

    def test_route_intent_detection_fuzzy_goes_to_tanyin(self):
        """意图检测阶段：模糊需求路由到探隐"""
        from services.flow.graph import TransitionReason
        intent_result = IntentAnalysisResult(
            intent=UserIntent.CHAT, clarity=ClarityLevel.FUZZY, confidence=0.5
        )
        next_phase, reason = self.graph.route(
            FlowPhase.INTENT_DETECTION, intent_result, "standard", {}
        )
        assert next_phase == FlowPhase.TANYIN
        assert reason == TransitionReason.INTENT_DETECTION

    def test_route_intent_detection_clear_high_confidence_goes_to_qishu(self):
        """意图检测阶段：清晰高置信路由到启枢"""
        from services.flow.graph import TransitionReason
        intent_result = IntentAnalysisResult(
            intent=UserIntent.CHAT, clarity=ClarityLevel.CLEAR, confidence=0.9
        )
        next_phase, reason = self.graph.route(
            FlowPhase.INTENT_DETECTION, intent_result, "standard", {}
        )
        assert next_phase == FlowPhase.QISHU
        assert reason == TransitionReason.INTENT_DETECTION

    def test_route_intent_detection_default_goes_to_channel_first(self):
        """意图检测阶段：默认路由到通道首阶段"""
        from services.flow.graph import TransitionReason
        intent_result = IntentAnalysisResult(
            intent=UserIntent.CHAT, clarity=ClarityLevel.PARTIAL, confidence=0.6
        )
        next_phase, reason = self.graph.route(
            FlowPhase.INTENT_DETECTION, intent_result, "standard", {}
        )
        assert next_phase == FlowPhase.QISHU
        assert reason == TransitionReason.INTENT_DETECTION

    def test_route_stay_when_incomplete(self):
        """当前阶段未完成时停留"""
        from services.flow.graph import TransitionReason
        intent_result = IntentAnalysisResult(
            intent=UserIntent.QISHU, clarity=ClarityLevel.CLEAR, confidence=0.9
        )
        next_phase, reason = self.graph.route(
            FlowPhase.QISHU, intent_result, "standard", {"qishu": 0.3}
        )
        assert next_phase == FlowPhase.QISHU
        assert reason == TransitionReason.STAY

    def test_route_back_when_intent_earlier_phase(self):
        """当前阶段未完成且意图指向更早阶段时回退"""
        from services.flow.graph import TransitionReason
        intent_result = IntentAnalysisResult(
            intent=UserIntent.QISHU, clarity=ClarityLevel.CLEAR, confidence=0.9
        )
        next_phase, reason = self.graph.route(
            FlowPhase.CAIHENG, intent_result, "standard", {"caiheng": 0.3}
        )
        assert next_phase == FlowPhase.QISHU
        assert reason == TransitionReason.INTENT_BACK

    def test_route_advance_when_complete(self):
        """当前阶段完成时前进"""
        from services.flow.graph import TransitionReason
        # 使用 TANYIN 意图，在 standard 通道中 QISHU(0) -> TANYIN(1)
        # target_idx=1 <= current_idx(0)+1=1，意图跳转成立
        intent_result = IntentAnalysisResult(
            intent=UserIntent.TANYIN, clarity=ClarityLevel.CLEAR, confidence=0.9
        )
        next_phase, reason = self.graph.route(
            FlowPhase.QISHU, intent_result, "standard", {"qishu": 0.8}
        )
        assert next_phase == FlowPhase.TANYIN
        assert reason == TransitionReason.INTENT_DIRECT

    # --- _route_from_intent_detection ---

    def test_route_from_intent_detection_qishu_intent(self):
        """意图检测阶段：启枢意图直接映射"""
        from services.flow.graph import TransitionReason
        intent_result = IntentAnalysisResult(
            intent=UserIntent.QISHU, clarity=ClarityLevel.CLEAR, confidence=0.9
        )
        next_phase, reason = self.graph._route_from_intent_detection(intent_result, "standard")
        assert next_phase == FlowPhase.QISHU
        assert reason == TransitionReason.INTENT_DIRECT

    def test_route_from_intent_detection_capability_check_blocks(self):
        """意图检测阶段：能力检查器阻止目标阶段"""
        from services.flow.graph import TransitionReason
        self.graph.set_capability_checker(lambda phase: phase != FlowPhase.CESHU)
        intent_result = IntentAnalysisResult(
            intent=UserIntent.CESHU, clarity=ClarityLevel.CLEAR, confidence=0.9
        )
        # CESHU 被阻止，应走其他分支
        next_phase, reason = self.graph._route_from_intent_detection(intent_result, "standard")
        assert next_phase != FlowPhase.CESHU

    def test_route_from_intent_detection_fast_channel(self):
        """意图检测阶段：fast 通道默认首阶段为启枢"""
        from services.flow.graph import TransitionReason
        intent_result = IntentAnalysisResult(
            intent=UserIntent.CHAT, clarity=ClarityLevel.PARTIAL, confidence=0.6
        )
        next_phase, reason = self.graph._route_from_intent_detection(intent_result, "fast")
        assert next_phase == FlowPhase.QISHU

    # --- _route_advance ---

    def test_route_advance_channel_next(self):
        """通道顺序前进（无意图跳转时按通道顺序）"""
        from services.flow.graph import TransitionReason
        # UNKNOWN 意图映射到 QISHU，在 standard 通道中 QISHU(0) -> QISHU(0)
        # target_idx(0) <= current_idx(0)+1=1，意图跳转成立但目标是自身
        # 实际上会走意图跳转分支返回 QISHU 自身
        # 改用 TANYIN 阶段完成，意图为 CHAT(映射QISHU)，此时意图回退不满足
        # 走通道顺序前进
        intent_result = IntentAnalysisResult(
            intent=UserIntent.CESHU, clarity=ClarityLevel.CLEAR, confidence=0.9
        )
        # TANYIN 完成，意图 CESHU 在 standard 通道中 index=3
        # current_idx(TANYIN)=1, target_idx(CESHU)=3, 3 > 1+1=2，不满足意图跳转
        # 走通道顺序前进：TANYIN -> CAIHENG
        next_phase, reason = self.graph.route(
            FlowPhase.TANYIN, intent_result, "standard", {"tanyin": 0.8}
        )
        assert next_phase == FlowPhase.CAIHENG
        assert reason == TransitionReason.CHANNEL_NEXT

    def test_route_advance_intent_direct_forward(self):
        """意图跳转前进（只允许前进1步）"""
        from services.flow.graph import TransitionReason
        intent_result = IntentAnalysisResult(
            intent=UserIntent.CAIHENG, clarity=ClarityLevel.CLEAR, confidence=0.9
        )
        next_phase, reason = self.graph.route(
            FlowPhase.QISHU, intent_result, "standard", {"qishu": 0.8}
        )
        # QISHU -> CAIHENG 在 standard 通道中间隔 TANYIN，不允许跳2步
        # 应该走 CHANNEL_NEXT
        assert next_phase == FlowPhase.TANYIN

    def test_route_advance_default_progression_when_not_in_channel(self):
        """不在通道中时使用默认前进映射"""
        from services.flow.graph import TransitionReason
        intent_result = IntentAnalysisResult(
            intent=UserIntent.CHAT, clarity=ClarityLevel.CLEAR, confidence=0.9
        )
        # POWANG 不在 standard 通道中
        next_phase, reason = self.graph.route(
            FlowPhase.POWANG, intent_result, "standard", {"powang": 0.8}
        )
        assert next_phase == FlowPhase.JIANYAN
        assert reason == TransitionReason.COMPLETION_ADVANCE

    def test_route_advance_capability_skip(self):
        """能力检查器跳过不支持阶段"""
        from services.flow.graph import TransitionReason
        # standard: QISHU(0) -> TANYIN(1) -> CAIHENG(2) -> CESHU(3) -> NINGMO(4)
        # 从 TANYIN 完成，意图 CESHU(index=3) 距离 TANYIN(index=1) 超过1步
        # 走通道顺序前进，跳过被阻止的 CAIHENG，到 CESHU
        self.graph.set_capability_checker(lambda phase: phase != FlowPhase.CAIHENG)
        intent_result = IntentAnalysisResult(
            intent=UserIntent.CESHU, clarity=ClarityLevel.CLEAR, confidence=0.9
        )
        next_phase, reason = self.graph.route(
            FlowPhase.TANYIN, intent_result, "standard", {"tanyin": 0.8}
        )
        # TANYIN(1) -> 下一个是 CAIHENG(2) 但被阻止 -> CESHU(3)
        assert next_phase == FlowPhase.CESHU
        assert reason == TransitionReason.CHANNEL_NEXT

    # --- 辅助方法 ---

    def test_workflow_to_phase(self):
        """workflow_to_phase 映射正确"""
        assert self.graph.workflow_to_phase("qishu") == FlowPhase.QISHU
        assert self.graph.workflow_to_phase("ningmo") == FlowPhase.NINGMO
        assert self.graph.workflow_to_phase("unknown") == FlowPhase.QISHU

    def test_intent_to_phase(self):
        """intent_to_phase 映射正确"""
        assert self.graph.intent_to_phase(UserIntent.QISHU) == FlowPhase.QISHU
        assert self.graph.intent_to_phase(UserIntent.CHAT) == FlowPhase.QISHU
        assert self.graph.intent_to_phase(UserIntent.UNKNOWN) == FlowPhase.QISHU

    def test_phase_index(self):
        """phase_index 返回正确的顺序索引"""
        assert self.graph.phase_index(FlowPhase.INTENT_DETECTION) == 0
        assert self.graph.phase_index(FlowPhase.QISHU) == 1
        assert self.graph.phase_index(FlowPhase.COMPLETED) == 9

    def test_intent_for_phase(self):
        """intent_for_phase 反向映射"""
        assert self.graph.intent_for_phase(FlowPhase.QISHU) == UserIntent.QISHU
        assert self.graph.intent_for_phase(FlowPhase.NINGMO) == UserIntent.NINGMO
        assert self.graph.intent_for_phase(FlowPhase.COMPLETED) == UserIntent.CHAT

    def test_get_suggested_next_phase(self):
        """获取建议的下一阶段"""
        # standard: QISHU -> TANYIN -> CAIHENG -> CESHU -> NINGMO
        assert self.graph.get_suggested_next_phase(FlowPhase.QISHU, "standard") == FlowPhase.TANYIN
        # fast: QISHU -> CAIHENG -> NINGMO
        assert self.graph.get_suggested_next_phase(FlowPhase.QISHU, "fast") == FlowPhase.CAIHENG


# ============================================================
#  ProjectMemoryCard 测试
# ============================================================


class TestProjectMemoryCard:
    """ProjectMemoryCard 项目记忆卡测试"""

    def test_creation_defaults(self):
        """默认创建空白记忆卡"""
        from core.project_memory import ProjectMemoryCard
        card = ProjectMemoryCard(project_id="test-project")
        assert card.project_id == "test-project"
        assert card.project_name == ""
        assert card.requirement_summary == ""
        assert card.core_features == []
        assert card.tech_decisions == []
        assert card.phases_completed == []
        assert card.channel == "standard"
        assert card.total_turns == 0

    def test_creation_with_data(self):
        """带数据创建记忆卡"""
        from core.project_memory import ProjectMemoryCard
        card = ProjectMemoryCard(
            project_id="proj-1",
            project_name="测试项目",
            requirement_summary="构建一个任务管理工具",
            core_features=["任务创建", "任务分配"],
            tech_stack={"frontend": "React", "backend": "FastAPI"},
        )
        assert card.project_name == "测试项目"
        assert card.requirement_summary == "构建一个任务管理工具"
        assert len(card.core_features) == 2
        assert card.tech_stack["frontend"] == "React"

    def test_update_from_artifact_tanyin(self):
        """从探隐阶段产出更新记忆卡"""
        from core.project_memory import ProjectMemoryCard
        card = ProjectMemoryCard(project_id="proj-1")
        card.update_from_artifact("tanyin", {
            "summary": "用户需要一个在线协作白板",
            "decisions": ["实时协作", "画布无限延伸"],
            "open_questions": ["是否需要离线支持？"],
        })
        assert card.requirement_summary == "用户需要一个在线协作白板"
        assert "实时协作" in card.core_features
        assert "是否需要离线支持？" in card.open_questions
        assert "tanyin" in card.phases_completed

    def test_update_from_artifact_caiheng(self):
        """从裁衡阶段产出更新记忆卡"""
        from core.project_memory import ProjectMemoryCard
        card = ProjectMemoryCard(project_id="proj-1")
        card.update_from_artifact("caiheng", {
            "decisions": ["使用 WebSocket 实现实时同步"],
            "commitments": [{"category": "性能", "content": "延迟 < 100ms"}],
        })
        assert len(card.tech_decisions) == 1
        assert card.tech_decisions[0]["decision"] == "使用 WebSocket 实现实时同步"
        assert len(card.commitments) == 1
        assert "caiheng" in card.phases_completed

    def test_update_from_artifact_zhenwei(self):
        """从甄微阶段产出更新记忆卡"""
        from core.project_memory import ProjectMemoryCard
        card = ProjectMemoryCard(project_id="proj-1")
        card.update_from_artifact("zhenwei", {
            "key_insights": ["微服务架构更适合扩展"],
            "decisions": ["采用事件驱动架构"],
        })
        assert "微服务架构更适合扩展" in card.architecture_choices
        # 甄微阶段的 decisions 追加到 tech_decisions
        assert any(d["decision"] == "采用事件驱动架构" for d in card.tech_decisions)
        assert "zhenwei" in card.phases_completed

    def test_update_from_artifact_ceshu(self):
        """从策书阶段产出更新记忆卡"""
        from core.project_memory import ProjectMemoryCard
        card = ProjectMemoryCard(project_id="proj-1")
        card.update_from_artifact("ceshu", {
            "commitments": [
                {"category": "安全", "content": "所有 API 必须鉴权"},
                {"category": "质量", "content": "测试覆盖率 > 80%"},
            ],
        })
        assert "所有 API 必须鉴权" in card.constraints
        assert "测试覆盖率 > 80%" in card.constraints
        assert "ceshu" in card.phases_completed

    def test_update_from_artifact_no_duplicate_phase(self):
        """同一阶段不重复添加到 phases_completed"""
        from core.project_memory import ProjectMemoryCard
        card = ProjectMemoryCard(project_id="proj-1")
        card.update_from_artifact("tanyin", {"summary": "第一次"})
        card.update_from_artifact("tanyin", {"summary": "第二次更新"})
        assert card.phases_completed.count("tanyin") == 1

    def test_update_from_artifact_completion_score(self):
        """更新完成度分数"""
        from core.project_memory import ProjectMemoryCard
        card = ProjectMemoryCard(project_id="proj-1")
        card.update_from_artifact("tanyin", {
            "summary": "测试",
            "completion_score": 0.85,
        })
        assert card.completion_scores["tanyin"] == 0.85

    def test_to_context_string_basic(self):
        """to_context_string 基本输出格式"""
        from core.project_memory import ProjectMemoryCard
        card = ProjectMemoryCard(
            project_id="proj-1",
            project_name="测试项目",
            requirement_summary="构建一个任务管理工具",
        )
        context = card.to_context_string()
        assert "## 项目记忆卡: 测试项目" in context
        assert "### 需求摘要" in context
        assert "构建一个任务管理工具" in context

    def test_to_context_string_with_tech_stack(self):
        """to_context_string 包含技术栈信息"""
        from core.project_memory import ProjectMemoryCard
        card = ProjectMemoryCard(
            project_id="proj-1",
            project_name="项目A",
            tech_stack={"frontend": "React", "backend": "FastAPI"},
        )
        context = card.to_context_string()
        assert "### 技术栈" in context
        assert "frontend: React" in context
        assert "backend: FastAPI" in context

    def test_to_context_string_with_phases_completed(self):
        """to_context_string 包含已完成阶段"""
        from core.project_memory import ProjectMemoryCard
        card = ProjectMemoryCard(project_id="proj-1")
        card.update_from_artifact("tanyin", {"summary": "需求"})
        card.update_from_artifact("caiheng", {"decisions": ["选型A"]})
        context = card.to_context_string()
        assert "### 已完成阶段" in context
        assert "tanyin" in context
        assert "caiheng" in context

    def test_to_context_string_empty_card(self):
        """空白记忆卡只输出标题"""
        from core.project_memory import ProjectMemoryCard
        card = ProjectMemoryCard(project_id="proj-1")
        context = card.to_context_string()
        assert "## 项目记忆卡: proj-1" in context

    def test_add_session_summary(self):
        """添加会话摘要"""
        from core.project_memory import ProjectMemoryCard
        card = ProjectMemoryCard(project_id="proj-1")
        card.add_session_summary("sess-1", "讨论了核心功能需求")
        assert len(card.session_summaries) == 1
        assert card.session_summaries[0]["session_id"] == "sess-1"
        assert card.session_summaries[0]["summary"] == "讨论了核心功能需求"

    def test_add_session_summary_max_10(self):
        """会话摘要最多保留10条"""
        from core.project_memory import ProjectMemoryCard
        card = ProjectMemoryCard(project_id="proj-1")
        for i in range(15):
            card.add_session_summary(f"sess-{i}", f"摘要 {i}")
        assert len(card.session_summaries) == 10
        assert card.session_summaries[0]["session_id"] == "sess-5"


class TestProjectMemoryStore:
    """ProjectMemoryStore 项目记忆卡存储测试"""

    def test_get_with_mock_db(self):
        """使用 mock DB 获取记忆卡"""
        from core.project_memory import ProjectMemoryCard, ProjectMemoryStore
        mock_db = MagicMock()
        card_data = ProjectMemoryCard(
            project_id="proj-1", project_name="已有项目"
        ).model_dump_json()
        mock_db.fetchone.return_value = (card_data,)
        store = ProjectMemoryStore(db=mock_db)
        result = store.get("proj-1")
        assert result.project_id == "proj-1"
        assert result.project_name == "已有项目"

    def test_get_creates_empty_card_when_not_found(self):
        """获取不存在的项目时创建空白记忆卡"""
        from core.project_memory import ProjectMemoryStore
        mock_db = MagicMock()
        mock_db.fetchone.return_value = None
        store = ProjectMemoryStore(db=mock_db)
        result = store.get("new-proj")
        assert result.project_id == "new-proj"
        assert result.project_name == ""

    def test_get_uses_cache(self):
        """第二次获取从缓存读取"""
        from core.project_memory import ProjectMemoryCard, ProjectMemoryStore
        mock_db = MagicMock()
        mock_db.fetchone.return_value = None
        store = ProjectMemoryStore(db=mock_db)
        card = store.get("proj-1")
        card.project_name = "缓存测试"
        # 第二次获取应从缓存读取
        result = store.get("proj-1")
        assert result.project_name == "缓存测试"
        # fetchvalue 只被调用一次
        assert mock_db.fetchone.call_count == 1

    def test_save_new_card(self):
        """保存新记忆卡（INSERT）"""
        from core.project_memory import ProjectMemoryCard, ProjectMemoryStore
        mock_db = MagicMock()
        mock_db.fetchone.return_value = None  # 不存在
        store = ProjectMemoryStore(db=mock_db)
        card = ProjectMemoryCard(project_id="proj-1", project_name="新项目")
        store.save(card)
        # 应该执行 INSERT
        mock_db.execute.assert_called()
        call_args = mock_db.execute.call_args[0][0]
        assert "INSERT" in call_args

    def test_save_existing_card(self):
        """保存已有记忆卡（UPDATE）"""
        from core.project_memory import ProjectMemoryCard, ProjectMemoryStore
        mock_db = MagicMock()
        mock_db.fetchone.return_value = ("existing",)  # 已存在
        store = ProjectMemoryStore(db=mock_db)
        card = ProjectMemoryCard(project_id="proj-1", project_name="更新项目")
        store.save(card)
        call_args = mock_db.execute.call_args[0][0]
        assert "UPDATE" in call_args

    def test_save_updates_cache(self):
        """保存后缓存同步更新"""
        from core.project_memory import ProjectMemoryCard, ProjectMemoryStore
        mock_db = MagicMock()
        mock_db.fetchone.return_value = None
        store = ProjectMemoryStore(db=mock_db)
        card = ProjectMemoryCard(project_id="proj-1", project_name="缓存项目")
        store.save(card)
        # 从缓存获取应返回保存的卡片
        result = store.get("proj-1")
        assert result.project_name == "缓存项目"


# ============================================================
#  Reflexion 测试
# ============================================================


class TestReflexion:
    """Reflexion 反思循环测试"""

    @pytest.mark.asyncio
    async def test_reflexion_loop_no_llm_returns_original(self):
        """无 LLM 提供者且工厂不可用时返回原始输出"""
        from services.reflexion import reflexion_loop
        # LLMFactory 是延迟导入的，patch core.llm_factory 模块
        with patch("core.llm_factory.LLMFactory.get_provider", side_effect=Exception("no factory")):
            result = await reflexion_loop(
                initial_output="原始输出",
                phase="ningmo",
                conversation="对话上下文",
                llm_provider=None,
            )
        assert result.final_output == "原始输出"
        assert result.improved is False
        assert result.rounds == 0

    @pytest.mark.asyncio
    async def test_reflexion_loop_complete_output(self):
        """输出完整时反思循环提前结束"""
        from services.reflexion import reflexion_loop
        mock_llm = AsyncMock()
        # _reflect 返回 is_complete=True
        mock_llm.chat.return_value = '{"is_complete": true, "reasoning": "", "missing_points": []}'
        result = await reflexion_loop(
            initial_output="完整的输出",
            phase="ningmo",
            conversation="对话",
            llm_provider=mock_llm,
            max_rounds=2,
        )
        assert result.final_output == "完整的输出"
        assert result.improved is False
        assert result.rounds == 0

    @pytest.mark.asyncio
    async def test_reflexion_loop_finds_improvement(self):
        """反思循环发现改进并纠正"""
        from services.reflexion import reflexion_loop
        mock_llm = AsyncMock()
        # 第一轮：反思发现遗漏
        # 第二轮：纠正后再次反思，发现完整
        mock_llm.chat.side_effect = [
            '{"is_complete": false, "reasoning": "缺少风险分析", "missing_points": ["风险分析"]}',
            "改进后的输出，包含风险分析",
            '{"is_complete": true, "reasoning": "", "missing_points": []}',
        ]
        result = await reflexion_loop(
            initial_output="原始输出",
            phase="ningmo",
            conversation="对话",
            llm_provider=mock_llm,
            max_rounds=2,
        )
        assert result.improved is True
        assert result.final_output == "改进后的输出，包含风险分析"
        assert result.rounds == 1

    @pytest.mark.asyncio
    async def test_reflexion_loop_correction_same_as_original(self):
        """纠正结果与原始输出相同时停止循环"""
        from services.reflexion import reflexion_loop
        mock_llm = AsyncMock()
        mock_llm.chat.side_effect = [
            '{"is_complete": false, "reasoning": "可以改进", "missing_points": ["细节"]}',
            "原始输出",  # 纠正结果与原始相同
        ]
        result = await reflexion_loop(
            initial_output="原始输出",
            phase="ningmo",
            conversation="对话",
            llm_provider=mock_llm,
            max_rounds=2,
        )
        assert result.improved is False

    @pytest.mark.asyncio
    async def test_reflexion_result_to_dict(self):
        """ReflexionResult.to_dict() 格式正确"""
        from services.reflexion import ReflexionResult
        result = ReflexionResult(
            final_output="最终输出",
            initial_output="初始输出",
            reflections=["遗漏1"],
            corrections=["纠正1"],
            rounds=1,
            improved=True,
        )
        d = result.to_dict()
        assert d["final_output"] == "最终输出"
        assert d["rounds"] == 1
        assert d["improved"] is True
        assert d["reflections_count"] == 1
        assert d["corrections_count"] == 1

    @pytest.mark.asyncio
    async def test_reflect_returns_none_on_exception(self):
        """_reflect 异常时返回 None"""
        from services.reflexion import _reflect
        mock_llm = AsyncMock()
        mock_llm.chat.side_effect = Exception("LLM error")
        result = await _reflect("输出", "ningmo", "对话", mock_llm)
        assert result is None

    @pytest.mark.asyncio
    async def test_correct_returns_none_on_exception(self):
        """_correct 异常时返回 None"""
        from services.reflexion import _correct
        mock_llm = AsyncMock()
        mock_llm.chat.side_effect = Exception("LLM error")
        result = await _correct("输出", {"missing_points": ["遗漏"], "reasoning": "不完整"}, "ningmo", mock_llm)
        assert result is None

    @pytest.mark.asyncio
    async def test_correct_returns_none_when_no_missing(self):
        """_correct 无遗漏点时返回 None"""
        from services.reflexion import _correct
        mock_llm = AsyncMock()
        result = await _correct("输出", {"missing_points": [], "reasoning": ""}, "ningmo", mock_llm)
        assert result is None

    @pytest.mark.asyncio
    async def test_reflect_with_phase_dimensions(self):
        """_reflect 包含阶段维度信息"""
        from services.reflexion import _reflect
        mock_llm = AsyncMock()
        mock_llm.chat.return_value = '{"is_complete": true, "reasoning": "", "missing_points": []}'
        dims = {"product_definition": "产品核心问题", "architecture": "架构设计"}
        result = await _reflect("输出", "ningmo", "对话", mock_llm, phase_dimensions=dims)
        # 验证 prompt 包含维度信息
        call_args = mock_llm.chat.call_args
        prompt = call_args[0][0][0]["content"]
        assert "产品核心问题" in prompt
        assert "架构设计" in prompt


# ============================================================
#  MCP Client 测试
# ============================================================


class TestMCPConfig:
    """MCP 配置模型测试"""

    def test_from_yaml_config(self):
        """从 YAML 配置字典解析 MCPConfig"""
        from core.mcp_client import MCPConfig
        config_dict = {
            "filesystem": {
                "enabled": True,
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            },
            "github": {
                "enabled": False,
                "type": "http",
                "url": "http://localhost:8080",
            },
        }
        config = MCPConfig.from_yaml_config(config_dict)
        assert "filesystem" in config.servers
        assert "github" in config.servers
        assert config.servers["filesystem"].command == "npx"
        assert config.servers["filesystem"].enabled is True
        assert config.servers["github"].enabled is False
        assert config.servers["github"].url == "http://localhost:8080"

    def test_from_yaml_config_ignores_non_dict(self):
        """from_yaml_config 忽略非字典值"""
        from core.mcp_client import MCPConfig
        config_dict = {
            "valid": {"enabled": True, "type": "stdio", "command": "echo"},
            "invalid": "not a dict",
            "also_invalid": 42,
        }
        config = MCPConfig.from_yaml_config(config_dict)
        assert "valid" in config.servers
        assert "invalid" not in config.servers
        assert "also_invalid" not in config.servers

    def test_from_yaml_config_empty(self):
        """空配置返回空 MCPConfig"""
        from core.mcp_client import MCPConfig
        config = MCPConfig.from_yaml_config({})
        assert len(config.servers) == 0

    def test_get_enabled_servers(self):
        """获取启用的服务器列表"""
        from core.mcp_client import MCPConfig
        config = MCPConfig.from_yaml_config({
            "active": {"enabled": True, "type": "stdio", "command": "echo"},
            "disabled": {"enabled": False, "type": "http", "url": "http://localhost"},
        })
        enabled = config.get_enabled_servers()
        assert "active" in enabled
        assert "disabled" not in enabled


class TestMCPToolSchema:
    """MCP 工具 Schema 模型测试"""

    def test_creation(self):
        """创建 MCPToolSchema"""
        from core.mcp_client import MCPToolSchema
        schema = MCPToolSchema(
            name="read_file",
            description="读取文件内容",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
            server_name="filesystem",
        )
        assert schema.name == "read_file"
        assert schema.description == "读取文件内容"
        assert schema.server_name == "filesystem"
        assert "path" in schema.input_schema["properties"]

    def test_defaults(self):
        """MCPToolSchema 默认值"""
        from core.mcp_client import MCPToolSchema
        schema = MCPToolSchema(name="test_tool")
        assert schema.description == ""
        assert schema.input_schema == {}
        assert schema.server_name == ""


class TestMCPToolResult:
    """MCP 工具调用结果模型测试"""

    def test_success_result(self):
        """成功的工具调用结果"""
        from core.mcp_client import MCPToolResult
        result = MCPToolResult(
            tool_name="read_file",
            server_name="filesystem",
            content=[{"type": "text", "text": "file content here"}],
        )
        assert result.is_error is False
        assert result.error_message == ""
        assert len(result.content) == 1

    def test_error_result(self):
        """失败的工具调用结果"""
        from core.mcp_client import MCPToolResult
        result = MCPToolResult(
            tool_name="read_file",
            server_name="filesystem",
            is_error=True,
            error_message="File not found",
        )
        assert result.is_error is True
        assert result.error_message == "File not found"

    def test_defaults(self):
        """MCPToolResult 默认值"""
        from core.mcp_client import MCPToolResult
        result = MCPToolResult(tool_name="test", server_name="srv")
        assert result.content == []
        assert result.is_error is False
        assert result.error_message == ""


class TestMCPClientManager:
    """MCP 客户端管理器测试（不连接实际服务器）"""

    def test_init(self):
        """初始化管理器"""
        from core.mcp_client import MCPClientManager, MCPConfig
        config = MCPConfig.from_yaml_config({
            "test": {"enabled": True, "type": "stdio", "command": "echo"},
        })
        manager = MCPClientManager(config)
        assert manager.is_connected is False

    def test_get_server_status(self):
        """获取服务器状态"""
        from core.mcp_client import MCPClientManager, MCPConfig
        config = MCPConfig.from_yaml_config({
            "srv1": {"enabled": True, "type": "stdio", "command": "echo"},
            "srv2": {"enabled": False, "type": "http", "url": "http://localhost"},
        })
        manager = MCPClientManager(config)
        status = manager.get_server_status()
        assert "srv1" in status
        assert status["srv1"]["enabled"] is True
        assert status["srv1"]["connected"] is False
        assert status["srv1"]["type"] == "stdio"
        assert "srv2" in status
        assert status["srv2"]["enabled"] is False

    def test_invalidate_cache_specific(self):
        """清除指定服务器的工具缓存"""
        from core.mcp_client import MCPClientManager, MCPConfig
        config = MCPConfig()
        manager = MCPClientManager(config)
        manager._tool_cache["srv1"] = []
        manager._tool_cache["srv2"] = []
        manager._tool_cache_time["srv1"] = time.time()
        manager._tool_cache_time["srv2"] = time.time()
        manager.invalidate_cache("srv1")
        assert "srv1" not in manager._tool_cache
        assert "srv2" in manager._tool_cache

    def test_invalidate_cache_all(self):
        """清除所有工具缓存"""
        from core.mcp_client import MCPClientManager, MCPConfig
        config = MCPConfig()
        manager = MCPClientManager(config)
        manager._tool_cache["srv1"] = []
        manager._tool_cache_time["srv1"] = time.time()
        manager.invalidate_cache()
        assert len(manager._tool_cache) == 0
        assert len(manager._tool_cache_time) == 0

    def test_config_accessible(self):
        """管理器可访问配置"""
        from core.mcp_client import MCPClientManager, MCPConfig
        config = MCPConfig.from_yaml_config({
            "myserver": {"enabled": True, "type": "sse", "url": "http://mcp.example.com"},
        })
        manager = MCPClientManager(config)
        enabled = manager._config.get_enabled_servers()
        assert "myserver" in enabled
        assert enabled["myserver"].type == "sse"


# ============================================================
#  HITL 测试
# ============================================================


class TestHITLConfig:
    """HITL 配置测试"""

    def test_default_phases(self):
        """默认阶段配置"""
        from core.hitl import HITLConfig
        config = HITLConfig()
        assert config.phases["caiheng"] is True
        assert config.phases["zhenwei"] is True
        assert config.phases["ningmo"] is True

    def test_default_mcp_approval(self):
        """默认 MCP 工具调用确认开启"""
        from core.hitl import HITLConfig
        config = HITLConfig()
        assert config.mcp_tool_approval is True

    def test_default_completion_threshold(self):
        """默认完成度阈值"""
        from core.hitl import HITLConfig
        config = HITLConfig()
        assert config.completion_threshold == 0.5

    def test_default_timeout(self):
        """默认超时为0（不超时）"""
        from core.hitl import HITLConfig
        config = HITLConfig()
        assert config.timeout_seconds == 0

    def test_custom_config(self):
        """自定义配置"""
        from core.hitl import HITLConfig
        config = HITLConfig(
            phases={"caiheng": False},
            mcp_tool_approval=False,
            completion_threshold=0.8,
        )
        assert config.phases["caiheng"] is False
        assert config.mcp_tool_approval is False
        assert config.completion_threshold == 0.8


class TestHumanInterrupt:
    """HumanInterrupt 人工中断记录测试"""

    def test_creation(self):
        """创建中断记录"""
        from core.hitl import HumanInterrupt
        interrupt = HumanInterrupt(
            project_id="proj-1",
            phase="caiheng",
            reason="裁衡阶段结论需要确认",
            content="方案摘要内容",
        )
        assert interrupt.project_id == "proj-1"
        assert interrupt.phase == "caiheng"
        assert interrupt.status == "pending"
        assert interrupt.is_pending is True

    def test_creation_with_options(self):
        """创建带选项的中断记录"""
        from core.hitl import HumanInterrupt
        interrupt = HumanInterrupt(
            project_id="proj-1",
            phase="ningmo",
            reason="凝墨阶段需要确认",
            content="最终方案",
            options=["accept", "ignore", "response", "edit"],
            allow_edit=True,
        )
        assert "edit" in interrupt.options
        assert interrupt.allow_edit is True

    def test_respond_accept(self):
        """接受响应"""
        from core.hitl import HumanInterrupt
        interrupt = HumanInterrupt(
            project_id="proj-1", phase="caiheng", reason="确认", content="内容"
        )
        interrupt.respond("accept")
        assert interrupt.status == "responded"
        assert interrupt.response_type == "accept"
        assert interrupt.responded_at is not None
        assert interrupt.is_pending is False

    def test_respond_with_content(self):
        """带内容的响应"""
        from core.hitl import HumanInterrupt
        interrupt = HumanInterrupt(
            project_id="proj-1", phase="zhenwei", reason="确认", content="内容"
        )
        interrupt.respond("response", content="我建议修改数据库选型")
        assert interrupt.response_type == "response"
        assert interrupt.response_content == "我建议修改数据库选型"

    def test_respond_edit(self):
        """编辑响应"""
        from core.hitl import HumanInterrupt
        interrupt = HumanInterrupt(
            project_id="proj-1", phase="ningmo", reason="确认", content="内容"
        )
        interrupt.respond("edit", content="修改后的内容")
        assert interrupt.response_type == "edit"
        assert interrupt.response_content == "修改后的内容"

    def test_id_format(self):
        """ID 格式以 hitl_ 开头"""
        from core.hitl import HumanInterrupt
        interrupt = HumanInterrupt(
            project_id="proj-1", phase="caiheng", reason="确认", content="内容"
        )
        assert interrupt.id.startswith("hitl_")


class TestHITLDecider:
    """HITL 决策器测试"""

    def test_should_interrupt_caiheng_above_threshold(self):
        """裁衡阶段完成度超过阈值时需要中断"""
        from core.hitl import HITLDecider
        decider = HITLDecider()
        reason = decider.should_interrupt("caiheng", 0.7)
        assert reason is not None
        assert "裁衡" in reason

    def test_should_interrupt_caiheng_below_threshold(self):
        """裁衡阶段完成度低于阈值时不需要中断"""
        from core.hitl import HITLDecider
        decider = HITLDecider()
        reason = decider.should_interrupt("caiheng", 0.3)
        assert reason is None

    def test_should_interrupt_zhenwei(self):
        """甄微阶段需要中断"""
        from core.hitl import HITLDecider
        decider = HITLDecider()
        reason = decider.should_interrupt("zhenwei", 0.6)
        assert reason is not None
        assert "甄微" in reason

    def test_should_interrupt_ningmo(self):
        """凝墨阶段需要中断"""
        from core.hitl import HITLDecider
        decider = HITLDecider()
        reason = decider.should_interrupt("ningmo", 0.8)
        assert reason is not None
        assert "凝墨" in reason

    def test_should_interrupt_qishu_not_configured(self):
        """启枢阶段不在默认配置中，不需要中断"""
        from core.hitl import HITLDecider
        decider = HITLDecider()
        reason = decider.should_interrupt("qishu", 0.9)
        assert reason is None

    def test_should_interrupt_mcp_tool_call(self):
        """MCP 工具调用需要确认"""
        from core.hitl import HITLDecider
        decider = HITLDecider()
        reason = decider.should_interrupt("qishu", 0.5, is_mcp_tool_call=True)
        assert reason is not None
        assert "MCP" in reason

    def test_should_interrupt_mcp_tool_call_disabled(self):
        """MCP 工具调用确认关闭时不需要中断"""
        from core.hitl import HITLDecider, HITLConfig
        config = HITLConfig(mcp_tool_approval=False)
        decider = HITLDecider(config)
        reason = decider.should_interrupt("qishu", 0.5, is_mcp_tool_call=True)
        assert reason is None

    def test_should_interrupt_phase_disabled(self):
        """阶段确认关闭时不需要中断"""
        from core.hitl import HITLDecider, HITLConfig
        config = HITLConfig(phases={"caiheng": False, "zhenwei": True, "ningmo": True})
        decider = HITLDecider(config)
        reason = decider.should_interrupt("caiheng", 0.9)
        assert reason is None

    def test_should_interrupt_completion_score_in_reason(self):
        """中断原因包含完成度百分比"""
        from core.hitl import HITLDecider
        decider = HITLDecider()
        reason = decider.should_interrupt("caiheng", 0.75)
        assert "75%" in reason

    def test_get_interrupt_options(self):
        """获取中断选项"""
        from core.hitl import HITLDecider
        decider = HITLDecider()
        options = decider.get_interrupt_options("caiheng")
        assert "accept" in options
        assert "ignore" in options
        assert "response" in options

    def test_get_interrupt_options_unconfigured_phase(self):
        """未配置阶段的默认选项"""
        from core.hitl import HITLDecider
        decider = HITLDecider()
        options = decider.get_interrupt_options("qishu")
        # 未配置阶段返回默认选项
        assert "accept" in options


# ============================================================
#  Middlewares 测试
# ============================================================


class TestFlowContext:
    """FlowContext 中间件共享上下文测试"""

    def test_creation_defaults(self):
        """默认创建 FlowContext"""
        from services.flow.middlewares import FlowContext
        ctx = FlowContext(project_id="proj-1", message="你好")
        assert ctx.project_id == "proj-1"
        assert ctx.message == "你好"
        assert ctx.conversation == ""
        assert ctx.current_phase is None
        assert ctx.next_phase is None
        assert ctx.short_circuited is False
        assert ctx.short_circuit_response == ""
        assert ctx.stream_chunks == []

    def test_creation_with_all_fields(self):
        """带所有字段创建 FlowContext"""
        from services.flow.middlewares import FlowContext
        ctx = FlowContext(
            project_id="proj-1",
            message="测试消息",
            conversation="历史对话",
            force_workflow="caiheng",
            current_phase="qishu",
            next_phase="caiheng",
            memory_context="记忆上下文",
        )
        assert ctx.force_workflow == "caiheng"
        assert ctx.current_phase == "qishu"
        assert ctx.next_phase == "caiheng"
        assert ctx.memory_context == "记忆上下文"

    def test_mutable_defaults_isolated(self):
        """可变默认值在不同实例间隔离"""
        from services.flow.middlewares import FlowContext
        ctx1 = FlowContext(project_id="p1", message="m1")
        ctx2 = FlowContext(project_id="p2", message="m2")
        ctx1.stream_chunks.append("chunk1")
        assert len(ctx2.stream_chunks) == 0

    def test_short_circuit_fields(self):
        """短路标志字段"""
        from services.flow.middlewares import FlowContext
        ctx = FlowContext(project_id="proj-1", message="你是谁？")
        ctx.short_circuited = True
        ctx.short_circuit_response = "我是 Ssuma"
        assert ctx.short_circuited is True
        assert ctx.short_circuit_response == "我是 Ssuma"


class TestBuildMiddlewareChain:
    """build_middleware_chain 函数测试"""

    def test_build_empty_chain(self):
        """空列表构建空链"""
        from services.flow.middlewares import build_middleware_chain
        chain = build_middleware_chain([])
        assert chain == []

    def test_build_chain_creates_instances(self):
        """构建链创建中间件实例"""
        from services.flow.middlewares import (
            build_middleware_chain,
            MemoryContextMiddleware,
            IdentityMiddleware,
        )
        chain = build_middleware_chain([MemoryContextMiddleware, IdentityMiddleware])
        assert len(chain) == 2
        assert isinstance(chain[0], MemoryContextMiddleware)
        assert isinstance(chain[1], IdentityMiddleware)

    def test_build_chain_each_instance_independent(self):
        """每个实例独立"""
        from services.flow.middlewares import build_middleware_chain, IdentityMiddleware
        chain1 = build_middleware_chain([IdentityMiddleware])
        chain2 = build_middleware_chain([IdentityMiddleware])
        assert chain1[0] is not chain2[0]


class TestIdentityMiddleware:
    """IdentityMiddleware 身份识别中间件测试"""

    @pytest.mark.asyncio
    async def test_pre_process_identity_question_short_circuits(self):
        """身份问题触发短路"""
        from services.flow.middlewares import IdentityMiddleware, FlowContext
        middleware = IdentityMiddleware()
        ctx = FlowContext(project_id="proj-1", message="你是谁？")
        mock_service = MagicMock()
        mock_service._check_identity_question.return_value = "我是 Ssuma，你的 AI 产品助手"
        result = await middleware.pre_process(ctx, mock_service)
        assert result is False
        assert ctx.short_circuited is True
        assert ctx.short_circuit_response == "我是 Ssuma，你的 AI 产品助手"

    @pytest.mark.asyncio
    async def test_pre_process_non_identity_question_passes(self):
        """非身份问题正常通过"""
        from services.flow.middlewares import IdentityMiddleware, FlowContext
        middleware = IdentityMiddleware()
        ctx = FlowContext(project_id="proj-1", message="我想做一个任务管理应用")
        mock_service = MagicMock()
        mock_service._check_identity_question.return_value = None
        result = await middleware.pre_process(ctx, mock_service)
        assert result is True
        assert ctx.short_circuited is False

    @pytest.mark.asyncio
    async def test_pre_process_what_can_you_do(self):
        """问能力问题触发短路"""
        from services.flow.middlewares import IdentityMiddleware, FlowContext
        middleware = IdentityMiddleware()
        ctx = FlowContext(project_id="proj-1", message="你能做什么？")
        mock_service = MagicMock()
        mock_service._check_identity_question.return_value = "我可以帮你做产品方案"
        result = await middleware.pre_process(ctx, mock_service)
        assert result is False
        assert ctx.short_circuited is True


class TestFlowMiddlewareBase:
    """FlowMiddleware 基类测试"""

    @pytest.mark.asyncio
    async def test_base_pre_process_returns_true(self):
        """基类 pre_process 默认返回 True"""
        from services.flow.middlewares import FlowMiddleware, FlowContext
        middleware = FlowMiddleware()
        ctx = FlowContext(project_id="p1", message="m1")
        result = await middleware.pre_process(ctx, None)
        assert result is True

    @pytest.mark.asyncio
    async def test_base_post_process_does_nothing(self):
        """基类 post_process 默认不做任何事"""
        from services.flow.middlewares import FlowMiddleware, FlowContext
        middleware = FlowMiddleware()
        ctx = FlowContext(project_id="p1", message="m1")
        # 不应抛异常
        await middleware.post_process(ctx, None)


class TestMemoryContextMiddleware:
    """MemoryContextMiddleware 记忆上下文中间件测试"""

    @pytest.mark.asyncio
    async def test_pre_process_loads_memory(self):
        """加载项目记忆卡上下文"""
        from services.flow.middlewares import MemoryContextMiddleware, FlowContext
        from core.project_memory import ProjectMemoryCard
        middleware = MemoryContextMiddleware()
        ctx = FlowContext(project_id="proj-1", message="继续讨论")
        mock_service = MagicMock()
        mock_card = ProjectMemoryCard(
            project_id="proj-1",
            project_name="测试项目",
            requirement_summary="构建一个白板",
        )
        mock_service._memory_store.get.return_value = mock_card
        result = await middleware.pre_process(ctx, mock_service)
        assert result is True
        assert ctx.memory_context != ""
        assert "测试项目" in ctx.memory_context

    @pytest.mark.asyncio
    async def test_pre_process_no_memory_still_passes(self):
        """无记忆卡时正常通过"""
        from services.flow.middlewares import MemoryContextMiddleware, FlowContext
        middleware = MemoryContextMiddleware()
        ctx = FlowContext(project_id="proj-1", message="你好")
        mock_service = MagicMock()
        mock_service._memory_store.get.side_effect = Exception("no store")
        result = await middleware.pre_process(ctx, mock_service)
        assert result is True
        assert ctx.memory_context == ""

    @pytest.mark.asyncio
    async def test_pre_process_empty_card_no_context(self):
        """空白记忆卡不注入上下文"""
        from services.flow.middlewares import MemoryContextMiddleware, FlowContext
        from core.project_memory import ProjectMemoryCard
        middleware = MemoryContextMiddleware()
        ctx = FlowContext(project_id="proj-1", message="你好")
        mock_service = MagicMock()
        # 空白卡片：没有 requirement_summary 和 tech_decisions
        mock_card = ProjectMemoryCard(project_id="proj-1")
        mock_service._memory_store.get.return_value = mock_card
        result = await middleware.pre_process(ctx, mock_service)
        assert result is True
        assert ctx.memory_context == ""
