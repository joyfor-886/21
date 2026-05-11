from typing import Dict, Any, List, Optional
import logging

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
from services.flow.router import (
    FlowPhase,
    FlowRouter,
    CHANNEL_PHASES,
    WORKFLOW_SYSTEM_PROMPTS,
)

logger = logging.getLogger('Ssuma.FlowService')

MAX_INMEMORY_PROJECTS = 200


class FlowService:
    """AdaptiveFlowService 的实例化版本

    支持：
    - 依赖注入（router, skill_registry 等）
    - 实例化测试
    - 并发安全（每个实例独立状态）
    - 向后兼容（AdaptiveFlowService 委托到此实例）
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
    ):
        self._router = router or FlowRouter()
        self._skill_registry = skill_registry or SkillRegistry
        self._intent_analyzer = intent_analyzer or IntentAnalyzer
        self._context_manager = context_manager or ContextManager
        self._artifact_store = artifact_store or ArtifactStore
        self._fact_checker = fact_checker or FactChecker
        self._response_validator = response_validator or ResponseValidator
        self._phase_gate = phase_gate or PhaseCompletionGate

        self._current_flows: Dict[str, FlowPhase] = {}
        self._flow_states: Dict[str, FlowState] = {}
        self._channel_assignments: Dict[str, str] = {}

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
            from core.llm_factory import LLMFactory
            from domain.enums import ModelTier

            adapter = get_llm_adapter()
            provider_name = LLMFactory.get_default_provider()
            provider = LLMFactory.get_provider(provider_name)
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

    async def process_message(
        self,
        project_id: str,
        message: str,
        conversation: Optional[str] = None,
        force_workflow: Optional[str] = None,
        attachments: Optional[List[dict]] = None,
    ) -> Dict[str, Any]:
        current_phase = self._current_flows.get(project_id, FlowPhase.INTENT_DETECTION)
        flow_state = self._get_or_create_flow_state(project_id)

        ctx_window = self._context_manager.get_window(project_id)
        if message:
            ctx_window.add_message("user", message)

        detected_skill = self._skill_registry.detect_skill(message)

        intent_result = await self._intent_analyzer.analyze(
            project_id, message, conversation or "", force_workflow
        )

        if flow_state.channel == "standard" and intent_result.context.get("channel"):
            channel = intent_result.context["channel"]
            self._channel_assignments[project_id] = channel
            flow_state.channel = channel

        self._auto_adjust_channel_for_model_tier(project_id)

        next_phase = self._router.determine_next_phase(
            current_phase, intent_result, force_workflow,
            self._channel_assignments.get(project_id, "standard"),
            flow_state.phase_completion,
        )
        self._current_flows[project_id] = next_phase

        skill_name = None
        if force_workflow:
            skill_name = None
        elif detected_skill and next_phase == FlowPhase.INTENT_DETECTION:
            skill_name = detected_skill
        elif detected_skill and detected_skill == next_phase.value:
            skill_name = detected_skill

        artifact_context = self._artifact_store.build_context_for_phase(
            project_id, next_phase.value
        )

        response_text = await self._generate_response(
            next_phase, message, conversation or "", intent_result,
            project_id=project_id, attachments=attachments,
            skill_name=skill_name, artifact_context=artifact_context,
        )

        ctx_window.add_message("assistant", response_text)

        completion_result = self._phase_gate.evaluate(
            next_phase.value, conversation or message, flow_state.conversation_turns,
        )
        flow_state.phase_completion[next_phase.value] = completion_result.score

        artifact = await extract_artifact_from_response(
            next_phase.value, response_text, conversation or "", completion_result,
        )
        self._artifact_store.add(project_id, artifact)

        validation = self._response_validator.validate(response_text, next_phase)

        if completion_result.should_advance and next_phase != FlowPhase.NINGMO:
            suggested_next = self._router.get_suggested_next_phase(
                next_phase, self._channel_assignments.get(project_id, "standard")
            )
            if suggested_next != next_phase:
                intent_label = INTENT_LABELS.get(
                    self._router.intent_for_phase(suggested_next), suggested_next.value
                )
                reminder = f"💡 当前阶段讨论已经比较充分（完成度 {completion_result.score:.0%}），可以进入下一阶段：{intent_label}"
                response_text += f"\n\n{reminder}"
        elif self._response_validator.should_remind_next_phase(
            next_phase, flow_state.conversation_turns
        ):
            if not completion_result.should_advance and completion_result.next_questions:
                question = completion_result.next_questions[0]
                response_text += f"\n\n💡 我们还需要深入一个方面：{question}"
            else:
                reminder = self._response_validator.generate_reminder(next_phase)
                response_text += f"\n\n💡 {reminder}"

        flow_state.workflow_history.append({
            "phase": next_phase.value,
            "turn": flow_state.conversation_turns,
            "completion_score": completion_result.score,
            "timestamp": __import__('datetime').datetime.now().isoformat(),
        })

        flow_state.conversation_turns += 1
        if next_phase == FlowPhase.NINGMO:
            flow_state.spec_generated = True

        self._save_all_to_repo(project_id)

        return {
            "project_id": project_id,
            "response": response_text,
            "current_phase": next_phase.value,
            "intent": intent_result.intent.value,
            "clarity": intent_result.clarity.value,
            "suggested_next": self._router.get_suggested_next_phase(
                next_phase, self._channel_assignments.get(project_id, "standard")
            ).value,
            "validation": {
                "is_valid": validation.is_valid,
                "score": validation.score,
                "issues": validation.issues,
            },
            "completion": {
                "score": completion_result.score,
                "dimensions_covered": completion_result.dimensions_covered,
                "dimensions_missing": completion_result.dimensions_missing,
                "should_advance": completion_result.should_advance,
            },
            "channel": flow_state.channel,
            "turn": flow_state.conversation_turns,
            "detected_skill": skill_name,
        }

    async def _generate_response(
        self,
        phase: FlowPhase,
        message: str,
        conversation_history: str,
        intent_result: IntentAnalysisResult,
        project_id: Optional[str] = None,
        attachments: Optional[List[dict]] = None,
        skill_name: Optional[str] = None,
        artifact_context: str = "",
    ) -> str:
        from core.llm_factory import LLMFactory

        if phase == FlowPhase.INTENT_DETECTION:
            return intent_result.reasoning

        full_conversation = self._build_conversation_context(
            project_id, message, conversation_history, artifact_context
        )

        skill_context = self._build_skill_context(project_id, phase, artifact_context)

        if skill_name:
            skill = self._skill_registry.get_skill(skill_name)
            if skill:
                try:
                    result = await skill.run(full_conversation, context=skill_context)
                    return result.response
                except Exception as e:
                    logger.warning(f"Skill {skill_name} failed: {e}, falling back to flow")

        phase_skill_name = phase.value
        skill = self._skill_registry.get_skill(phase_skill_name)
        if skill:
            try:
                result = await skill.run(full_conversation, context=skill_context)
                return result.response
            except Exception as e:
                logger.warning(f"Phase skill {phase_skill_name} failed: {e}, falling back to LLM")

        system_prompt = WORKFLOW_SYSTEM_PROMPTS.get(phase, "")

        if artifact_context:
            system_prompt = f"{system_prompt}\n\n{artifact_context}" if system_prompt else artifact_context

        if phase == FlowPhase.QUESTIONNAIRE:
            from services.questionnaire_service import QuestionnaireService
            trigger_result = QuestionnaireService.should_trigger_questionnaire(project_id, message)
            if trigger_result.get("should_trigger"):
                questionnaire_prompt = QuestionnaireService.get_questionnaire_prompt(project_id, message)
                if questionnaire_prompt:
                    system_prompt = questionnaire_prompt

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
                db=_db, system_prompt=system_prompt,
            )
        else:
            from core.skill_registry import Skill
            temp_skill = Skill.__new__(Skill)
            messages = temp_skill.build_chat_messages(system_prompt, full_conversation, skill_context)

        if intent_result.context.get("key_insights"):
            messages.append({
                "role": "system",
                "content": "关键洞察: " + ", ".join(intent_result.context["key_insights"])
            })

        max_tokens_map = {
            FlowPhase.QISHU: 512,
            FlowPhase.CAIHENG: 1000,
            FlowPhase.ZHENWEI: 1500,
            FlowPhase.CESHU: 1500,
            FlowPhase.NINGMO: 2000,
        }
        max_tokens = max_tokens_map.get(phase, 2048)

        if project_id:
            reminder = self._fact_checker.generate_consistency_reminder(project_id)
            if reminder:
                messages.append({"role": "system", "content": reminder})

        try:
            provider = LLMFactory.get_provider()
            import asyncio
            response = await asyncio.wait_for(
                provider.chat(messages, max_tokens=max_tokens, temperature=0.7),
                timeout=120.0
            )

            if project_id and phase in [FlowPhase.NINGMO, FlowPhase.CESHU]:
                verification = await self._fact_checker.verify_response(
                    project_id, response, conversation_history or ""
                )
                if not verification.is_consistent:
                    response += f"\n\n⚠️ **一致性警告**: " + "; ".join(verification.issues)
                elif verification.warnings:
                    response += f"\n\n💡 **注意**: " + "; ".join(verification.warnings)

            return response
        except ImportError:
            raise
        except Exception as e:
            logger.error(f"Flow response generation failed: {e}")
            return f"Sorry, I encountered an error: {str(e)}"

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
                if artifact.phase in ("qishu", "questionnaire") and artifact.decisions:
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

    def get_flow_status(self, project_id: str) -> Dict[str, Any]:
        self._ensure_loaded(project_id)
        current_phase = self._current_flows.get(project_id, FlowPhase.INTENT_DETECTION)
        flow_state = self._flow_states.get(project_id)

        ctx_status = self._context_manager.get_status(project_id) if project_id else {}

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
            "should_remind": self._response_validator.should_remind_next_phase(
                current_phase, flow_state.conversation_turns if flow_state else 0
            ) if flow_state else False,
        }

    def get_flow_options(self, project_id: str) -> List[Dict[str, Any]]:
        self._ensure_loaded(project_id)
        current_phase = self._current_flows.get(project_id, FlowPhase.INTENT_DETECTION)

        options_map = {
            FlowPhase.INTENT_DETECTION: [
                {"id": "qishu", "label": "头脑风暴", "description": "自由讨论，深入思考需求", "icon": "💭"},
                {"id": "questionnaire", "label": "需求问卷", "description": "系统化收集需求", "icon": "📋"},
                {"id": "ningmo", "label": "生成方案", "description": "直接产出具执行方案", "icon": "📄"},
            ],
            FlowPhase.QISHU: [
                {"id": "questionnaire", "label": "需求问卷", "description": "切换到系统化问卷", "icon": "📋"},
                {"id": "caiheng", "label": "CEO视角", "description": "审视产品价值", "icon": "👔"},
                {"id": "zhenwei", "label": "技术评审", "description": "讨论技术实现", "icon": "⚙️"},
                {"id": "ningmo", "label": "生成方案", "description": "产出具执行方案", "icon": "📄"},
            ],
            FlowPhase.QUESTIONNAIRE: [
                {"id": "caiheng", "label": "CEO视角", "description": "审视产品价值", "icon": "👔"},
                {"id": "zhenwei", "label": "技术评审", "description": "讨论技术实现", "icon": "⚙️"},
                {"id": "ningmo", "label": "生成方案", "description": "产出具执行方案", "icon": "📄"},
            ],
            FlowPhase.CAIHENG: [
                {"id": "zhenwei", "label": "技术评审", "description": "讨论技术实现", "icon": "⚙️"},
                {"id": "ceshu", "label": "实施计划", "description": "分解为任务", "icon": "📝"},
                {"id": "ningmo", "label": "生成方案", "description": "产出具执行方案", "icon": "📄"},
            ],
            FlowPhase.ZHENWEI: [
                {"id": "ceshu", "label": "实施计划", "description": "分解为任务", "icon": "📝"},
                {"id": "ningmo", "label": "生成方案", "description": "产出具执行方案", "icon": "📄"},
            ],
            FlowPhase.CESHU: [
                {"id": "ningmo", "label": "生成方案", "description": "产出具执行方案", "icon": "📄"},
            ],
            FlowPhase.NINGMO: [
                {"id": "restart", "label": "重新开始", "description": "开始新项目", "icon": "🔄"},
            ],
            FlowPhase.COMPLETED: [
                {"id": "qishu", "label": "头脑风暴", "description": "讨论新想法", "icon": "💭"},
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
