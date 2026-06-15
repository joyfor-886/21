"""Human-in-the-Loop (HITL) API — 人工确认端点"""

from fastapi import APIRouter, Request
from typing import Optional, Literal
from pydantic import BaseModel

router = APIRouter(prefix="/hitl", tags=["HITL"])


class HITLResponseRequest(BaseModel):
    """人工响应请求"""
    response_type: Literal["accept", "ignore", "response", "edit"]
    content: Optional[str] = None


@router.get("/pending/{project_id}", response_model=dict)
async def get_pending_interrupt(project_id: str):
    """获取项目的待处理中断"""
    from core.hitl import HITLStore

    interrupt = HITLStore.get_pending_for_project(project_id)
    if not interrupt:
        return {"pending": False, "interrupt": None}

    return {
        "pending": True,
        "interrupt": {
            "id": interrupt.id,
            "phase": interrupt.phase,
            "reason": interrupt.reason,
            "content": interrupt.content,
            "options": interrupt.options,
            "allow_accept": interrupt.allow_accept,
            "allow_ignore": interrupt.allow_ignore,
            "allow_response": interrupt.allow_response,
            "allow_edit": interrupt.allow_edit,
            "created_at": interrupt.created_at,
        },
    }


@router.get("/interrupt/{interrupt_id}", response_model=dict)
async def get_interrupt(interrupt_id: str):
    """获取中断详情"""
    from core.hitl import HITLStore

    interrupt = HITLStore.get_interrupt(interrupt_id)
    if not interrupt:
        return {"found": False}

    return {
        "found": True,
        "interrupt": interrupt.model_dump(),
    }


@router.post("/respond/{interrupt_id}", response_model=dict)
async def respond_to_interrupt(interrupt_id: str, body: HITLResponseRequest):
    """响应中断"""
    from core.hitl import HITLStore

    interrupt = HITLStore.get_interrupt(interrupt_id)
    if not interrupt:
        return {"success": False, "error": "Interrupt not found"}

    if not interrupt.is_pending:
        return {"success": False, "error": f"Interrupt already {interrupt.status}"}

    # 验证响应类型是否允许
    type_allowed = {
        "accept": interrupt.allow_accept,
        "ignore": interrupt.allow_ignore,
        "response": interrupt.allow_response,
        "edit": interrupt.allow_edit,
    }
    if not type_allowed.get(body.response_type, False):
        return {"success": False, "error": f"Response type '{body.response_type}' not allowed"}

    # 记录响应
    interrupt.respond(body.response_type, body.content)
    HITLStore.update_interrupt(interrupt)

    # 根据响应类型处理
    if body.response_type == "accept":
        # 接受 — 继续流程
        return {
            "success": True,
            "action": "continue",
            "message": "已确认，流程继续",
        }
    elif body.response_type == "ignore":
        # 忽略 — 跳过此阶段
        return {
            "success": True,
            "action": "skip",
            "message": "已跳过",
        }
    elif body.response_type == "response":
        # 回复 — 将人工反馈注入下一轮对话
        return {
            "success": True,
            "action": "feedback",
            "message": "反馈已记录",
            "feedback": body.content,
        }
    elif body.response_type == "edit":
        # 编辑 — 修改内容后继续
        return {
            "success": True,
            "action": "edit",
            "message": "修改已记录",
            "edited_content": body.content,
        }

    return {"success": False, "error": "Unknown response type"}


@router.post("/feedback/{project_id}", response_model=dict)
async def submit_hitl_feedback(project_id: str, body: HITLResponseRequest):
    """提交 HITL 反馈并继续流程

    这是一个便捷端点，自动查找项目的待处理中断并响应。
    如果有反馈内容，会将其作为用户消息注入对话。
    """
    from core.hitl import HITLStore

    interrupt = HITLStore.get_pending_for_project(project_id)
    if not interrupt:
        return {"success": False, "error": "No pending interrupt for this project"}

    # 记录响应
    interrupt.respond(body.response_type, body.content)
    HITLStore.update_interrupt(interrupt)

    result = {
        "success": True,
        "interrupt_id": interrupt.id,
        "response_type": body.response_type,
    }

    # 如果是反馈类型，返回需要注入的反馈内容
    if body.response_type == "response" and body.content:
        result["inject_message"] = body.content
    elif body.response_type == "edit" and body.content:
        result["inject_message"] = f"[用户修改]: {body.content}"

    return result


@router.get("/config", response_model=dict)
async def get_hitl_config():
    """获取 HITL 配置"""
    from core.hitl import get_hitl_config

    config = get_hitl_config()
    return {
        "phases": config.phases,
        "mcp_tool_approval": config.mcp_tool_approval,
        "completion_threshold": config.completion_threshold,
        "timeout_seconds": config.timeout_seconds,
    }
