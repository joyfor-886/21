"""MCP (Model Context Protocol) 管理 API"""

from fastapi import APIRouter, Request, Depends
from typing import Optional

from api.dependencies import get_db

router = APIRouter(prefix="/mcp", tags=["MCP"])


@router.get("/status", response_model=dict)
async def get_mcp_status(request: Request):
    """获取 MCP 服务器状态"""
    from core.mcp_client import get_mcp_manager

    manager = get_mcp_manager()
    if not manager:
        return {"connected": False, "servers": [], "tools_count": 0}

    server_status = manager.get_server_status()
    tools = await manager.list_tools()

    # 将 Dict 转为 Array 格式，方便前端消费
    servers_list = []
    for name, info in server_status.items():
        server_tools = await manager.list_tools(server_name=name)
        servers_list.append({
            "name": name,
            "status": "connected" if info.get("connected") else "disconnected",
            "type": info.get("type", ""),
            "tools_count": len(server_tools),
            "description": info.get("description", ""),
        })

    return {
        "connected": manager.is_connected,
        "servers": servers_list,
        "tools_count": len(tools),
    }


@router.get("/servers", response_model=dict)
async def list_mcp_servers(request: Request):
    """列出所有 MCP 服务器配置"""
    from core.mcp_client import get_mcp_manager

    manager = get_mcp_manager()
    if not manager:
        return {"servers": {}}

    return {"servers": manager.get_server_status()}


@router.get("/tools", response_model=dict)
async def list_mcp_tools(
    request: Request,
    server: Optional[str] = None,
):
    """列出可用的 MCP 工具"""
    from core.mcp_client import get_mcp_manager

    manager = get_mcp_manager()
    if not manager:
        return {"tools": [], "error": "MCP not initialized"}

    try:
        tools = await manager.list_tools(server_name=server)
        return {
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "server": t.server_name,
                    "input_schema": t.input_schema,
                }
                for t in tools
            ],
        }
    except Exception as e:
        return {"tools": [], "error": str(e)}


@router.post("/tools/call", response_model=dict)
async def call_mcp_tool(request: Request):
    """调用 MCP 工具"""
    body = await request.json()
    tool_name = body.get("tool_name", "")
    arguments = body.get("arguments", {})
    server_name = body.get("server_name")

    if not tool_name:
        return {"success": False, "error": "tool_name is required"}

    from core.mcp_client import get_mcp_manager

    manager = get_mcp_manager()
    if not manager:
        return {"success": False, "error": "MCP not initialized"}

    result = await manager.call_tool(tool_name, arguments, server_name)

    return {
        "success": not result.is_error,
        "tool_name": result.tool_name,
        "server_name": result.server_name,
        "content": result.content,
        "error": result.error_message if result.is_error else None,
    }


@router.post("/refresh", response_model=dict)
async def refresh_mcp_tools(request: Request):
    """刷新 MCP 工具缓存"""
    from core.mcp_client import get_mcp_manager

    manager = get_mcp_manager()
    if not manager:
        return {"success": False, "error": "MCP not initialized"}

    manager.invalidate_cache()
    tools = await manager.list_tools()

    return {"success": True, "tools_count": len(tools)}


@router.post("/reconnect", response_model=dict)
async def reconnect_mcp_servers(request: Request):
    """重新连接所有 MCP 服务器"""
    from core.mcp_client import get_mcp_manager, initialize_mcp
    from core.config import Config

    # 先断开
    manager = get_mcp_manager()
    if manager:
        await manager.disconnect_all()

    # 重新初始化
    mcp_config = Config().mcp
    if mcp_config:
        new_manager = await initialize_mcp(mcp_config)
        request.app.state.mcp_manager = new_manager
        tools = await new_manager.list_tools()
        return {
            "success": True,
            "servers": new_manager.get_server_status(),
            "tools_count": len(tools),
        }

    return {"success": False, "error": "No MCP configuration found"}
