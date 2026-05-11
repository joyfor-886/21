from fastapi import APIRouter, HTTPException

from services.evolution_engine import SelfEvolutionEngine
from api.models import EvolutionActionRequest

router = APIRouter(prefix="/evolution", tags=["evolution"])


@router.get("/history", response_model=list)
async def get_evolution_history():
    history = SelfEvolutionEngine.get_history()
    return [
        {
            "id": r.id,
            "type": r.type.value,
            "description": r.description,
            "risk": r.risk.value,
            "status": r.status.value,
            "created_at": r.created_at,
            "applied_at": r.applied_at,
        }
        for r in history
    ]


@router.post("/action", response_model=dict)
async def evolution_action(req: EvolutionActionRequest):
    if req.action == "apply":
        success = SelfEvolutionEngine.apply_evolution(req.evolution_id)
        return {"success": success}
    elif req.action == "rollback":
        success = SelfEvolutionEngine.rollback_evolution(req.evolution_id)
        return {"success": success}
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")


@router.get("/config", response_model=dict)
async def get_evolution_config():
    return SelfEvolutionEngine._current_config


@router.get("/stats", response_model=dict)
async def get_evolution_stats():
    history = SelfEvolutionEngine.get_history()
    return {
        "total_evolutions": len(history),
        "applied": sum(1 for r in history if r.status.value == "applied"),
        "pending": sum(1 for r in history if r.status.value == "pending"),
        "rolled_back": sum(1 for r in history if r.status.value == "rolled_back"),
    }
