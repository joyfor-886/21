"""MCP (Model Context Protocol) 客户端管理器

参考 DeerFlow 的 MCP 集成和 Pydantic AI 的 MCPToolset 设计，
为 Ssuma 提供 MCP 服务器连接、工具发现和调用能力。

架构：
  MCPConfig       — 配置管理（从 config.yaml 加载 MCP 服务器定义）
  MCPClientManager — 客户端生命周期管理（连接/断开/重连）
  MCPToolRegistry  — 工具注册表（发现/缓存/调用 MCP 工具）
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

logger = logging.getLogger('Ssuma.MCP')


# ===== 配置模型 =====


class McpServerConfig(BaseModel):
    """单个 MCP 服务器配置"""
    enabled: bool = True
    type: str = "stdio"  # stdio | sse | http
    # stdio 模式
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    # http/sse 模式
    url: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    # 通用
    description: str = ""
    timeout: int = 30  # 秒


class MCPConfig(BaseModel):
    """MCP 全局配置"""
    servers: Dict[str, McpServerConfig] = Field(default_factory=dict)

    @classmethod
    def from_yaml_config(cls, config_dict: Dict[str, Any]) -> "MCPConfig":
        """从 config.yaml 的 mcp 段解析"""
        servers = {}
        for name, server_conf in config_dict.items():
            if isinstance(server_conf, dict):
                servers[name] = McpServerConfig(**server_conf)
        return cls(servers=servers)

    def get_enabled_servers(self) -> Dict[str, McpServerConfig]:
        """获取所有启用的服务器"""
        return {k: v for k, v in self.servers.items() if v.enabled}


# ===== 工具模型 =====


class MCPToolSchema(BaseModel):
    """MCP 工具的 Schema 定义"""
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    server_name: str = ""  # 来源服务器


class MCPToolResult(BaseModel):
    """MCP 工具调用结果"""
    tool_name: str
    server_name: str
    content: List[Dict[str, Any]] = Field(default_factory=list)
    is_error: bool = False
    error_message: str = ""


# ===== 客户端管理器 =====


class MCPClientManager:
    """MCP 客户端生命周期管理

    职责：
    1. 管理与 MCP 服务器的连接（stdio/SSE/HTTP）
    2. 工具发现（list_tools）
    3. 工具调用（call_tool）
    4. 连接池与会话管理
    """

    def __init__(self, config: MCPConfig):
        self._config = config
        self._sessions: Dict[str, Any] = {}  # server_name -> session
        self._exit_stacks: Dict[str, Any] = {}  # server_name -> AsyncExitStack
        self._tool_cache: Dict[str, List[MCPToolSchema]] = {}
        self._tool_cache_time: Dict[str, float] = {}
        self._cache_ttl = 300  # 5 分钟缓存
        self._connected = False

    async def connect_all(self) -> Dict[str, bool]:
        """连接所有启用的 MCP 服务器"""
        results = {}
        enabled = self._config.get_enabled_servers()

        for name, conf in enabled.items():
            try:
                await self._connect_server(name, conf)
                results[name] = True
                logger.info(f"MCP server '{name}' connected successfully")
            except Exception as e:
                results[name] = False
                logger.warning(f"MCP server '{name}' connection failed: {e}")

        self._connected = any(results.values())
        return results

    async def _connect_server(self, name: str, conf: McpServerConfig):
        """连接单个 MCP 服务器"""
        from contextlib import AsyncExitStack
        from mcp.client.session import ClientSession

        exit_stack = AsyncExitStack()

        if conf.type == "stdio":
            from mcp.client.stdio import StdioServerParameters, stdio_client

            server_params = StdioServerParameters(
                command=conf.command,
                args=conf.args,
                env=conf.env or None,
            )
            read_stream, write_stream = await exit_stack.enter_async_context(
                stdio_client(server_params)
            )
        elif conf.type in ("sse", "http"):
            from mcp.client.sse import sse_client
            from mcp.client.streamable_http import streamable_http_client

            if conf.type == "sse":
                read_stream, write_stream = await exit_stack.enter_async_context(
                    sse_client(conf.url, headers=conf.headers)
                )
            else:
                read_stream, write_stream = await exit_stack.enter_async_context(
                    streamable_http_client(conf.url, headers=conf.headers)
                )
        else:
            raise ValueError(f"Unsupported transport type: {conf.type}")

        session = await exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()

        self._sessions[name] = session
        self._exit_stacks[name] = exit_stack

    async def disconnect_all(self):
        """断开所有 MCP 服务器连接"""
        for name, stack in self._exit_stacks.items():
            try:
                await stack.aclose()
                logger.info(f"MCP server '{name}' disconnected")
            except Exception as e:
                logger.warning(f"MCP server '{name}' disconnect error: {e}")

        self._sessions.clear()
        self._exit_stacks.clear()
        self._connected = False

    async def list_tools(self, server_name: Optional[str] = None) -> List[MCPToolSchema]:
        """列出可用工具

        Args:
            server_name: 指定服务器名，None 则列出所有服务器的工具
        """
        if server_name:
            return await self._list_server_tools(server_name)

        all_tools = []
        for name in self._sessions:
            tools = await self._list_server_tools(name)
            all_tools.extend(tools)
        return all_tools

    async def _list_server_tools(self, server_name: str) -> List[MCPToolSchema]:
        """列出单个服务器的工具（带缓存）"""
        now = time.time()
        cached_time = self._tool_cache_time.get(server_name, 0)

        if server_name in self._tool_cache and (now - cached_time) < self._cache_ttl:
            return self._tool_cache[server_name]

        session = self._sessions.get(server_name)
        if not session:
            return []

        try:
            result = await session.list_tools()
            tools = [
                MCPToolSchema(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=tool.inputSchema or {},
                    server_name=server_name,
                )
                for tool in result.tools
            ]
            self._tool_cache[server_name] = tools
            self._tool_cache_time[server_name] = now
            return tools
        except Exception as e:
            logger.warning(f"Failed to list tools from '{server_name}': {e}")
            return self._tool_cache.get(server_name, [])

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        server_name: Optional[str] = None,
    ) -> MCPToolResult:
        """调用 MCP 工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数
            server_name: 指定服务器（如果工具名跨服务器重复则需要指定）
        """
        # 如果未指定服务器，自动查找
        if not server_name:
            server_name = await self._find_tool_server(tool_name)

        if not server_name:
            return MCPToolResult(
                tool_name=tool_name,
                server_name="",
                is_error=True,
                error_message=f"Tool '{tool_name}' not found in any connected server",
            )

        session = self._sessions.get(server_name)
        if not session:
            return MCPToolResult(
                tool_name=tool_name,
                server_name=server_name,
                is_error=True,
                error_message=f"Server '{server_name}' not connected",
            )

        try:
            result = await session.call_tool(tool_name, arguments)
            content = []
            for item in result.content:
                if hasattr(item, "text"):
                    content.append({"type": "text", "text": item.text})
                elif hasattr(item, "data"):
                    content.append({
                        "type": "image",
                        "data": item.data,
                        "mime_type": getattr(item, "mimeType", "image/png"),
                    })
                else:
                    content.append({"type": "text", "text": str(item)})

            return MCPToolResult(
                tool_name=tool_name,
                server_name=server_name,
                content=content,
                is_error=result.isError if hasattr(result, "isError") else False,
            )
        except Exception as e:
            logger.error(f"MCP tool call failed: {tool_name}@{server_name}: {e}")
            return MCPToolResult(
                tool_name=tool_name,
                server_name=server_name,
                is_error=True,
                error_message=str(e),
            )

    async def _find_tool_server(self, tool_name: str) -> Optional[str]:
        """查找工具所在的服务器"""
        all_tools = await self.list_tools()
        for tool in all_tools:
            if tool.name == tool_name:
                return tool.server_name
        return None

    @property
    def is_connected(self) -> bool:
        return self._connected

    def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有服务器状态"""
        status = {}
        for name, conf in self._config.servers.items():
            status[name] = {
                "enabled": conf.enabled,
                "type": conf.type,
                "connected": name in self._sessions,
                "url": conf.url,
                "command": conf.command,
                "description": conf.description,
            }
        return status

    def invalidate_cache(self, server_name: Optional[str] = None):
        """清除工具缓存"""
        if server_name:
            self._tool_cache.pop(server_name, None)
            self._tool_cache_time.pop(server_name, None)
        else:
            self._tool_cache.clear()
            self._tool_cache_time.clear()


# ===== 全局管理器 =====

_global_manager: Optional[MCPClientManager] = None


def get_mcp_manager() -> Optional[MCPClientManager]:
    """获取全局 MCP 管理器"""
    return _global_manager


async def initialize_mcp(config_dict: Dict[str, Any]) -> MCPClientManager:
    """初始化 MCP 管理器并连接所有服务器"""
    global _global_manager

    config = MCPConfig.from_yaml_config(config_dict)
    manager = MCPClientManager(config)

    enabled = config.get_enabled_servers()
    if enabled:
        results = await manager.connect_all()
        connected = sum(1 for v in results.values() if v)
        logger.info(f"MCP initialized: {connected}/{len(results)} servers connected")
    else:
        logger.info("No MCP servers configured")

    _global_manager = manager
    return manager


async def shutdown_mcp():
    """关闭 MCP 管理器"""
    global _global_manager
    if _global_manager:
        await _global_manager.disconnect_all()
        _global_manager = None
