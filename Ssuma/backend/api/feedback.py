from fastapi import APIRouter, HTTPException

from services.feedback_service import FeedbackService
from api.models import FeedbackRequest

router = APIRouter(prefix="", tags=["feedback"])


@router.post("/feedback", response_model=dict)
async def submit_feedback(req: FeedbackRequest):
    if req.rating < 1 or req.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    try:
        FeedbackService.add_feedback(
            project_id=req.project_id,
            turn=0,
            rating=req.rating,
            feedback_text=req.feedback_text,
            ai_response="",
            phase=""
        )

        trend = FeedbackService.get_satisfaction_trend(req.project_id)
        return {
            "success": True,
            "average_rating": trend["average"],
            "trend": trend["trend"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/stats/{project_id}", response_model=dict)
async def get_feedback_stats(project_id: str):
    try:
        trend = FeedbackService.get_satisfaction_trend(project_id)
        return trend
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
