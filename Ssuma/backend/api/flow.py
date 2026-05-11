import json
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from db.sqlite import Database
from services.project_service import ProjectService
from services.context_manager import ContextManager
from services.adaptive_flow import AdaptiveFlowService
from services.intent_analyzer import IntentAnalyzer
from services.questionnaire_service import QuestionnaireService
from api.models import FlowChatRequest, FlowChatResponse
from core.errors import SsumaError, ErrorCode

logger = logging.getLogger('Ssuma.FlowAPI')

router = APIRouter(prefix="/flow", tags=["flow"])

MAX_CONVERSATION_CHARS = 10000


def get_db():
    return Database()


@router.post("/chat", response_model=FlowChatResponse)
async def flow_chat(req: FlowChatRequest, db: Database = Depends(get_db)):
    project_id = ProjectService.ensure_project(req.project_id, req.message, db)

    ProjectService.save_message(project_id, "user", req.message, db=db)

    conversation = ContextManager.build_conversation_string(
        project_id, db=db, max_chars=MAX_CONVERSATION_CHARS
    )

    try:
        result = await AdaptiveFlowService.process_message(
            project_id, req.message, conversation, req.force_workflow, req.attachments
        )
        response_text = result["response"]

        ProjectService.save_message(
            project_id, "assistant", response_text,
            skill_used=result["current_phase"], db=db
        )

        intent = result.get("intent", "")
        clarity = result.get("clarity", "")
        validation = result.get("validation", {})

        intent_action_map = {
            "qishu": "请提供更多关于项目起数的信息",
            "caiheng": "请提供更多关于财衡分析的信息",
            "guihua": "请提供更多关于规划的信息",
            "pinggu": "请提供更多关于评估的信息",
        }

        return FlowChatResponse(
            project_id=project_id,
            response=response_text,
            current_phase=result["current_phase"],
            current_phase_label=result["current_phase"].replace("_", " ").title(),
            intent_analysis={
                "intent": intent,
                "clarity": clarity,
                "confidence": validation.get("score"),
            },
            suggested_next_phase=result.get("suggested_next"),
            suggested_next_action=intent_action_map.get(intent, f"请继续提供关于{intent}的信息" if intent else ""),
            workflow_options=AdaptiveFlowService.get_flow_options(project_id),
            completed=result["current_phase"] == "completed",
        )
    except Exception as e:
        logger.error(f"Flow chat error: {str(e)}")
        raise SsumaError(ErrorCode.WORKFLOW_ERROR, str(e))


@router.get("/status/{project_id}", response_model=dict)
async def get_flow_status(project_id: str):
    return AdaptiveFlowService.get_flow_status(project_id)


@router.get("/state/{project_id}", response_model=dict)
async def get_flow_state(project_id: str, db: Database = Depends(get_db)):
    try:
        flow_status = AdaptiveFlowService.get_flow_status(project_id)
        messages = db.fetchall(
            "SELECT * FROM messages WHERE project_id = ? ORDER BY timestamp ASC",
            (project_id,)
        )
        project = db.fetchone(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,)
        )
        return {
            **flow_status,
            "messages": [dict(msg) for msg in messages],
            "project": dict(project) if project else None,
        }
    except Exception as e:
        logger.error(f"获取工作流状态失败: {str(e)}")
        raise SsumaError(ErrorCode.INTERNAL_ERROR, f"获取状态失败: {str(e)}")


@router.get("/options/{project_id}", response_model=list)
async def get_flow_options(project_id: str):
    return AdaptiveFlowService.get_flow_options(project_id)


@router.post("/switch/{project_id}", response_model=dict)
async def switch_workflow(project_id: str, workflow: str):
    success = AdaptiveFlowService.switch_workflow(project_id, workflow)
    return {
        "success": success,
        "project_id": project_id,
        "workflow": workflow,
        "new_phase": AdaptiveFlowService.get_flow_status(project_id)["current_phase"],
    }


@router.post("/reset/{project_id}", response_model=dict)
async def reset_flow(project_id: str):
    AdaptiveFlowService.reset_flow(project_id)
    IntentAnalyzer.reset_state(project_id)
    QuestionnaireService.reset_state(project_id)
    return {"success": True, "message": "工作流已重置"}


@router.post("/chat/stream")
async def flow_chat_stream(request: FlowChatRequest, db: Database = Depends(get_db)):
    from core.llm_factory import LLMFactory
    from services.flow.service import get_flow_service, FlowService
    from services.flow.router import FlowPhase, WORKFLOW_SYSTEM_PROMPTS
    from services.artifact_store import extract_artifact_from_response
    from services.phase_gates import PhaseCompletionGate
    from services.response_validator import ResponseValidator
    from services.fact_checker import FactChecker
    from services.intent_analyzer import INTENT_LABELS
    from domain.enums import FlowPhase as FlowPhaseEnum

    async def stream_gen():
        project_id = ProjectService.ensure_project(request.project_id, request.message, db)
        ProjectService.save_message(project_id, "user", request.message, db=db)
        conversation = ContextManager.build_conversation_string(
            project_id, db=db, max_chars=MAX_CONVERSATION_CHARS
        )

        flow_service = get_flow_service()
        flow_service._ensure_loaded(project_id)

        current_phase = flow_service._current_flows.get(project_id, FlowPhase.INTENT_DETECTION)
        flow_state = flow_service._get_or_create_flow_state(project_id)

        ctx_window = flow_service._context_manager.get_window(project_id)
        if request.message:
            ctx_window.add_message("user", request.message)

        intent_result = await flow_service._intent_analyzer.analyze(
            project_id, request.message, conversation or "", request.force_workflow
        )

        if flow_state.channel == "standard" and intent_result.context.get("channel"):
            channel = intent_result.context["channel"]
            flow_service._channel_assignments[project_id] = channel
            flow_state.channel = channel

        flow_service._auto_adjust_channel_for_model_tier(project_id)

        next_phase = flow_service._router.determine_next_phase(
            current_phase, intent_result, request.force_workflow,
            flow_service._channel_assignments.get(project_id, "standard"),
            flow_state.phase_completion,
        )
        flow_service._current_flows[project_id] = next_phase

        skill_name = None
        detected_skill = flow_service._skill_registry.detect_skill(request.message)
        if request.force_workflow:
            skill_name = None
        elif detected_skill and next_phase == FlowPhase.INTENT_DETECTION:
            skill_name = detected_skill
        elif detected_skill and detected_skill == next_phase.value:
            skill_name = detected_skill

        artifact_context = flow_service._artifact_store.build_context_for_phase(
            project_id, next_phase.value
        )

        system_prompt = WORKFLOW_SYSTEM_PROMPTS.get(next_phase, "")
        if artifact_context:
            system_prompt = f"{system_prompt}\n\n{artifact_context}" if system_prompt else artifact_context

        messages = flow_service._context_manager.build_llm_messages(
            project_id, request.message, db=db, system_prompt=system_prompt,
        )

        if intent_result.context.get("key_insights"):
            messages.append({
                "role": "system",
                "content": "关键洞察: " + ", ".join(intent_result.context["key_insights"])
            })

        reminder = flow_service._fact_checker.generate_consistency_reminder(project_id)
        if reminder:
            messages.append({"role": "system", "content": reminder})

        try:
            provider = LLMFactory.get_provider()
            full_response = ""
            async for chunk in provider.chat_stream(messages, max_tokens=4096):
                full_response += chunk
                yield f"data: {json.dumps({'content': chunk, 'phase': next_phase.value})}\n\n"

            ctx_window.add_message("assistant", full_response)

            completion_result = flow_service._phase_gate.evaluate(
                next_phase.value, conversation or request.message, flow_state.conversation_turns,
            )
            flow_state.phase_completion[next_phase.value] = completion_result.score

            artifact = await extract_artifact_from_response(
                next_phase.value, full_response, conversation or "", completion_result,
            )
            flow_service._artifact_store.add(project_id, artifact)

            if completion_result.should_advance and next_phase != FlowPhase.NINGMO:
                suggested_next = flow_service._router.get_suggested_next_phase(
                    next_phase, flow_service._channel_assignments.get(project_id, "standard")
                )
                if suggested_next != next_phase:
                    intent_label = INTENT_LABELS.get(
                        flow_service._router.intent_for_phase(suggested_next), suggested_next.value
                    )
                    reminder_text = f"💡 当前阶段讨论已经比较充分（完成度 {completion_result.score:.0%}），可以进入下一阶段：{intent_label}"
                    full_response += f"\n\n{reminder_text}"
                    yield f"data: {json.dumps({'content': reminder_text, 'phase': next_phase.value})}\n\n"

            flow_state.workflow_history.append({
                "phase": next_phase.value,
                "turn": flow_state.conversation_turns,
                "completion_score": completion_result.score,
                "timestamp": __import__('datetime').datetime.now().isoformat(),
            })
            flow_state.conversation_turns += 1
            if next_phase == FlowPhase.NINGMO:
                flow_state.spec_generated = True

            flow_service._save_all_to_repo(project_id)

            ProjectService.save_message(
                project_id, "assistant", full_response,
                skill_used=next_phase.value, db=db
            )

            yield f"data: {json.dumps({
                'content': '',
                'phase': next_phase.value,
                'done': True,
                'project_id': project_id,
                'completion_score': completion_result.score,
                'current_phase': next_phase.value,
                'suggested_next': flow_service._router.get_suggested_next_phase(
                    next_phase, flow_service._channel_assignments.get(project_id, "standard")
                ).value,
                'channel': flow_state.channel,
                'turn': flow_state.conversation_turns,
            })}\n\n"
        except Exception as e:
            logger.error(f"Flow chat stream failed: {str(e)}")
            yield f"data: {json.dumps({'content': f'错误: {str(e)}', 'phase': 'error', 'done': True})}\n\n"

    return StreamingResponse(stream_gen(), media_type="text/event-stream")
