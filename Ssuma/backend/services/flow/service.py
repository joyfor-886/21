from typing import Dict, Any, List, Optional
import logging
import re

from services.intent_analyzer import (
    IntentAnalyzer,
    IntentAnalysisResult,
    UserIntent,
    ClarityLevel,
    FlowState,
    INTENT_LABELS,
)
from services.response_validator import ResponseValidator
from services.context_manager import ContextManager
from services.fact_checker import FactChecker
from services.phase_gates import PhaseCompletionGate
from services.artifact_store import ArtifactStore, extract_artifact_from_response
from core.skill_registry import SkillRegistry
from services.flow.router import FlowRouter
from domain.enums import FlowPhase, CHANNEL_PHASES, WORKFLOW_SYSTEM_PROMPTS, ProjectComplexity

logger = logging.getLogger('Ssuma.FlowService')

MAX_INMEMORY_PROJECTS = 200


class FlowService:
    """Ssuma 核心流程引擎

    支持：
    - 依赖注入（router, skill_registry, llm_factory 等）
    - 实例化测试
    - 并发安全（每个实例独立状态）
    - Pre/Post 中间件链
    """

    STATE_SERVICE_FLOW = "adaptive_flow_current"
    STATE_SERVICE_STATE = "adaptive_flow_state"
    STATE_SERVICE_CHANNEL = "adaptive_flow_channel"

    def __init__(
        self,
        router: Optional[FlowRouter] = None,
        skill_registry=None,
        intent_analyzer=None,
        context_manager=None,
        artifact_store=None,
        fact_checker=None,
        response_validator=None,
        phase_gate=None,
        llm_factory=None,
        middlewares=None,
    ):
        self._router = router or FlowRouter()
        self._skill_registry = skill_registry or SkillRegistry
        self._intent_analyzer = intent_analyzer or IntentAnalyzer
        self._context_manager = context_manager or ContextManager
        self._artifact_store = artifact_store or ArtifactStore
        self._fact_checker = fact_checker or FactChecker
        self._response_validator = response_validator or ResponseValidator
        self._phase_gate = phase_gate or PhaseCompletionGate
        self._llm_factory = llm_factory  # None 时回退到 LLMFactory 类方法
        self._middlewares = middlewares  # None 时使用内置流程

        # 项目记忆卡存储（第二层记忆）
        from core.project_memory import ProjectMemoryStore
        self._memory_store = ProjectMemoryStore(llm_factory)

        self._current_flows: Dict[str, FlowPhase] = {}
        self._flow_states: Dict[str, FlowState] = {}
        self._channel_assignments: Dict[str, str] = {}

    def _get_llm_provider(self, name=None):
        """获取 LLM Provider，优先使用注入的 factory，回退到全局 LLMFactory"""
        if self._llm_factory is not None:
            return self._llm_factory.get_provider(name)
        from core.llm_factory import LLMFactory
        return LLMFactory.get_provider(name)

    def _get_llm_default_provider(self) -> str:
        """获取默认 Provider 名称"""
        if self._llm_factory is not None:
            return self._llm_factory.get_default_provider()
        from core.llm_factory import LLMFactory
        return LLMFactory.get_default_provider()

    @staticmethod
    def extract_interactive_options(text: str) -> List[Dict[str, str]]:
        options: List[Dict[str, str]] = []
        patterns = [
            r'[A-D][\.、\)]\s*(.+?)(?=\n|$)',
            r'[①②③④⑤][\s]*(.+?)(?=\n|$)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if len(matches) >= 2:
                for i, m in enumerate(matches):
                    label = chr(65 + i) if i < 4 else str(i + 1)
                    options.append({"label": label, "text": m.strip()})
                break
        if not options:
            fill_match = re.search(r'[：:]\s*[_＿]{2,}', text)
            if fill_match:
                options.append({"label": "fill", "text": "", "type": "fill"})
        return options

    def _ensure_loaded(self, project_id: str):
        if project_id not in self._flow_states:
            from core.state_repository import StateRepository
            state_data = StateRepository.load(self.STATE_SERVICE_STATE, project_id)
            if state_data is not None:
                self._flow_states[project_id] = FlowState.from_dict(state_data)
            else:
                self._flow_states[project_id] = FlowState(project_id)

        if project_id not in self._current_flows:
            from core.state_repository import StateRepository
            phase_data = StateRepository.load(self.STATE_SERVICE_FLOW, project_id)
            if phase_data is not None:
                try:
                    self._current_flows[project_id] = FlowPhase(phase_data)
                except ValueError:
                    self._current_flows[project_id] = FlowPhase.INTENT_DETECTION
            else:
                self._current_flows[project_id] = FlowPhase.INTENT_DETECTION

        if project_id not in self._channel_assignments:
            from core.state_repository import StateRepository
            channel_data = StateRepository.load(self.STATE_SERVICE_CHANNEL, project_id)
            if channel_data is not None:
                self._channel_assignments[project_id] = channel_data
            else:
                self._channel_assignments[project_id] = "standard"

        self._evict_if_needed()

    def _evict_if_needed(self):
        if len(self._flow_states) <= MAX_INMEMORY_PROJECTS:
            return
        evict_count = len(self._flow_states) - MAX_INMEMORY_PROJECTS + 10
        keys_to_evict = list(self._flow_states.keys())[:evict_count]
        for key in keys_to_evict:
            self._flow_states.pop(key, None)
            self._current_flows.pop(key, None)
            self._channel_assignments.pop(key, None)
        logger.info(f"Evicted {len(keys_to_evict)} projects from memory cache")

    def _save_all_to_repo(self, project_id: str):
        from core.state_repository import StateRepository

        flow_state = self._flow_states.get(project_id)
        if flow_state:
            StateRepository.save(self.STATE_SERVICE_STATE, project_id, flow_state.to_dict())

        current_phase = self._current_flows.get(project_id)
        if current_phase:
            StateRepository.save(self.STATE_SERVICE_FLOW, project_id, current_phase.value)

        channel = self._channel_assignments.get(project_id)
        if channel:
            StateRepository.save(self.STATE_SERVICE_CHANNEL, project_id, channel)

        self._context_manager._save_to_repo(project_id)

    def _get_or_create_flow_state(self, project_id: str) -> FlowState:
        self._ensure_loaded(project_id)
        if project_id not in self._flow_states:
            self._flow_states[project_id] = FlowState(project_id)
        return self._flow_states[project_id]

    def _get_channel_phases(self, project_id: str) -> List[FlowPhase]:
        channel = self._channel_assignments.get(project_id, "standard")
        return CHANNEL_PHASES.get(channel, CHANNEL_PHASES["standard"])

    def _auto_adjust_channel_for_model_tier(self, project_id: str) -> str:
        """根据模型档次自动调整工作流通道"""
        try:
            from core.llm_adapter import get_llm_adapter
            from domain.enums import ModelTier

            adapter = get_llm_adapter()
            provider_name = self._get_llm_default_provider()
            provider = self._get_llm_provider(provider_name)
            model_name = getattr(provider, "model", "")
            tier = adapter.detect_tier(model_name)

            current_channel = self._channel_assignments.get(project_id, "standard")
            if tier == ModelTier.INSUFFICIENT and current_channel == "standard":
                self._channel_assignments[project_id] = "fast"
                logger.info(f"Auto-adjusted channel to 'fast' for INSUFFICIENT model tier")
                return "fast"
            elif tier == ModelTier.BASIC and current_channel == "deep":
                self._channel_assignments[project_id] = "standard"
                logger.info(f"Auto-adjusted channel from 'deep' to 'standard' for BASIC model tier")
                return "standard"
        except Exception as e:
            logger.warning(f"Auto-adjust channel failed: {e}")
        return self._channel_assignments.get(project_id, "standard")

    def _build_pre_middlewares(self):
        """构建 Pre-generation 中间件链"""
        from services.flow.middlewares import build_middleware_chain, PRE_GENERATION_MIDDLEWARES
        if self._middlewares is not None:
            # 用户自定义中间件链
            return build_middleware_chain(self._middlewares.get("pre", PRE_GENERATION_MIDDLEWARES))
        return build_middleware_chain(PRE_GENERATION_MIDDLEWARES)

    def _build_post_middlewares(self):
        """构建 Post-generation 中间件链"""
        from services.flow.middlewares import build_middleware_chain, POST_GENERATION_MIDDLEWARES
        if self._middlewares is not None:
            return build_middleware_chain(self._middlewares.get("post", POST_GENERATION_MIDDLEWARES))
        return build_middleware_chain(POST_GENERATION_MIDDLEWARES)

    async def process_message(
        self,
        project_id: str,
        message: str,
        conversation: Optional[str] = None,
        force_workflow: Optional[str] = None,
        attachments: Optional[List[dict]] = None,
    ) -> Dict[str, Any]:
        """非流式处理 — 收集 process_message_stream 的所有 chunk 后返回完整结果"""
        final_chunk = None
        async for chunk in self.process_message_stream(
            project_id, message, conversation, force_workflow, attachments
        ):
            final_chunk = chunk

        if final_chunk is None:
            return {
                "project_id": project_id,
                "response": "",
                "current_phase": "intent_detection",
                "intent": "chat",
                "clarity": "standard",
                "suggested_next": "qishu",
                "validation": {"is_valid": True, "score": 1.0, "issues": []},
                "completion": {"score": 0.0, "dimensions_covered": [], "dimensions_missing": [], "should_advance": False},
                "channel": "standard",
                "turn": 0,
                "detected_skill": None,
            }

        # 从流式最终 chunk 组装非流式返回格式
        full_response = final_chunk.get("full_response", "")
        current_phase = final_chunk.get("current_phase", final_chunk.get("phase", "intent_detection"))
        completion_score = final_chunk.get("completion_score", 0.0)

        # 验证
        from services.flow.router import FlowPhase as _FP
        try:
            phase_enum = _FP(current_phase)
        except ValueError:
            phase_enum = _FP.INTENT_DETECTION
        validation = self._response_validator.validate(full_response, phase_enum)

        return {
            "project_id": project_id,
            "response": full_response,
            "current_phase": current_phase,
            "intent": final_chunk.get("intent", "chat"),
            "clarity": final_chunk.get("clarity", "standard"),
            "suggested_next": final_chunk.get("suggested_next", current_phase),
            "validation": {
                "is_valid": validation.is_valid,
                "score": validation.score,
                "issues": validation.issues,
            },
            "completion": {
                "score": completion_score,
                "dimensions_covered": final_chunk.get("dimensions_covered", []),
                "dimensions_missing": final_chunk.get("dimensions_missing", []),
                "should_advance": completion_score >= 0.55,
            },
            "channel": final_chunk.get("channel", "standard"),
            "turn": final_chunk.get("turn", 0),
            "detected_skill": final_chunk.get("detected_skill"),
        }

    async def process_message_stream(
        self,
        project_id: str,
        message: str,
        conversation: Optional[str] = None,
        force_workflow: Optional[str] = None,
        attachments: Optional[List[dict]] = None,
    ):
        from services.flow.middlewares import FlowContext

        current_phase = self._current_flows.get(project_id, FlowPhase.INTENT_DETECTION)
        flow_state = self._get_or_create_flow_state(project_id)

        # 构建中间件上下文
        ctx = FlowContext(
            project_id=project_id,
            message=message,
            conversation=conversation or "",
            force_workflow=force_workflow,
            attachments=attachments,
        )

        # 添加用户消息到上下文窗口
        ctx_window = self._context_manager.get_window(project_id)
        if message:
            ctx_window.add_message("user", message)

        # ===== Phase 1: Pre-generation 中间件链 =====
        pre_middlewares = self._build_pre_middlewares()
        for mw in pre_middlewares:
            should_continue = await mw.pre_process(ctx, self)
            if not should_continue:
                # 短路返回（如身份识别）
                break

        # 处理短路
        if ctx.short_circuited:
            ctx_window.add_message("assistant", ctx.short_circuit_response)
            flow_state.conversation_turns += 1
            self._save_all_to_repo(project_id)
            yield {
                "content": ctx.short_circuit_response,
                "phase": current_phase.value,
                "done": True,
                "project_id": project_id,
                "full_response": ctx.short_circuit_response,
                "completion_score": 0.0,
                "current_phase": current_phase.value,
                "suggested_next": current_phase.value,
                "channel": flow_state.channel,
                "turn": flow_state.conversation_turns,
                "intent": "chat",
                "clarity": flow_state.channel or "standard",
                "detected_skill": None,
                "dimensions_covered": [],
                "dimensions_missing": [],
            }
            return

        # ===== Phase 2: 流式 LLM 生成 =====
        next_phase = FlowPhase(ctx.next_phase) if ctx.next_phase else FlowPhase.INTENT_DETECTION

        full_response = ""
        async for chunk in self._generate_response_stream(
            next_phase, message, conversation or "", ctx.intent_result,
            project_id=project_id, attachments=attachments,
            skill_name=ctx.skill_name, artifact_context=ctx.artifact_context,
            memory_context=ctx.memory_context,
            mcp_tools_context=ctx.mcp_tools_context,
        ):
            full_response += chunk
            yield {
                "content": chunk,
                "phase": next_phase.value,
                "done": False,
            }

        ctx.full_response = full_response

        # ===== Phase 3: Post-generation 中间件链（逆序 post_process）=====
        post_middlewares = self._build_post_middlewares()
        for mw in reversed(post_middlewares):
            await mw.post_process(ctx, self)

        # ===== Phase 4: 组装最终输出 =====
        interactive_options = self.extract_interactive_options(ctx.full_response)

        # 如果有提醒文本，额外 yield 一个 chunk
        if ctx.reminder_text:
            yield {
                "content": ctx.reminder_text,
                "phase": next_phase.value,
                "done": False,
            }

        yield {
            "content": "",
            "phase": next_phase.value,
            "done": True,
            "project_id": project_id,
            "full_response": ctx.full_response,
            "completion_score": ctx.completion_result.score if ctx.completion_result else 0.0,
            "current_phase": next_phase.value,
            "suggested_next": self._router.get_suggested_next_phase(
                next_phase, self._channel_assignments.get(project_id, "standard")
            ).value,
            "channel": flow_state.channel,
            "turn": flow_state.conversation_turns,
            "interactive_options": interactive_options,
            "intent": ctx.intent_result.intent.value if ctx.intent_result else "chat",
            "clarity": ctx.intent_result.clarity.value if ctx.intent_result else "standard",
            "detected_skill": ctx.skill_name,
            "dimensions_covered": ctx.completion_result.dimensions_covered if ctx.completion_result else [],
            "dimensions_missing": ctx.completion_result.dimensions_missing if ctx.completion_result else [],
            # HITL 中断信息
            "hitl_interrupt": {
                "id": ctx.hitl_interrupt.id,
                "phase": ctx.hitl_interrupt.phase,
                "reason": ctx.hitl_interrupt.reason,
                "content": ctx.hitl_interrupt.content,
                "options": ctx.hitl_interrupt.options,
                "status": ctx.hitl_interrupt.status,
            } if ctx.hitl_interrupt else None,
        }

    async def _generate_response_stream(
        self,
        phase: FlowPhase,
        message: str,
        conversation_history: str,
        intent_result: IntentAnalysisResult,
        project_id: Optional[str] = None,
        attachments: Optional[List[dict]] = None,
        skill_name: Optional[str] = None,
        artifact_context: str = "",
        memory_context: str = "",
        mcp_tools_context: str = "",
    ):
        if phase == FlowPhase.INTENT_DETECTION:
            yield intent_result.reasoning
            return

        system_prompt = WORKFLOW_SYSTEM_PROMPTS.get(phase, "")

        if artifact_context:
            system_prompt = f"{system_prompt}\n\n{artifact_context}" if system_prompt else artifact_context

        if memory_context:
            system_prompt = f"{system_prompt}\n\n{memory_context}" if system_prompt else memory_context

        # MCP 工具上下文注入 — 让 LLM 知道可调用的外部工具
        if mcp_tools_context:
            mcp_section = (
                "## 可用的外部工具（MCP）\n\n"
                "你可以通过在回复中使用以下格式来调用这些工具：\n"
                "```tool_call\n"
                '{"tool": "工具名", "arguments": {参数}}\n'
                "```\n\n"
                f"{mcp_tools_context}\n\n"
                "调用工具后，系统会返回结果供你继续分析。请在需要时才调用工具。"
            )
            system_prompt = f"{system_prompt}\n\n{mcp_section}" if system_prompt else mcp_section

        if phase == FlowPhase.TANYIN:
            from services.tanyin_service import TanyinService
            trigger_result = TanyinService.should_trigger_tanyin(project_id, message)
            if trigger_result.get("should_trigger"):
                tanyin_prompt = TanyinService.get_tanyin_prompt(project_id, message)
                if tanyin_prompt:
                    system_prompt = tanyin_prompt

        user_content = message
        if attachments:
            has_images = any(att.get("type") == "image" for att in attachments)
            if has_images:
                user_content = [{"type": "text", "text": message}]
                for att in attachments:
                    if att.get("type") == "image" and att.get("data"):
                        user_content.append({"type": "image_url", "image_url": {"url": att["data"]}})
                    elif att.get("type") == "file" and att.get("content"):
                        user_content[0]["text"] += f"\n\n[附件: {att.get('filename')}]\n{att['content']}"
            else:
                for att in attachments:
                    if att.get("type") == "file" and att.get("content"):
                        user_content += f"\n\n[附件: {att.get('filename')}]\n{att['content']}"

        if project_id:
            from db.sqlite import Database as _DB
            _db = _DB()
            messages = self._context_manager.build_llm_messages(
                project_id, user_content if isinstance(user_content, str) else message,
                db=_db, system_prompt=system_prompt, max_history=30,
            )
        else:
            full_conversation = self._build_conversation_context(
                project_id, message, conversation_history, artifact_context
            )
            skill_context = self._build_skill_context(project_id, phase, artifact_context)
            from core.skill_registry import Skill
            temp_skill = Skill.__new__(Skill)
            messages = temp_skill.build_chat_messages(system_prompt, full_conversation, skill_context)

        if intent_result.context.get("key_insights"):
            messages.append({
                "role": "system",
                "content": "关键洞察: " + ", ".join(intent_result.context["key_insights"])
            })

        if project_id:
            reminder = self._fact_checker.generate_consistency_reminder(project_id)
            if reminder:
                messages.append({"role": "system", "content": reminder})

        try:
            provider = self._get_llm_provider()
            async for chunk in provider.chat_stream(messages, max_tokens=4096):
                yield chunk
        except Exception as e:
            logger.error(f"Flow stream generation failed: {e}")
            yield f"错误: {str(e)}"

    def _build_conversation_context(
        self,
        project_id: Optional[str],
        message: str,
        conversation_history: str,
        artifact_context: str,
    ) -> str:
        parts = []
        if conversation_history and conversation_history.strip():
            parts.append(f"【对话历史】\n{conversation_history}")
        elif project_id:
            ctx_window = self._context_manager.get_window(project_id)
            if ctx_window.recent_messages:
                history_text = "\n".join(
                    f"{'用户' if m['role'] == 'user' else '助手'}: {m['content']}"
                    for m in ctx_window.recent_messages
                )
                parts.append(f"【对话历史】\n{history_text}")
        parts.append(f"【当前用户消息】\n{message}")
        return "\n\n---\n\n".join(parts)

    def _build_skill_context(
        self,
        project_id: Optional[str],
        phase: FlowPhase,
        artifact_context: str,
    ) -> Dict[str, Any]:
        context: Dict[str, Any] = {}
        if artifact_context:
            context["artifact_context"] = artifact_context
        if project_id:
            artifacts = self._artifact_store.get_all(project_id)
            for artifact in artifacts:
                if artifact.phase in ("qishu", "tanyin") and artifact.decisions:
                    if "original_requirements" not in context:
                        context["original_requirements"] = artifact.decisions
                if artifact.phase in ("ceshu", "zhenwei", "caiheng") and artifact.summary:
                    if "generated_spec" not in context:
                        context["generated_spec"] = artifact.summary
                    if "current_spec" not in context:
                        context["current_spec"] = artifact.summary
            if "generated_spec" not in context:
                ctx_window = self._context_manager.get_window(project_id)
                if ctx_window.recent_messages:
                    assistant_msgs = [
                        m["content"] for m in ctx_window.recent_messages
                        if m["role"] == "assistant"
                    ]
                    if assistant_msgs:
                        context["generated_spec"] = assistant_msgs[-1][:5000]
        return context

    # ===== 项目复杂度评估 =====

    def _check_identity_question(self, message: str) -> Optional[str]:
        """检测是否为身份/自我介绍类问题，返回枢墨介绍文案"""
        if not message or not message.strip():
            return None

        identity_patterns = [
            r'你是谁',
            r'你叫什么',
            r'你是[什么哪位]',
            r'介绍.*自己',
            r'自我.*介绍',
            r'who\s+are\s+you',
            r'what\s+is\s+your\s+name',
            r'what\s+are\s+you',
            r'你的名字',
            r'你是.*模型',
            r'你是.*AI',
            r'你是.*助手',
            r'介绍.*一下.*你',
            r'你是什么',
            r'你叫什么名字',
        ]

        msg_lower = message.strip().lower()
        matched = any(re.search(p, msg_lower) for p in identity_patterns)

        # 只在短消息（<=30字）中触发，避免误判
        if not matched or len(message.strip()) > 30:
            return None

        # 获取当前模型信息
        model_display = "AI 模型"
        recommended = "Claude Sonnet 4.6 / GPT-4o / DeepSeek-V3"
        try:
            from core.llm_adapter import get_llm_adapter

            provider_name = self._get_llm_default_provider()
            provider = self._get_llm_provider(provider_name)
            model_name = getattr(provider, "model", "")
            adapter = get_llm_adapter()
            tier = adapter.detect_tier(model_name)
            model_display = f"{model_name}（{tier.label}）"

            if tier.value == "adequate":
                recommended = "当前模型已达达标档，可充分发挥七艺全部能力"
            elif tier.value == "basic":
                recommended = "建议使用 Claude Sonnet 4.6 / GPT-4o / DeepSeek-V3 等 ≥32B 参数模型以获得最佳体验"
            else:
                recommended = "当前模型能力不足，强烈建议切换到 Claude Sonnet 4.6 / GPT-4o / DeepSeek-V3 等模型"
        except Exception:
            pass

        return (
            f"你好！我是 **枢墨（Ssuma）**，你的 AI 项目共创伙伴。\n\n"
            f"我通过「八技艺」工作流——启枢·追问、探隐·深问、裁衡·审视、甄微·评审、策书·规划、凝墨·成案、破妄·验证、渐衍·演进——"
            f"帮你把模糊的想法一步步打磨成 AI IDE（Cursor/Trae/Copilot）可以直接执行的完整方案。\n\n"
            f"🖥️ 当前使用模型：**{model_display}**\n"
            f"💡 {recommended}\n\n"
            f"你有什么想法需要和我讨论吗？"
        )

    def _detect_complexity(self, description: str, features_count: int = 0) -> ProjectComplexity:
        """基于项目描述自动检测复杂度"""
        desc_lower = description.lower()

        # 平台级关键词
        platform_keywords = [
            "微服务", "microservice", "多系统", "数据平台", "数据 pipeline",
            "高并发", "million users", "百万用户", "multi-tenant", "多租户",
            "saas platform", "平台", "infrastructure", "基础设施",
        ]
        if any(kw in desc_lower for kw in platform_keywords):
            return ProjectComplexity.PLATFORM

        # 复杂项目关键词
        complex_keywords = [
            "支付", "payment", "实时", "real-time", "websocket", "多角色",
            "权限", "permission", "rbac", "文件上传", "upload", "搜索", "search",
            "通知", "notification", "消息", "messaging", "社交", "social",
            "电商", "ecommerce", "dashboard", "仪表盘", "analytics",
        ]
        complex_count = sum(1 for kw in complex_keywords if kw in desc_lower)
        if complex_count >= 2 or features_count >= 6:
            return ProjectComplexity.COMPLEX

        # 中等项目关键词
        moderate_keywords = [
            "认证", "auth", "登录", "注册", "crud", "表单", "form",
            "数据库", "database", "列表", "list", "详情", "detail",
        ]
        moderate_count = sum(1 for kw in moderate_keywords if kw in desc_lower)
        if moderate_count >= 2 or features_count >= 3:
            return ProjectComplexity.MODERATE

        return ProjectComplexity.SIMPLE

    # ===== AI IDE 文件导出 =====

    def export_ide_files(self, project_id: str) -> Dict[str, Any]:
        """将当前项目状态导出为 AI IDE 可用的文件集合

        返回所有生成文件的 {path: content} 字典。
        """
        self._ensure_loaded(project_id)
        flow_state = self._flow_states.get(project_id)
        ctx_window = self._context_manager.get_window(project_id)

        # 收集项目信息
        all_msgs = ctx_window.recent_messages if ctx_window else []
        user_msgs = [m["content"] for m in all_msgs if m["role"] == "user"]

        # 从对话中推断项目名称
        project_name = self._infer_project_name(user_msgs)

        # 收集 artifacts
        artifacts = self._artifact_store.get_all(project_id)
        product_spec = ""
        tech_spec = ""
        exec_spec = ""

        for a in artifacts:
            if a.phase in ("qishu", "tanyin") and a.summary:
                if not product_spec:
                    product_spec = a.summary
            if a.phase in ("caiheng", "zhenwei") and a.summary:
                if not tech_spec:
                    tech_spec = a.summary
            if a.phase in ("ceshu",) and a.summary:
                if not exec_spec:
                    exec_spec = a.summary
            if a.phase == "ningmo" and a.summary:
                product_spec = a.summary  # ningmo 包含完整的方案

        # 如果没有 artifact，从对话提取
        if not product_spec:
            assistant_msgs = [m["content"] for m in all_msgs if m["role"] == "assistant"]
            if assistant_msgs:
                product_spec = assistant_msgs[-1][:5000]

        # 构建 spec 字典
        description = user_msgs[0][:200] if user_msgs else ""
        complexity = self._detect_complexity(description)

        spec = {
            "name": project_name,
            "description": description,
            "tech_stack": "根据对话确定",
            "product_spec": product_spec,
            "tech_spec": tech_spec,
            "exec_spec": exec_spec,
            "features": self._extract_features_from_artifacts(artifacts),
            "decisions": [a.summary for a in artifacts if a.decisions],
            "out_of_scope": [],
        }

        # 调用 IDE Exporter
        from services.ide_exporter import IDEExporter
        exported = IDEExporter.export(spec)

        logger.info(
            f"Exported {len(exported.files)} IDE files for project '{project_id}' "
            f"(complexity: {complexity.value})"
        )

        return {
            "project_name": project_name,
            "complexity": complexity.value,
            "complexity_label": complexity.label,
            "files": exported.files,
            "file_count": len(exported.files),
        }

    def _infer_project_name(self, user_msgs: List[str]) -> str:
        """从用户消息中推断项目名称"""
        if not user_msgs:
            return "my-project"

        first_msg = user_msgs[0]

        # 尝试匹配「项目名」或「项目：XXX」等模式
        patterns = [
            r'「(.+?)」',
            r'项目名[称]?[：:]\s*(.+?)(?:[，。,\.\n]|$)',
            r'项目[：:]\s*(.+?)(?:[，。,\.\n]|$)',
        ]
        for pattern in patterns:
            match = re.search(pattern, first_msg)
            if match:
                name = match.group(1).strip()
                if len(name) <= 30:
                    return name

        # 取前 30 字符作为项目名
        return first_msg[:30].replace("\n", " ").strip()

    def _extract_features_from_artifacts(self, artifacts: list) -> List[str]:
        """从 artifacts 中提取功能列表"""
        features = []
        for a in artifacts:
            if a.phase in ("qishu", "tanyin") and a.decisions:
                features.extend(a.decisions)
            if a.summary and "功能" in a.summary:
                # 尝试提取功能相关的行
                for line in a.summary.split("\n"):
                    line = line.strip()
                    if line.startswith("-") and len(line) < 200:
                        features.append(line.lstrip("- ").strip())
        return list(set(features))[:10]  # 去重，最多 10 个

    def get_flow_status(self, project_id: str) -> Dict[str, Any]:
        self._ensure_loaded(project_id)
        current_phase = self._current_flows.get(project_id, FlowPhase.INTENT_DETECTION)
        flow_state = self._flow_states.get(project_id)

        ctx_status = self._context_manager.get_status(project_id) if project_id else {}
        ctx_window = self._context_manager.get_window(project_id) if project_id else None

        completion_score = 0.0
        if flow_state and current_phase.value in flow_state.phase_completion:
            completion_score = flow_state.phase_completion[current_phase.value]

        channel = self._channel_assignments.get(project_id, "standard")
        channel_phases = self._get_channel_phases(project_id)

        total_phases = len(channel_phases)
        completed_phases = 0
        if flow_state:
            for phase in channel_phases:
                if phase.value in flow_state.phase_completion and flow_state.phase_completion[phase.value] >= 0.55:
                    completed_phases += 1
        overall_progress = (completed_phases / total_phases * 100) if total_phases > 0 else 0

        artifacts_summary = []
        for artifact in self._artifact_store.get_all(project_id):
            artifacts_summary.append({
                "phase": artifact.phase,
                "summary": artifact.summary,
                "decisions_count": len(artifact.decisions),
                "open_questions_count": len(artifact.open_questions),
            })

        # 检测复杂度
        all_msgs = ctx_window.recent_messages if ctx_window else []
        user_msgs = [m["content"] for m in all_msgs if m["role"] == "user"]
        description = user_msgs[0][:200] if user_msgs else ""
        complexity = self._detect_complexity(description, features_count=len(artifacts_summary))

        return {
            "current_phase": current_phase.value,
            "current_phase_label": current_phase.value.replace("_", " ").title(),
            "channel": channel,
            "channel_phases": [p.value for p in channel_phases],
            "overall_progress": round(overall_progress, 1),
            "workflow_history": flow_state.workflow_history if flow_state else [],
            "conversation_turns": flow_state.conversation_turns if flow_state else 0,
            "completion_score": completion_score,
            "phase_completion": flow_state.phase_completion if flow_state else {},
            "suggested_next": self._router.get_suggested_next_phase(
                current_phase, channel
            ).value if flow_state else FlowPhase.QISHU.value,
            "context": ctx_status,
            "artifacts": artifacts_summary,
            "complexity": complexity.value,
            "complexity_label": complexity.label,
            "can_export": current_phase == FlowPhase.NINGMO or (flow_state and flow_state.spec_generated) if flow_state else False,
            "should_remind": self._response_validator.should_remind_next_phase(
                current_phase, flow_state.conversation_turns if flow_state else 0
            ) if flow_state else False,
        }

    def get_flow_options(self, project_id: str) -> List[Dict[str, Any]]:
        self._ensure_loaded(project_id)
        current_phase = self._current_flows.get(project_id, FlowPhase.INTENT_DETECTION)

        options_map = {
            FlowPhase.INTENT_DETECTION: [
                {"id": "qishu", "label": "启枢", "description": "追问澄清，深入思考需求", "icon": "💭"},
                {"id": "tanyin", "label": "探隐", "description": "探求隐情，系统化收集需求", "icon": "📋"},
                {"id": "ningmo", "label": "凝墨", "description": "直接产出具执行方案", "icon": "📄"},
            ],
            FlowPhase.QISHU: [
                {"id": "tanyin", "label": "探隐", "description": "切换到探隐阶段", "icon": "📋"},
                {"id": "caiheng", "label": "裁衡", "description": "审视产品价值", "icon": "👔"},
                {"id": "zhenwei", "label": "甄微", "description": "评审技术实现", "icon": "⚙️"},
                {"id": "ningmo", "label": "凝墨", "description": "产出具执行方案", "icon": "📄"},
            ],
            FlowPhase.TANYIN: [
                {"id": "caiheng", "label": "裁衡", "description": "审视产品价值", "icon": "👔"},
                {"id": "zhenwei", "label": "甄微", "description": "评审技术实现", "icon": "⚙️"},
                {"id": "ningmo", "label": "凝墨", "description": "产出具执行方案", "icon": "📄"},
            ],
            FlowPhase.CAIHENG: [
                {"id": "zhenwei", "label": "甄微", "description": "评审技术实现", "icon": "⚙️"},
                {"id": "ceshu", "label": "策书", "description": "分解为任务", "icon": "📝"},
                {"id": "ningmo", "label": "凝墨", "description": "产出具执行方案", "icon": "📄"},
            ],
            FlowPhase.ZHENWEI: [
                {"id": "ceshu", "label": "策书", "description": "分解为任务", "icon": "📝"},
                {"id": "ningmo", "label": "凝墨", "description": "产出具执行方案", "icon": "📄"},
            ],
            FlowPhase.CESHU: [
                {"id": "ningmo", "label": "凝墨", "description": "产出具执行方案", "icon": "📄"},
            ],
            FlowPhase.NINGMO: [
                {"id": "powang", "label": "破妄", "description": "覆盖验证方案", "icon": "🔍"},
                {"id": "jianyan", "label": "渐衍", "description": "分阶段生成", "icon": "🌱"},
                {"id": "restart", "label": "重新开始", "description": "开始新项目", "icon": "🔄"},
            ],
            FlowPhase.POWANG: [
                {"id": "jianyan", "label": "渐衍", "description": "分阶段生成", "icon": "🌱"},
            ],
            FlowPhase.JIANYAN: [
                {"id": "restart", "label": "重新开始", "description": "开始新项目", "icon": "🔄"},
            ],
            FlowPhase.COMPLETED: [
                {"id": "qishu", "label": "启枢", "description": "讨论新想法", "icon": "💭"},
                {"id": "restart", "label": "重新开始", "description": "开始新项目", "icon": "🔄"},
            ],
        }

        return options_map.get(current_phase, [])

    def reset_flow(self, project_id: str):
        from core.state_repository import StateRepository

        if project_id in self._current_flows:
            del self._current_flows[project_id]
        if project_id in self._flow_states:
            del self._flow_states[project_id]
        if project_id in self._channel_assignments:
            del self._channel_assignments[project_id]
        self._intent_analyzer.reset_state(project_id)
        self._artifact_store.clear(project_id)
        from services.context_manager import ContextManager
        ContextManager.clear_window(project_id)

        StateRepository.delete(self.STATE_SERVICE_FLOW, project_id)
        StateRepository.delete(self.STATE_SERVICE_STATE, project_id)
        StateRepository.delete(self.STATE_SERVICE_CHANNEL, project_id)

    def switch_workflow(self, project_id: str, workflow: str) -> bool:
        new_phase = self._router.workflow_to_phase(workflow)
        self._current_flows[project_id] = new_phase
        self._save_all_to_repo(project_id)
        logger.info(f"Workflow switched: project={project_id}, workflow={workflow}")
        return True


_flow_service_instance: Optional[FlowService] = None


def get_flow_service() -> FlowService:
    global _flow_service_instance
    if _flow_service_instance is None:
        _flow_service_instance = FlowService()
    return _flow_service_instance
