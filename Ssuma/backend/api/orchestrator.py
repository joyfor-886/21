from fastapi import APIRouter

from services.orchestrator import OrchestratorService
from api.models import OrchestratorInitRequest, TaskCompleteRequest, ErrorAnalyzeRequest

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


@router.post("/init", response_model=dict)
async def init_orchestrator(req: OrchestratorInitRequest):
    tasks = await OrchestratorService.create_project_tasks(
        req.project_id,
        {"tasks": req.tasks}
    )
    return {
        "success": True,
        "tasks_count": len(tasks)
    }


@router.get("/progress/{project_id}", response_model=dict)
async def get_orchestrator_progress(project_id: str):
    return OrchestratorService.get_progress(project_id)


@router.get("/task/{project_id}", response_model=dict)
async def get_current_task(project_id: str):
    prompt = OrchestratorService.get_task_prompt(project_id)
    if not prompt:
        return {"has_task": False}
    return {"has_task": True, "prompt": prompt}


@router.post("/complete", response_model=dict)
async def complete_task(req: TaskCompleteRequest):
    success = OrchestratorService.complete_task(req.project_id, req.task_id)
    return {"success": success, "progress": OrchestratorService.get_progress(req.project_id)}


@router.post("/error", response_model=dict)
async def analyze_error(req: ErrorAnalyzeRequest):
    result = await OrchestratorService.analyze_error(req.project_id, req.error)
    return result


@router.post("/reset/{project_id}", response_model=dict)
async def reset_orchestrator(project_id: str):
    OrchestratorService.reset_project(project_id)
    return {"success": True}
