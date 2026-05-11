from fastapi import APIRouter, HTTPException

from services.questionnaire_service import QuestionnaireService
from api.models import QuestionnaireRequest, QuestionnaireSubmitRequest

router = APIRouter(prefix="/questionnaire", tags=["questionnaire"])


@router.post("/start", response_model=dict)
async def start_questionnaire(req: QuestionnaireRequest):
    questions = QuestionnaireService.get_questions()
    return {"questions": questions, "project_id": req.project_id}


@router.post("/submit", response_model=dict)
async def submit_questionnaire(req: QuestionnaireSubmitRequest):
    try:
        result = QuestionnaireService.process_answers(req.project_id, req.answers)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{project_id}", response_model=dict)
async def get_questionnaire_status(project_id: str):
    state = QuestionnaireService.get_state(project_id)
    return state


@router.post("/reset/{project_id}", response_model=dict)
async def reset_questionnaire(project_id: str):
    QuestionnaireService.reset_state(project_id)
    return {"success": True}
