import json
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from db.sqlite import Database
from services.project_service import ProjectService
from services.context_manager import ContextManager
from services.adaptive_flow import AdaptiveFlowService
from api.models import ChatRequest, ChatResponse
from core.errors import SsumaError, ErrorCode

logger = logging.getLogger('Ssuma.ChatAPI')

router = APIRouter(prefix="", tags=["chat"])

MAX_CONVERSATION_CHARS = 10000


def get_db():
    return Database()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: Database = Depends(get_db)):
    project_id = ProjectService.ensure_project(req.project_id, req.message, db)

    ProjectService.save_message(project_id, "user", req.message, db=db)

    conversation = ContextManager.build_conversation_string(
        project_id, db=db, max_chars=MAX_CONVERSATION_CHARS
    )

    try:
        result = await AdaptiveFlowService.process_message(
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
async def chat_stream(req: ChatRequest, db: Database = Depends(get_db)):
    from core.llm_factory import LLMFactory

    async def stream_gen():
        project_id = ProjectService.ensure_project(req.project_id, req.message, db)

        ProjectService.save_message(project_id, "user", req.message, db=db)

        conversation = ContextManager.build_conversation_string(
            project_id, db=db, max_chars=MAX_CONVERSATION_CHARS
        )

        try:
            provider = LLMFactory.get_provider()
            messages = []
            if conversation:
                messages.append({"role": "system", "content": conversation})
            messages.append({"role": "user", "content": req.message})

            full_response = ""
            async for chunk in provider.chat_stream(messages, max_tokens=4096):
                full_response += chunk
                yield f"data: {json.dumps({'content': chunk})}\n\n"

            ProjectService.save_message(
                project_id, "assistant", full_response, db=db
            )
            yield f"data: {json.dumps({'content': '', 'done': True, 'project_id': project_id})}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            yield f"data: {json.dumps({'content': f'Error: {str(e)}', 'done': True})}\n\n"

    return StreamingResponse(stream_gen(), media_type="text/event-stream")
