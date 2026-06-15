"""Flow 中间件链 — 参考 Agno Capability 设计

将 process_message_stream 中的硬编码步骤拆分为可插拔的中间件。
每个中间件可以：
  - 在处理前修改上下文（pre-process）
  - 在处理后修改结果（post-process）
  - 短路返回（skip remaining middleware）

中间件执行顺序：
  Pre-generation（生成前）:
    1. MemoryContextMiddleware — 加载项目记忆卡上下文
    2. IdentityMiddleware     — 身份识别短路
    3. IntentMiddleware       — 意图分析
    4. ChannelMiddleware      — 通道调整
    5. RoutingMiddleware      — 阶段路由 + 技能检测

  Generation（流式生成，由 process_message_stream 直接控制）

  Post-generation（生成后）:
    6. EvaluationMiddleware   — 完成度评估 + artifact 提取
    7. ReflexionMiddleware    — 反思循环（凝墨阶段）
    8. ReminderMiddleware     — 提醒追加
    9. PostProcessMiddleware  — 记忆卡更新 + 进化引擎触发
"""

from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
import logging
import asyncio

logger = logging.getLogger('Ssuma.Middleware')


@dataclass
class FlowContext:
    """中间件共享上下文 — 在中间件链中传递"""
    project_id: str
    message: str
    conversation: str = ""
    force_workflow: Optional[str] = None
    attachments: Optional[List[dict]] = None

    # 中间件填充的字段
    current_phase: Optional[str] = None
    next_phase: Optional[str] = None
    intent_result: Optional[Any] = None
    skill_name: Optional[str] = None
    artifact_context: str = ""
    response_text: str = ""
    full_response: str = ""
    completion_result: Optional[Any] = None
    validation_result: Optional[Any] = None
    artifact: Optional[Any] = None

    # 记忆上下文（MemoryContextMiddleware 填充）
    memory_context: str = ""

    # MCP 工具上下文（RoutingMiddleware 填充）
    mcp_tools_context: str = ""

    # 流式输出 chunks（由 process_message_stream 填充）
    stream_chunks: List[str] = field(default_factory=list)

    # 短路标志
    short_circuited: bool = False
    short_circuit_response: str = ""

    # 提醒文本（ReminderMiddleware 填充）
    reminder_text: str = ""

    # MCP 工具调用结果（MCPToolCallMiddleware 填充）
    mcp_tool_results: List[str] = field(default_factory=list)

    # HITL 中断（HITLMiddleware 填充）
    hitl_interrupt: Optional[Any] = None


class FlowMiddleware:
    """中间件基类"""

    async def pre_process(self, ctx: FlowContext, service) -> bool:
        """前置处理。返回 False 表示短路，跳过后续中间件。"""
        return True

    async def post_process(self, ctx: FlowContext, service) -> None:
        """后置处理。在所有中间件 pre_process 完成后逆序执行。"""
        pass


# ===== Pre-generation 中间件 =====


class MemoryContextMiddleware(FlowMiddleware):
    """加载项目记忆卡上下文 — 跨会话记忆注入"""

    async def pre_process(self, ctx: FlowContext, service) -> bool:
        try:
            memory_card = service._memory_store.get(ctx.project_id)
            if memory_card and (memory_card.requirement_summary or memory_card.tech_decisions):
                ctx.memory_context = memory_card.to_context_string()
        except Exception:
            pass
        return True


class IdentityMiddleware(FlowMiddleware):
    """身份识别 — 问"你是谁"时短路返回"""

    async def pre_process(self, ctx: FlowContext, service) -> bool:
        identity_response = service._check_identity_question(ctx.message)
        if identity_response:
            ctx.short_circuited = True
            ctx.short_circuit_response = identity_response
            return False
        return True


class IntentMiddleware(FlowMiddleware):
    """意图分析"""

    async def pre_process(self, ctx: FlowContext, service) -> bool:
        ctx.intent_result = await service._intent_analyzer.analyze(
            ctx.project_id, ctx.message, ctx.conversation, ctx.force_workflow
        )
        return True


class ChannelMiddleware(FlowMiddleware):
    """通道调整"""

    async def pre_process(self, ctx: FlowContext, service) -> bool:
        flow_state = service._get_or_create_flow_state(ctx.project_id)

        if flow_state.channel == "standard" and ctx.intent_result and ctx.intent_result.context.get("channel"):
            channel = ctx.intent_result.context["channel"]
            service._channel_assignments[ctx.project_id] = channel
            flow_state.channel = channel

        service._auto_adjust_channel_for_model_tier(ctx.project_id)
        return True


class RoutingMiddleware(FlowMiddleware):
    """阶段路由 + 技能检测 + MCP 工具上下文注入"""

    async def pre_process(self, ctx: FlowContext, service) -> bool:
        from domain.enums import FlowPhase

        current_phase = service._current_flows.get(ctx.project_id, FlowPhase.INTENT_DETECTION)
        ctx.current_phase = current_phase.value

        next_phase = service._router.determine_next_phase(
            current_phase, ctx.intent_result, ctx.force_workflow,
            service._channel_assignments.get(ctx.project_id, "standard"),
            service._get_or_create_flow_state(ctx.project_id).phase_completion,
        )
        service._current_flows[ctx.project_id] = next_phase
        ctx.next_phase = next_phase.value

        # 技能检测
        detected_skill = service._skill_registry.detect_skill(ctx.message)
        skill_name = None
        if ctx.force_workflow:
            skill_name = None
        elif detected_skill and next_phase == FlowPhase.INTENT_DETECTION:
            skill_name = detected_skill
        elif detected_skill and detected_skill == next_phase.value:
            skill_name = detected_skill
        ctx.skill_name = skill_name

        # artifact 上下文
        ctx.artifact_context = service._artifact_store.build_context_for_phase(
            ctx.project_id, next_phase.value
        )

        # MCP 工具上下文注入 — 让 LLM 知道可用的外部工具
        try:
            from core.mcp_client import get_mcp_manager
            mcp_manager = get_mcp_manager()
            if mcp_manager and mcp_manager.is_connected:
                mcp_tools = await mcp_manager.list_tools()
                if mcp_tools:
                    tool_descriptions = []
                    for tool in mcp_tools:
                        params_desc = ""
                        schema = tool.input_schema
                        if schema and "properties" in schema:
                            props = schema["properties"]
                            required = schema.get("required", [])
                            param_parts = []
                            for pname, pdef in props.items():
                                req_mark = "*" if pname in required else ""
                                ptype = pdef.get("type", "any")
                                pdesc = pdef.get("description", "")
                                param_parts.append(f"  - {pname}{req_mark} ({ptype}): {pdesc}")
                            params_desc = "\n".join(param_parts)
                        tool_descriptions.append(
                            f"### {tool.name} (来源: {tool.server_name})\n{tool.description}\n参数:\n{params_desc}"
                        )
                    ctx.mcp_tools_context = "\n\n".join(tool_descriptions)
        except Exception:
            pass

        return True


# ===== Post-generation 中间件 =====


class EvaluationMiddleware(FlowMiddleware):
    """完成度评估 + artifact 提取 + 流程状态更新"""

    async def post_process(self, ctx: FlowContext, service) -> None:
        from domain.enums import FlowPhase

        next_phase_value = ctx.next_phase or "intent_detection"
        flow_state = service._get_or_create_flow_state(ctx.project_id)

        # 保存助手消息到上下文窗口
        ctx_window = service._context_manager.get_window(ctx.project_id)
        ctx_window.add_message("assistant", ctx.full_response)

        # 完成度评估
        completion_result = service._phase_gate.evaluate(
            next_phase_value, ctx.conversation or ctx.message, flow_state.conversation_turns,
        )
        flow_state.phase_completion[next_phase_value] = completion_result.score
        ctx.completion_result = completion_result

        # artifact 提取
        artifact = await extract_artifact_from_response(
            next_phase_value, ctx.full_response, ctx.conversation, completion_result,
        )
        service._artifact_store.add(ctx.project_id, artifact)
        ctx.artifact = artifact

        # 验证
        try:
            phase_enum = FlowPhase(next_phase_value)
        except ValueError:
            phase_enum = FlowPhase.INTENT_DETECTION
        ctx.validation_result = service._response_validator.validate(ctx.full_response, phase_enum)

        # 更新流程状态
        flow_state.workflow_history.append({
            "phase": next_phase_value,
            "turn": flow_state.conversation_turns,
            "completion_score": completion_result.score,
            "timestamp": __import__('datetime').datetime.now().isoformat(),
        })
        flow_state.conversation_turns += 1
        if next_phase_value == FlowPhase.NINGMO.value:
            flow_state.spec_generated = True

        service._save_all_to_repo(ctx.project_id)


class HITLMiddleware(FlowMiddleware):
    """Human-in-the-Loop — 关键阶段暂停等待人工确认

    在裁衡、甄微、凝墨等关键决策点，如果完成度超过阈值，
    创建 HumanInterrupt 记录并标记流程暂停。

    暂停不会阻塞服务器，而是将中断信息返回给前端，
    前端展示确认界面，用户操作后通过 API 恢复流程。
    """

    async def post_process(self, ctx: FlowContext, service) -> None:
        from core.hitl import get_hitl_decider, HITLStore, HumanInterrupt

        next_phase_value = ctx.next_phase or "intent_detection"
        completion_score = ctx.completion_result.score if ctx.completion_result else 0.0

        # 检查是否有 MCP 工具调用
        is_mcp_tool_call = bool(ctx.mcp_tool_results)

        decider = get_hitl_decider()
        reason = decider.should_interrupt(next_phase_value, completion_score, is_mcp_tool_call)

        if not reason:
            return

        # 创建中断记录
        interrupt = HumanInterrupt(
            project_id=ctx.project_id,
            phase=next_phase_value,
            reason=reason,
            content=ctx.full_response[:500],
            options=decider.get_interrupt_options(next_phase_value),
            flow_context_snapshot={
                "next_phase": ctx.next_phase,
                "current_phase": ctx.current_phase,
                "completion_score": completion_score,
                "full_response_length": len(ctx.full_response),
            },
        )

        HITLStore.save_interrupt(interrupt)
        ctx.hitl_interrupt = interrupt
        logger.info(f"HITL interrupt created: {interrupt.id} for phase {next_phase_value}")


class ReflexionMiddleware(FlowMiddleware):
    """反思循环 — 凝墨阶段自检"""

    async def post_process(self, ctx: FlowContext, service) -> None:
        from domain.enums import FlowPhase

        next_phase_value = ctx.next_phase or "intent_detection"
        try:
            next_phase = FlowPhase(next_phase_value)
        except ValueError:
            return

        if next_phase != FlowPhase.NINGMO or len(ctx.full_response) <= 200:
            return

        try:
            from services.reflexion import reflexion_loop
            ningmo_dims = {
                "product_definition": "产品核心问题和切入点",
                "architecture_design": "架构设计和数据模型",
                "risk_mitigation": "风险缓解策略",
                "execution_plan": "执行步骤和TDD计划",
            }
            reflexion_result = await reflexion_loop(
                initial_output=ctx.full_response,
                phase="ningmo",
                conversation=ctx.conversation,
                llm_provider=service._get_llm_provider(),
                max_rounds=1,
                phase_dimensions=ningmo_dims,
            )
            if reflexion_result.improved:
                ctx.full_response = reflexion_result.final_output
                logger.info(f"Reflexion improved ningmo output (rounds={reflexion_result.rounds})")
        except Exception as e:
            logger.warning(f"Reflexion loop failed: {e}")


class ReminderMiddleware(FlowMiddleware):
    """提醒追加"""

    async def post_process(self, ctx: FlowContext, service) -> None:
        from domain.enums import FlowPhase

        next_phase_value = ctx.next_phase or "intent_detection"
        flow_state = service._get_or_create_flow_state(ctx.project_id)

        try:
            next_phase = FlowPhase(next_phase_value)
        except ValueError:
            return

        reminder_text = ""

        if ctx.completion_result and ctx.completion_result.should_advance and next_phase != FlowPhase.NINGMO:
            suggested_next = service._router.get_suggested_next_phase(
                next_phase, service._channel_assignments.get(ctx.project_id, "standard")
            )
            if suggested_next != next_phase:
                intent_label = INTENT_LABELS.get(
                    service._router.intent_for_phase(suggested_next), suggested_next.value
                )
                reminder_text = f"💡 当前阶段讨论已经比较充分（完成度 {ctx.completion_result.score:.0%}），可以进入下一阶段：{intent_label}"
        elif service._response_validator.should_remind_next_phase(
            next_phase, flow_state.conversation_turns
        ):
            if ctx.completion_result and not ctx.completion_result.should_advance and ctx.completion_result.next_questions:
                question = ctx.completion_result.next_questions[0]
                reminder_text = f"💡 我们还需要深入一个方面：{question}"
            else:
                reminder_text = service._response_validator.generate_reminder(next_phase)

        if reminder_text:
            ctx.full_response += f"\n\n{reminder_text}"
            ctx.reminder_text = reminder_text


class PostProcessMiddleware(FlowMiddleware):
    """后处理 — 记忆卡更新 + 进化引擎触发"""

    async def post_process(self, ctx: FlowContext, service) -> None:
        from domain.enums import FlowPhase

        next_phase_value = ctx.next_phase or "intent_detection"
        flow_state = service._get_or_create_flow_state(ctx.project_id)

        # 更新项目记忆卡（第二层记忆）
        try:
            memory_card = service._memory_store.get(ctx.project_id)
            memory_card.update_from_artifact(next_phase_value, {
                "summary": ctx.full_response[:200],
                "decisions": ctx.completion_result.dimensions_covered if ctx.completion_result else [],
                "open_questions": ctx.completion_result.dimensions_missing if ctx.completion_result else [],
                "commitments": [],
                "key_insights": ctx.intent_result.context.get("key_insights", []) if ctx.intent_result else [],
                "completion_score": ctx.completion_result.score if ctx.completion_result else 0.0,
            })
            memory_card.channel = flow_state.channel
            memory_card.last_phase = next_phase_value
            memory_card.total_turns = flow_state.conversation_turns
            service._memory_store.save(memory_card)
        except Exception as e:
            logger.warning(f"Failed to update memory card: {e}")

        # 触发进化引擎（第三层记忆）— 仅在完成度较高时
        if ctx.completion_result and ctx.completion_result.score >= 0.7:
            try:
                from services.evolution_engine import SelfEvolutionEngine
                SelfEvolutionEngine.reflect_and_tune(
                    project_id=ctx.project_id,
                    phase_scores=flow_state.phase_completion,
                    total_turns=flow_state.conversation_turns,
                    channel=flow_state.channel,
                )
            except Exception as e:
                logger.warning(f"Evolution engine failed: {e}")


class MCPToolCallMiddleware(FlowMiddleware):
    """MCP 工具调用解析与执行

    解析 LLM 输出中的 ```tool_call``` 块，调用对应的 MCP 工具，
    并将结果追加到回复中。
    """

    async def post_process(self, ctx: FlowContext, service) -> None:
        import json
        import re

        if not ctx.mcp_tools_context:
            return  # 没有 MCP 工具可用，跳过

        # 解析 tool_call 块
        pattern = r'```tool_call\s*\n(.*?)```'
        matches = re.findall(pattern, ctx.full_response, re.DOTALL)

        if not matches:
            return  # 没有工具调用

        try:
            from core.mcp_client import get_mcp_manager
            mcp_manager = get_mcp_manager()
            if not mcp_manager or not mcp_manager.is_connected:
                return
        except Exception:
            return

        tool_results = []
        for match in matches:
            try:
                call_spec = json.loads(match.strip())
                tool_name = call_spec.get("tool", "")
                arguments = call_spec.get("arguments", {})

                if not tool_name:
                    continue

                result = await mcp_manager.call_tool(tool_name, arguments)

                if result.is_error:
                    tool_results.append(
                        f"**工具调用失败: {tool_name}**\n错误: {result.error_message}"
                    )
                else:
                    result_text = "\n".join(
                        item.get("text", str(item))
                        for item in result.content
                        if item.get("type") == "text"
                    )
                    tool_results.append(
                        f"**工具调用结果: {tool_name}**\n{result_text}"
                    )
            except json.JSONDecodeError:
                tool_results.append(f"**工具调用格式错误**\n无法解析: {match.strip()[:100]}")
            except Exception as e:
                tool_results.append(f"**工具调用异常**\n{str(e)}")

        if tool_results:
            results_section = "\n\n---\n\n".join(tool_results)
            ctx.full_response += f"\n\n---\n\n🔧 **MCP 工具执行结果**\n\n{results_section}"
            ctx.mcp_tool_results = tool_results


# ===== 中间件链配置 =====

# Pre-generation 中间件（在 LLM 生成前执行）
PRE_GENERATION_MIDDLEWARES = [
    MemoryContextMiddleware,
    IdentityMiddleware,
    IntentMiddleware,
    ChannelMiddleware,
    RoutingMiddleware,
]

# Post-generation 中间件（在 LLM 生成后执行，逆序 post_process）
POST_GENERATION_MIDDLEWARES = [
    EvaluationMiddleware,
    HITLMiddleware,
    ReflexionMiddleware,
    MCPToolCallMiddleware,
    ReminderMiddleware,
    PostProcessMiddleware,
]


def build_middleware_chain(middleware_classes: List[type]) -> List[FlowMiddleware]:
    """从类列表构建中间件实例链"""
    return [cls() for cls in middleware_classes]


# 延迟导入，避免循环依赖
from domain.results import INTENT_LABELS
from services.artifact_store import extract_artifact_from_response
