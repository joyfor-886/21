import json
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from db.sqlite import Database
from services.project_service import ProjectService
from services.context_manager import ContextManager
from services.flow.service import FlowService
from services.intent_analyzer import IntentAnalyzer
from api.models import FlowChatRequest, FlowChatResponse
from api.dependencies import get_db, get_flow_service, MAX_CONVERSATION_CHARS
from core.errors import SsumaError, ErrorCode

logger = logging.getLogger('Ssuma.FlowAPI')

router = APIRouter(prefix="/flow", tags=["flow"])


@router.post("/chat", response_model=FlowChatResponse)
async def flow_chat(
    req: FlowChatRequest,
    db: Database = Depends(get_db),
    flow_service: FlowService = Depends(get_flow_service),
):
    project_id = ProjectService.ensure_project(req.project_id, req.message, db)

    ProjectService.save_message(project_id, "user", req.message, db=db)

    conversation = ContextManager.build_conversation_string(
        project_id, db=db, max_chars=MAX_CONVERSATION_CHARS
    )

    try:
        result = await flow_service.process_message(
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

        from domain.results import INTENT_LABELS
        from domain.enums import UserIntent
        suggested_action = ""
        try:
            intent_enum = UserIntent(intent)
            suggested_action = f"请提供更多关于{INTENT_LABELS.get(intent_enum, '')}的信息"
        except ValueError:
            pass

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
            suggested_next_action=suggested_action,
            workflow_options=flow_service.get_flow_options(project_id),
            completed=result["current_phase"] == "completed",
            hitl_interrupt=result.get("hitl_interrupt"),
        )
    except Exception as e:
        logger.error(f"Flow chat error: {str(e)}")
        raise SsumaError(ErrorCode.WORKFLOW_ERROR, str(e))


@router.get("/status/{project_id}", response_model=dict)
async def get_flow_status(project_id: str, flow_service: FlowService = Depends(get_flow_service)):
    return flow_service.get_flow_status(project_id)


@router.get("/state/{project_id}", response_model=dict)
async def get_flow_state(
    project_id: str,
    db: Database = Depends(get_db),
    flow_service: FlowService = Depends(get_flow_service),
):
    try:
        flow_status = flow_service.get_flow_status(project_id)
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
async def get_flow_options(project_id: str, flow_service: FlowService = Depends(get_flow_service)):
    return flow_service.get_flow_options(project_id)


@router.post("/switch/{project_id}", response_model=dict)
async def switch_workflow(project_id: str, workflow: str, flow_service: FlowService = Depends(get_flow_service)):
    success = flow_service.switch_workflow(project_id, workflow)
    return {
        "success": success,
        "project_id": project_id,
        "workflow": workflow,
        "new_phase": flow_service.get_flow_status(project_id)["current_phase"],
    }


@router.post("/export/{project_id}", response_model=dict)
async def export_ide_files(project_id: str, flow_service: FlowService = Depends(get_flow_service)):
    """将项目方案导出为 AI IDE（Cursor/Trae/Copilot）可用的项目文件"""
    try:
        result = flow_service.export_ide_files(project_id)

        return {
            "success": True,
            "project_id": project_id,
            "project_name": result["project_name"],
            "complexity": result["complexity"],
            "complexity_label": result["complexity_label"],
            "file_count": result["file_count"],
            "files": {
                path: content
                for path, content in result["files"].items()
            },
        }
    except Exception as e:
        logger.error(f"导出 IDE 文件失败: {str(e)}")
        raise SsumaError(ErrorCode.INTERNAL_ERROR, f"导出失败: {str(e)}")


@router.post("/autopilot/{project_id}", response_model=dict)
async def autopilot_generate(
    project_id: str,
    message: str,
    channel: str = "standard",
):
    """一键自动流水线：输入模糊想法，自动跑完全部阶段并导出 IDE 文件

    流程：qishu → caiheng → zhenwei → ceshu → ningmo → powang → 导出

    Args:
        project_id: 项目 ID
        message: 用户的一句话想法
        channel: 通道（fast=跳过架构审查, standard=完整流程, deep=完整+深度验证）
    """
    try:
        from services.autopilot_service import AutoPilotService

        logger.info(f"启动自动流水线: project={project_id}, channel={channel}")
        result = await AutoPilotService.run(project_id, message, channel)

        return {
            "success": True,
            "project_id": result["project_id"],
            "final_spec": result["final_spec"],
            "file_count": result["file_count"],
            "ide_files": result["ide_files"],
            "phase_summary": result["phase_summary"],
            "total_duration_seconds": result["total_duration_seconds"],
            "quality_score": result["quality_score"],
        }
    except Exception as e:
        logger.error(f"自动流水线失败: {str(e)}")
        raise SsumaError(ErrorCode.WORKFLOW_ERROR, f"自动流水线失败: {str(e)}")


@router.post("/autopilot/stream/{project_id}")
async def autopilot_stream(
    project_id: str,
    message: str,
    channel: str = "standard",
):
    """流式自动流水线 —— 实时展示每个阶段的进度和生成内容"""
    from services.autopilot_service import AutoPilotService

    async def stream_gen():
        async for event in AutoPilotService.run_stream(project_id, message, channel):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        stream_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-API-Key",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
        },
    )


@router.get("/autopilot/status/{project_id}", response_model=dict)
async def autopilot_status(project_id: str):
    """查询自动流水线运行状态"""
    from services.autopilot_service import AutoPilotService
    status = AutoPilotService.get_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail="未找到自动流水线任务")
    return status


@router.post("/autopilot/cancel/{project_id}", response_model=dict)
async def autopilot_cancel(project_id: str):
    """取消正在运行的自动流水线"""
    from services.autopilot_service import AutoPilotService
    cancelled = AutoPilotService.cancel(project_id)
    return {"success": cancelled, "project_id": project_id}


@router.post("/reset/{project_id}", response_model=dict)
async def reset_flow(project_id: str, flow_service: FlowService = Depends(get_flow_service)):
    flow_service.reset_flow(project_id)
    IntentAnalyzer.reset_state(project_id)
    TanyinService.reset_state(project_id)
    return {"success": True, "message": "工作流已重置"}


@router.post("/chat/stream")
async def flow_chat_stream(
    request: FlowChatRequest,
    db: Database = Depends(get_db),
    flow_service: FlowService = Depends(get_flow_service),
):
    async def stream_gen():
        project_id = ProjectService.ensure_project(request.project_id, request.message, db)
        ProjectService.save_message(project_id, "user", request.message, db=db)
        conversation = ContextManager.build_conversation_string(
            project_id, db=db, max_chars=MAX_CONVERSATION_CHARS
        )

        async for chunk_data in flow_service.process_message_stream(
            project_id, request.message, conversation, request.force_workflow, request.attachments
        ):
            yield f"data: {json.dumps(chunk_data)}\n\n"

            if chunk_data.get("done"):
                ProjectService.save_message(
                    project_id, "assistant", chunk_data.get("full_response", ""),
                    skill_used=chunk_data.get("current_phase", ""), db=db
                )

    return StreamingResponse(
        stream_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-API-Key",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
        },
    )
