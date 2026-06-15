from fastapi import APIRouter, HTTPException, Depends

from db.sqlite import Database
from services.tanyin_service import TanyinService
from api.models import TanyinRequest, TanyinSubmitRequest
from api.dependencies import get_db

router = APIRouter(prefix="/tanyin", tags=["tanyin"])


@router.post("/start", response_model=dict)
async def start_tanyin(req: TanyinRequest, db: Database = Depends(get_db)):
    trigger_check = TanyinService.should_trigger_tanyin(
        req.project_id, req.message or ""
    )
    if not trigger_check.get("should_trigger", False):
        return {
            "questions": [],
            "project_id": req.project_id,
            "skipped": True,
            "reason": trigger_check.get("reason", "no_trigger"),
        }

    questions = TanyinService.get_questions()
    return {"questions": questions, "project_id": req.project_id, "skipped": False}


@router.post("/submit", response_model=dict)
async def submit_tanyin(req: TanyinSubmitRequest, db: Database = Depends(get_db)):
    try:
        result = TanyinService.process_answers(req.project_id, req.answers)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{project_id}", response_model=dict)
async def get_tanyin_status(project_id: str, db: Database = Depends(get_db)):
    state = TanyinService.get_state(project_id)
    return state


@router.post("/reset/{project_id}", response_model=dict)
async def reset_tanyin(project_id: str, db: Database = Depends(get_db)):
    TanyinService.reset_state(project_id)
    return {"success": True}
