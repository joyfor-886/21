from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class ChatRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    message: str
    project_id: Optional[str] = None
    attachments: Optional[List[dict]] = []


class CreateProjectRequest(BaseModel):
    id: Optional[str] = None
    name: str = "New Project"
    description: str = ""


class ChatResponse(BaseModel):
    project_id: str
    response: str
    phase: str
    intent_analysis: Optional[Dict] = None
    suggested_next_action: Optional[str] = None


class FlowChatRequest(BaseModel):
    message: str
    project_id: Optional[str] = None
    force_workflow: Optional[str] = None
    attachments: Optional[List[dict]] = []


class FlowChatResponse(BaseModel):
    project_id: str
    response: str
    current_phase: str
    current_phase_label: str
    intent_analysis: Optional[Dict] = None
    suggested_next_phase: Optional[str] = None
    suggested_next_action: Optional[str] = None
    workflow_options: Optional[List[Dict]] = []
    completed: bool = False
    hitl_interrupt: Optional[Dict] = None


class GenerationRequest(BaseModel):
    project_id: str
    name: str = "Untitled"
    description: str = ""
    features: list = []
    tech_stack: str = "Next.js + Supabase"
    data_model: dict = {}


class ModelFetchRequest(BaseModel):
    provider: str
    api_key: str
    base_url: Optional[str] = None


class TanyinRequest(BaseModel):
    project_id: str
    message: Optional[str] = None


class TanyinSubmitRequest(BaseModel):
    project_id: str
    answers: Dict[str, Any]


class FeedbackRequest(BaseModel):
    project_id: str
    rating: int
    feedback_text: str = ""


class OrchestratorInitRequest(BaseModel):
    project_id: str
    tasks: list = []


class TaskCompleteRequest(BaseModel):
    project_id: str
    task_id: str


class ErrorAnalyzeRequest(BaseModel):
    project_id: str
    error: str


class LLMDetectRequest(BaseModel):
    provider: str
    model: str
    run_test: bool = False


class LLMConfigRequest(BaseModel):
    mode: str
    chat_provider: str
    chat_model: str
    generate_provider: Optional[str] = None
    generate_model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class LLMTestConnectionRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    provider_type: str
    base_url: str
    api_key: Optional[str] = None
    model_name: Optional[str] = None


class LLMFetchModelsRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    provider_type: str
    base_url: str
    api_key: Optional[str] = None


class LLMSpeedTestRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    provider_type: str
    base_url: str
    model_name: str
    api_key: Optional[str] = None


class EvolutionActionRequest(BaseModel):
    evolution_id: str
    action: str
