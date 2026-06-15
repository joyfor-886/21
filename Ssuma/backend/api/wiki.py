"""
Wiki 审阅界面 API

提供模块化文档的审阅、批注、修改功能
设计依据：2026-05-06-ssuma-zero-to-hero-design.md 第三章
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

router = APIRouter(prefix="/wiki", tags=["wiki"])


# ======= Models =======

class DocumentAnnotation(BaseModel):
    """文档批注"""
    id: str
    document_id: str
    content: str
    author: str = "user"
    created_at: str


class DocumentModule(BaseModel):
    """文档模块"""
    id: str
    doc_type: str
    title: str
    content: str
    status: str = "pending"  # pending / reviewed / modified
    annotations: List[DocumentAnnotation] = []
    ai_declaration: str = ""


class ProjectDocuments(BaseModel):
    """项目文档包"""
    project_id: str
    project_name: str
    modules: List[DocumentModule]
    reviewed_count: int = 0
    total_count: int = 0


class ModificationRequest(BaseModel):
    """修改请求"""
    project_id: str
    document_id: str
    modification: str
    user_id: str = "default"


class ModificationImpact(BaseModel):
    """修改影响评估"""
    document_id: str
    change_summary: str
    affected_modules: List[Dict[str, Any]]
    risk_level: str  # low / medium / high
    suggestion: str


class AnnotationRequest(BaseModel):
    """批注请求"""
    document_id: str
    content: str
    author: str = "user"


# ======= 文档类型定义 =======

DOC_TYPES = [
    {"id": "requirement", "title": "📌 需求说明书", "desc": "核心问题、用户故事、约束条件"},
    {"id": "prd", "title": "📋 PRD", "desc": "功能列表、优先级、验收标准"},
    {"id": "flowchart", "title": "🔀 业务流程图", "desc": "Mermaid 流程图 + 状态机"},
    {"id": "architecture", "title": "🏗️ 系统架构图", "desc": "技术选型、模块关系、部署图"},
    {"id": "database", "title": "💾 数据库设计", "desc": "ER 图、表结构、索引策略"},
    {"id": "api", "title": "🔌 API 接口文档", "desc": "端点、请求/响应、错误码"},
    {"id": "execution_plan", "title": "📝 执行计划", "desc": "TDD 任务列表（2-5min 粒度）"},
]

# ======= 内存存储（生产应使用数据库）======

_docs_cache: Dict[str, ProjectDocuments] = {}
_STATE_SERVICE_NAME = "wiki_docs"


def _save_docs_to_repo(project_id: str):
    from core.state_repository import StateRepository
    docs = _docs_cache.get(project_id)
    if docs:
        StateRepository.save(_STATE_SERVICE_NAME, project_id, docs.model_dump())


def _load_docs_from_repo(project_id: str) -> Optional[ProjectDocuments]:
    from core.state_repository import StateRepository
    data = StateRepository.load(_STATE_SERVICE_NAME, project_id)
    if data is not None:
        return ProjectDocuments(**data)
    return None


# ======= Endpoints =======

@router.get("/types", response_model=List[Dict[str, str]])
async def get_document_types():
    """获取所有文档类型"""
    return DOC_TYPES


@router.get("/project/{project_id}", response_model=ProjectDocuments)
async def get_project_documents(project_id: str):
    """获取项目所有文档"""
    if project_id in _docs_cache:
        return _docs_cache[project_id]

    cached = _load_docs_from_repo(project_id)
    if cached:
        _docs_cache[project_id] = cached
        return cached

    modules = [
        DocumentModule(
            id=str(uuid.uuid4()),
            doc_type=doc["id"],
            title=doc["title"],
            content=f"# {doc['title']}\n\n等待生成...",
            status="pending"
        )
        for doc in DOC_TYPES
    ]

    docs = ProjectDocuments(
        project_id=project_id,
        project_name="新项目",
        modules=modules,
        reviewed_count=0,
        total_count=len(modules)
    )

    _docs_cache[project_id] = docs
    _save_docs_to_repo(project_id)
    return docs


@router.get("/{document_id}", response_model=DocumentModule)
async def get_document(document_id: str):
    """获取单个文档"""
    for docs in _docs_cache.values():
        for module in docs.modules:
            if module.id == document_id:
                return module
    raise HTTPException(status_code=404, detail="Document not found")


@router.post("/{document_id}/annotate", response_model=DocumentAnnotation)
async def add_annotation(document_id: str, req: AnnotationRequest):
    """添加批注"""
    annotation = DocumentAnnotation(
        id=str(uuid.uuid4()),
        document_id=document_id,
        content=req.content,
        author=req.author,
        created_at=datetime.now().isoformat()
    )

    # 找到文档并添加批注
    for docs in _docs_cache.values():
        for module in docs.modules:
            if module.id == document_id:
                module.annotations.append(annotation)
                _save_docs_to_repo(docs.project_id)
                return annotation

    raise HTTPException(status_code=404, detail="Document not found")


@router.get("/{document_id}/annotations", response_model=List[DocumentAnnotation])
async def get_annotations(document_id: str):
    """获取文档所有批注"""
    for docs in _docs_cache.values():
        for module in docs.modules:
            if module.id == document_id:
                return module.annotations
    raise HTTPException(status_code=404, detail="Document not found")


@router.post("/modify", response_model=ModificationImpact)
async def request_modification(req: ModificationRequest):
    """
    请求修改文档

    返回 AI 影响评估
    """
    # 找到文档
    target_doc = None
    for docs in _docs_cache.values():
        for module in docs.modules:
            if module.id == req.document_id:
                target_doc = module
                break
        if target_doc:
            break

    if not target_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # 生成影响评估
    # 实际应调用 LLM 生成，这里简化处理
    impact = ModificationImpact(
        document_id=req.document_id,
        change_summary=f"修改：{req.modification[:50]}...",
        affected_modules=[
            {
                "doc_type": target_doc.doc_type,
                "title": target_doc.title,
                "action": "需更新"
            }
        ],
        risk_level="medium",
        suggestion="建议修改，影响范围可控"
    )

    return impact


@router.post("/{document_id}/review")
async def mark_as_reviewed(document_id: str):
    """标记文档已审阅"""
    for docs in _docs_cache.values():
        for module in docs.modules:
            if module.id == document_id:
                module.status = "reviewed"
                docs.reviewed_count += 1
                _save_docs_to_repo(docs.project_id)
                return {"success": True, "status": "reviewed"}

    raise HTTPException(status_code=404, detail="Document not found")


@router.get("/project/{project_id}/stats")
async def get_review_stats(project_id: str):
    """获取审阅统计"""
    if project_id not in _docs_cache:
        return {
            "reviewed_count": 0,
            "total_count": len(DOC_TYPES),
            "pending_count": len(DOC_TYPES),
            "modified_count": 0
        }

    docs = _docs_cache[project_id]
    return {
        "reviewed_count": docs.reviewed_count,
        "total_count": docs.total_count,
        "pending_count": docs.total_count - docs.reviewed_count,
        "modified_count": sum(1 for m in docs.modules if m.status == "modified")
    }


@router.post("/project/{project_id}/generate")
async def generate_documents(project_id: str):
    """
    生成项目文档包

    调用凝墨技能生成完整的7份模块文档
    """
    # TODO: 调用 ningmo 技能生成文档
    # 这里简化处理，返回成功

    if project_id not in _docs_cache:
        await get_project_documents(project_id)

    return {
        "success": True,
        "message": "文档生成请求已提交",
        "project_id": project_id
    }
