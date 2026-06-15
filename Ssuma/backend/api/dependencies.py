"""FastAPI 依赖注入

通过 app.state 提供单例实例，替代全局变量和类级状态。
旧代码仍可通过 Database() / LLMFactory / get_flow_service() 工作（向后兼容）。
"""

from fastapi import Request
from db.sqlite import Database
from core.llm_factory import LLMFactory
from services.flow.service import FlowService

MAX_CONVERSATION_CHARS = 10000


def get_db(request: Request) -> Database:
    """从 app.state 获取 Database 实例，回退到全局单例"""
    db = getattr(request.app.state, "db", None)
    if db is not None:
        return db
    return Database()


def get_llm_factory(request: Request) -> type:
    """获取 LLMFactory 类引用

    LLMFactory 当前是类级状态设计，暂不实例化。
    后续 Phase 可将其改为实例模式。
    """
    return LLMFactory


def get_flow_service(request: Request) -> FlowService:
    """从 app.state 获取 FlowService 实例，回退到全局单例"""
    service = getattr(request.app.state, "flow_service", None)
    if service is not None:
        return service
    from services.flow.service import get_flow_service as _get_global
    return _get_global()
