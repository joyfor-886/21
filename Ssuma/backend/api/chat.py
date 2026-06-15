import json
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from db.sqlite import Database
from services.project_service import ProjectService
from services.context_manager import ContextManager
from services.flow.service import FlowService
from api.models import ChatRequest, ChatResponse
from api.dependencies import get_db, get_flow_service, MAX_CONVERSATION_CHARS
from core.errors import SsumaError, ErrorCode

logger = logging.getLogger('Ssuma.ChatAPI')

router = APIRouter(prefix="", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
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
            project_id, req.message, conversation, None, req.attachments
        )
        response_text = result["response"]
        current_phase = result["current_phase"]

        ProjectService.save_message(
            project_id, "assistant", response_text,
            skill_used=current_phase, db=db
        )

        return ChatResponse(
            project_id=project_id,
            response=response_text,
            phase=current_phase,
            intent_analysis=result.get("intent_analysis", {}),
            suggested_next_action=result.get("suggested_next_action", "")
        )
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise SsumaError(ErrorCode.LLM_UNAVAILABLE, str(e))


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    db: Database = Depends(get_db),
    flow_service: FlowService = Depends(get_flow_service),
):
    async def stream_gen():
        project_id = ProjectService.ensure_project(req.project_id, req.message, db)

        ProjectService.save_message(project_id, "user", req.message, db=db)

        conversation = ContextManager.build_conversation_string(
            project_id, db=db, max_chars=MAX_CONVERSATION_CHARS
        )

        try:
            async for chunk_data in flow_service.process_message_stream(
                project_id, req.message, conversation, req.force_workflow, req.attachments
            ):
                yield f"data: {json.dumps(chunk_data)}\n\n"

                if chunk_data.get("done"):
                    ProjectService.save_message(
                        project_id, "assistant", chunk_data.get("full_response", ""),
                        skill_used=chunk_data.get("current_phase", ""), db=db
                    )
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            yield f"data: {json.dumps({'content': f'Error: {str(e)}', 'done': True})}\n\n"

    return StreamingResponse(stream_gen(), media_type="text/event-stream")
