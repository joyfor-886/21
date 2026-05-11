from fastapi import APIRouter

from services.context_generator import ContextGenerator
from services.scaffold_generator import ScaffoldGenerator
from api.models import GenerationRequest

router = APIRouter(prefix="/generate", tags=["generation"])


@router.post("/context", response_model=dict)
async def generate_context(req: GenerationRequest):
    spec = {
        "name": req.name,
        "description": req.description,
        "features": req.features,
        "tech_stack": req.tech_stack,
        "data_model": req.data_model
    }
    files = ContextGenerator.generate(spec)
    return {
        "project_id": req.project_id,
        "files": files,
        "download_url": f"/api/download/context/{req.project_id}"
    }


@router.post("/scaffold", response_model=dict)
async def generate_scaffold(req: GenerationRequest):
    config = {
        "name": req.name,
        "tech_stack": req.tech_stack,
        "features": req.features,
        "description": req.description,
        "data_model": req.data_model
    }
    files = ScaffoldGenerator.generate(config)
    return {
        "project_id": req.project_id,
        "files_count": len(files),
        "files": files
    }
