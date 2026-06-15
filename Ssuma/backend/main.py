"""Ssuma Backend - FastAPI Application"""
import os
import json
import hmac
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from core.middleware import RateLimitMiddleware, APIKeyMiddleware, RequestIDMiddleware, RequestBodySizeLimitMiddleware
from core.errors import SsumaError, ERROR_HTTP_STATUS

from db.sqlite import Database
from core.llm_factory import LLMFactory
from core.state_repository import StateRepository
from services.flow.service import FlowService
from services.intent_analyzer import IntentAnalyzer
from services.tanyin_service import TanyinService
from services.project_service import ProjectService
from services.context_manager import ContextManager

from api.wiki import router as wiki_router
from api.chat import router as chat_router
from api.flow import router as flow_router
from api.projects import router as projects_router
from api.generation import router as generation_router
from api.llm_config import router as llm_config_router
from api.feedback import router as feedback_router
from api.orchestrator import router as orchestrator_router
from api.evolution import router as evolution_router
from api.tanyin import router as tanyin_router
from api.voice import router as voice_router
from api.mcp import router as mcp_router
from api.hitl import router as hitl_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ssuma.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('Ssuma')

from skills import register_builtin_skills

_default_cors_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

from core.config import Config
cors_origins = Config().server.get("cors_origins", _default_cors_origins)


@asynccontextmanager
async def lifespan(app: FastAPI):
    register_builtin_skills()
    logger.info("Builtin skills registered")

    db = Database()
    db._init_db()
    app.state.db = db
    logger.info("Database initialized")

    StateRepository.initialize()
    logger.info("StateRepository initialized")

    try:
        LLMFactory.initialize()
        logger.info("LLMFactory initialized")
    except Exception as e:
        logger.warning(f"LLMFactory initialization failed: {e}")

    try:
        from services.context_manager import auto_configure_context_limits
        auto_configure_context_limits()
        logger.info("Context limits auto-configured")
    except Exception as e:
        logger.warning(f"Context auto-configure failed: {e}")

    # 创建 FlowService 实例并存入 app.state
    from services.flow.service import FlowService
    flow_service = FlowService()
    app.state.flow_service = flow_service
    logger.info("FlowService initialized and stored in app.state")

    # 初始化项目记忆表
    try:
        from core.project_memory import ProjectMemoryStore
        ProjectMemoryStore(db).ensure_table()
        logger.info("ProjectMemoryStore table ensured")
    except Exception as e:
        logger.warning(f"ProjectMemoryStore table creation failed: {e}")

    # 初始化 MCP 客户端
    try:
        from core.mcp_client import initialize_mcp
        mcp_config = Config().mcp
        if mcp_config:
            mcp_manager = await initialize_mcp(mcp_config)
            app.state.mcp_manager = mcp_manager
            logger.info("MCP client manager initialized")
        else:
            logger.info("No MCP servers configured")
    except Exception as e:
        logger.warning(f"MCP initialization failed: {e}")

    yield

    # 关闭 MCP 连接
    try:
        from core.mcp_client import shutdown_mcp
        await shutdown_mcp()
        logger.info("MCP connections closed")
    except Exception as e:
        logger.warning(f"MCP shutdown failed: {e}")


app = FastAPI(title="Ssuma API", version="1.0.0", lifespan=lifespan)


@app.exception_handler(SsumaError)
async def ssuma_error_handler(request: Request, exc: SsumaError):
    status_code = ERROR_HTTP_STATUS.get(exc.error_code, 500)
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.error_code.value,
                "message": exc.message,
                "detail": exc.detail_dict,
                **({"request_id": request_id} if request_id else {}),
            }
        },
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)
app.add_middleware(RequestBodySizeLimitMiddleware, max_body_size=10 * 1024 * 1024)
app.add_middleware(APIKeyMiddleware)
app.include_router(wiki_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(flow_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(generation_router, prefix="/api/v1")
app.include_router(llm_config_router, prefix="/api/v1")
app.include_router(feedback_router, prefix="/api/v1")
app.include_router(orchestrator_router, prefix="/api/v1")
app.include_router(evolution_router, prefix="/api/v1")
app.include_router(tanyin_router, prefix="/api/v1")
app.include_router(voice_router, prefix="/api/v1")
app.include_router(mcp_router, prefix="/api/v1")
app.include_router(hitl_router, prefix="/api/v1")


@app.get("/api/v1/health", response_model=dict)
async def health_check(request: Request):
    result = {"status": "ok", "version": "1.0.0", "checks": {}}

    try:
        db = getattr(request.app.state, "db", None) or Database()
        conn = db._get_connection()
        conn.execute("SELECT 1")
        result["checks"]["database"] = {"status": "ok"}
    except Exception as e:
        result["checks"]["database"] = {"status": "error", "detail": str(e)}
        result["status"] = "degraded"

    try:
        providers = LLMFactory.list_providers()
        if providers:
            result["checks"]["llm"] = {"status": "ok", "providers": providers}
        else:
            result["checks"]["llm"] = {"status": "warning", "detail": "No providers configured"}
            result["status"] = "degraded"
    except Exception as e:
        result["checks"]["llm"] = {"status": "error", "detail": str(e)}
        result["status"] = "degraded"

    return result


from core.cache import cache as _cache


@app.get("/api/v1/cache/stats", response_model=dict)
async def cache_stats():
    return _cache.stats()


@app.post("/api/v1/cache/clear", response_model=dict)
async def clear_cache():
    _cache.clear()
    return {"success": True, "message": "Cache cleared"}


@app.get("/api/v1/settings/llm", response_model=dict)
async def get_llm_settings():
    from core.config import Config
    config = Config()
    return config.llm


@app.post("/api/v1/config/reload", response_model=dict)
async def reload_config():
    from core.config import Config
    Config.reload()
    logger.info("Configuration reloaded")
    return {"success": True, "message": "Configuration reloaded"}


@app.get("/api/health", response_model=dict, include_in_schema=False)
async def health_check_legacy():
    return {"status": "ok", "version": "1.0.0", "deprecated": True, "new_path": "/api/v1/health"}


@app.get("/api/cache/stats", response_model=dict, include_in_schema=False)
async def cache_stats_legacy():
    return _cache.stats()


@app.post("/api/cache/clear", response_model=dict, include_in_schema=False)
async def clear_cache_legacy():
    _cache.clear()
    return {"success": True, "message": "Cache cleared"}


@app.websocket("/ws/chat/{project_id}")
async def websocket_chat_legacy(websocket: WebSocket, project_id: str):
    await websocket.accept()
    await websocket.send_json({
        "type": "error",
        "message": "Deprecated endpoint. Use /ws/v1/chat/{project_id}"
    })
    await websocket.close()


MAX_MESSAGE_LENGTH = 10000


@app.websocket("/ws/v1/chat/{project_id}")
async def websocket_chat(websocket: WebSocket, project_id: str):
    api_key = os.environ.get("SSUMA_API_KEY", "")
    if not api_key:
        try:
            from core.config import Config
            api_key = Config().storage.get("api_key", "")
        except Exception:
            pass
    if api_key:
        provided = websocket.query_params.get("api_key", "")
        if not provided:
            for header_name, header_value in websocket.headers.items():
                if header_name.lower() in ("x-api-key", "authorization"):
                    provided = header_value
                    if header_name.lower() == "authorization" and provided.startswith("Bearer "):
                        provided = provided[7:]
                    break
        if not hmac.compare_digest(provided, api_key):
            await websocket.close(code=4001, reason="Unauthorized")
            return

    await websocket.accept()
    last_ping = asyncio.get_event_loop().time()

    async def heartbeat():
        nonlocal last_ping
        while True:
            await asyncio.sleep(30)
            try:
                await websocket.send_json({"type": "ping"})
                last_ping = asyncio.get_event_loop().time()
            except Exception:
                break

    heartbeat_task = asyncio.create_task(heartbeat())

    db = getattr(websocket.app.state, "db", None) or Database()

    try:
        while True:
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            if message_data.get("type") == "pong":
                last_ping = asyncio.get_event_loop().time()
                continue

            message = message_data.get("message", "")
            force_workflow = message_data.get("force_workflow")
            attachments = message_data.get("attachments")

            if not message:
                continue

            if len(message) > MAX_MESSAGE_LENGTH:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Message too long. Maximum length is {MAX_MESSAGE_LENGTH} characters."
                })
                continue

            ProjectService.save_message(project_id, "user", message, db=db)

            conversation = ContextManager.build_conversation_string(
                project_id, db=db, max_chars=10000
            )

            # 使用新 FlowService + 流式输出
            flow_service = getattr(websocket.app.state, "flow_service", None)
            if not flow_service:
                from services.flow.service import FlowService
                flow_service = FlowService()

            full_response = ""
            final_data = {}

            async for chunk in flow_service.process_message_stream(
                project_id, message, conversation, force_workflow, attachments
            ):
                if chunk.get("content"):
                    await websocket.send_json({
                        "type": "chunk",
                        "content": chunk["content"],
                        "phase": chunk.get("phase", ""),
                    })
                    full_response += chunk["content"]

                if chunk.get("done"):
                    final_data = chunk

            # 发送完成消息
            await websocket.send_json({
                "type": "message",
                "response": full_response,
                "phase": final_data.get("current_phase", final_data.get("phase", "")),
                "project_id": project_id,
                "completion_score": final_data.get("completion_score", 0),
                "suggested_next": final_data.get("suggested_next", ""),
                "channel": final_data.get("channel", "standard"),
                "intent": final_data.get("intent", ""),
                "detected_skill": final_data.get("detected_skill"),
                "hitl_interrupt": final_data.get("hitl_interrupt"),
            })

            ProjectService.save_message(
                project_id, "assistant", full_response,
                skill_used=final_data.get("current_phase", ""), db=db
            )
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for project {project_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        heartbeat_task.cancel()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
