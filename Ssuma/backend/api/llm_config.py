import httpx
import re
import time
import logging
from typing import Optional
from fastapi import APIRouter

from core.config import Config
from core.llm_factory import LLMFactory
from api.models import (
    LLMDetectRequest, LLMConfigRequest, LLMTestConnectionRequest,
    LLMFetchModelsRequest, LLMSpeedTestRequest,
)

logger = logging.getLogger('Ssuma.LLMConfigAPI')

router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/detect", response_model=dict)
async def detect_llm_tier(req: LLMDetectRequest):
    from core.llm_adapter import get_llm_adapter, ModelTier, TIER_CAPABILITY_CONFIGS

    adapter = get_llm_adapter()
    model_info = await adapter.detect_and_configure(
        provider_name=req.provider,
        model_name=req.model,
        run_test=req.run_test
    )

    config = adapter.get_capability_config(model_info.tier)

    return {
        "model": model_info.name,
        "provider": model_info.provider,
        "tier": model_info.tier.value,
        "tier_label": model_info.tier.label,
        "tier_color": model_info.tier.color,
        "tier_source": model_info.tier_source,
        "estimated_params": model_info.estimated_params,
        "capability_config": {
            "qishu_enabled": config.qishu_enabled,
            "qishu_depth": config.qishu_depth,
            "caiheng_enabled": config.caiheng_enabled,
            "caiheng_challenge_dims": config.caiheng_challenge_dims,
            "zhenwei_enabled": config.zhenwei_enabled,
            "zhenwei_scope": config.zhenwei_scope,
            "ceshu_enabled": config.ceshu_enabled,
            "ceshu_granularity": config.ceshu_granularity,
            "ningmo_passes": config.ningmo_passes,
            "powang_enabled": config.powang_enabled,
            "jianyan_enabled": config.jianyan_enabled,
            "jianyan_stages": config.jianyan_stages,
        }
    }


@router.post("/test-connection", response_model=dict)
async def test_llm_connection(req: LLMTestConnectionRequest):
    from core.llm_adapter import get_llm_config_manager

    config_manager = get_llm_config_manager()
    result = await config_manager.test_connection(
        provider_type=req.provider_type,
        base_url=req.base_url,
        api_key=req.api_key,
        model_name=req.model_name
    )

    if result.get("success"):
        available_models = await config_manager.list_available_models(
            provider_type=req.provider_type,
            base_url=req.base_url,
            api_key=req.api_key
        )
        result["available_models"] = available_models

    return result


@router.get("/list-providers", response_model=dict)
async def list_llm_providers():
    yaml_config = Config()
    raw_providers = yaml_config.llm.get("providers", {})
    default_provider = yaml_config.llm.get("default_provider", "")

    active_models = {}
    for name, provider in LLMFactory._providers.items():
        if hasattr(provider, "model"):
            active_models[name] = provider.model

    provider_details = []
    for name, cfg in raw_providers.items():
        provider_details.append({
            "name": name,
            "model": active_models.get(name, cfg.get("model", "")),
            "base_url": cfg.get("base_url", ""),
            "type": cfg.get("type", "openai_compatible"),
        })

    return {
        "default": default_provider,
        "providers": provider_details,
    }


@router.post("/config", response_model=dict)
async def save_llm_config(req: LLMConfigRequest):
    from core.llm_adapter import get_llm_config_manager, get_llm_adapter

    config_manager = get_llm_config_manager()
    adapter = get_llm_adapter()

    config = {
        "mode": req.mode,
        "chat_model": {
            "provider": req.chat_provider,
            "model": req.chat_model,
        },
        "generate_model": {
            "provider": req.generate_provider or req.chat_provider,
            "model": req.generate_model or req.chat_model,
        },
        "base_url": req.base_url,
        "api_key": req.api_key,
    }

    success = config_manager.save_user_llm_config("default", config)

    model_info = await adapter.detect_and_configure(
        provider_name=req.chat_provider,
        model_name=req.chat_model,
        run_test=False
    )

    return {
        "success": success,
        "mode": req.mode,
        "chat_model": {
            "provider": req.chat_provider,
            "model": req.chat_model,
            "tier": model_info.tier.value,
            "tier_label": model_info.tier.label,
        },
        "generate_model": {
            "provider": req.generate_provider or req.chat_provider,
            "model": req.generate_model or req.chat_model,
        },
    }


@router.get("/config", response_model=dict)
async def get_llm_config():
    from core.llm_adapter import get_llm_config_manager, get_llm_adapter

    config_manager = get_llm_config_manager()
    adapter = get_llm_adapter()

    config = config_manager.get_user_llm_config("default")

    chat_provider = config.get("chat_model", {}).get("provider", "")
    chat_base_url = config.get("chat_model", {}).get("base_url", "") or config.get("base_url", "")
    if not chat_base_url and chat_provider:
        if chat_provider == "ollama":
            chat_base_url = "http://127.0.0.1:11434/v1"
        elif chat_provider == "lm_studio":
            chat_base_url = "http://127.0.0.1:1234/v1"
        else:
            yaml_config = Config()
            provider_cfg = yaml_config.llm.get("providers", {}).get(chat_provider, {})
            chat_base_url = provider_cfg.get("base_url", "")

    chat_model = config.get("chat_model", {}).get("model", "")

    try:
        model_info = await adapter.detect_and_configure(chat_provider, chat_model)
        tier = model_info.tier.value
        tier_label = model_info.tier.label
    except Exception as e:
        logger.warning(f"检测模型档次失败: {e}")
        tier = "unknown"
        tier_label = "未知"

    return {
        **config,
        "chat_model": {
            **config.get("chat_model", {}),
            "base_url": chat_base_url,
        },
        "current_tier": tier,
        "current_tier_label": tier_label,
    }


@router.get("/declaration", response_model=dict)
async def get_ai_declaration(model_name: str, tier: str = "adequate", version: str = "1.0"):
    from core.llm_adapter import get_llm_adapter, ModelTier

    adapter = get_llm_adapter()
    tier_enum = ModelTier(tier)
    declaration = adapter.generate_ai_declaration(
        tier=tier_enum,
        model_name=model_name,
        version=version
    )

    return {
        "declaration": declaration,
        "tier": tier,
        "tier_label": tier_enum.label,
        "tier_color": tier_enum.color,
    }


@router.get("/capability-matrix", response_model=dict)
async def get_capability_matrix():
    from core.llm_adapter import ModelTier, TIER_CAPABILITY_CONFIGS

    matrix = {}
    for tier in ModelTier:
        config = TIER_CAPABILITY_CONFIGS[tier]
        matrix[tier.value] = {
            "label": tier.label,
            "color": tier.color,
            "capabilities": {
                "qishu": {
                    "enabled": config.qishu_enabled,
                    "depth": config.qishu_depth,
                    "description": "启枢对话引导"
                },
                "caiheng": {
                    "enabled": config.caiheng_enabled,
                    "challenge_dims": config.caiheng_challenge_dims,
                    "description": "CEO 视角审视"
                },
                "zhenwei": {
                    "enabled": config.zhenwei_enabled,
                    "scope": config.zhenwei_scope,
                    "description": "技术架构评审"
                },
                "ceshu": {
                    "enabled": config.ceshu_enabled,
                    "granularity": config.ceshu_granularity,
                    "description": "执行计划"
                },
                "ningmo": {
                    "enabled": True,
                    "passes": config.ningmo_passes,
                    "description": "凝墨方案生成"
                },
                "powang": {
                    "enabled": config.powang_enabled,
                    "description": "需求覆盖检查"
                },
                "jianyan": {
                    "enabled": config.jianyan_enabled,
                    "max_stages": config.jianyan_stages,
                    "description": "分阶段生成"
                },
            }
        }

    return {"matrix": matrix}


@router.get("/known-models", response_model=dict)
async def get_known_models():
    from core.llm_adapter import KNOWN_MODELS, ModelTier

    models_by_tier = {
        "adequate": [],
        "basic": [],
        "insufficient": [],
    }

    for model_name, tier in KNOWN_MODELS.items():
        models_by_tier[tier.value].append(model_name)

    return {
        "adequate": {
            "label": "🟢 达标档",
            "models": models_by_tier["adequate"],
            "description": "完整七艺可用，复杂推理、长文档生成稳定"
        },
        "basic": {
            "label": "🟡 基础档",
            "models": models_by_tier["basic"],
            "description": "七艺可用，部分功能降级"
        },
        "insufficient": {
            "label": "🔴 不足档",
            "models": models_by_tier["insufficient"],
            "description": "仅启枢可用，凝墨生成简化版"
        },
    }


def _format_size(size_bytes: int) -> str:
    if size_bytes <= 0:
        return ""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def _parse_param_from_name(name: str) -> str:
    m = re.search(r'(\d+(?:\.\d+)?)\s*[bB]', name)
    return f"{m.group(1).upper()}B" if m else ""


def _parse_quant_from_name(name: str) -> str:
    m = re.search(r'(Q\d+[_\w]*)', name, re.IGNORECASE)
    return m.group(1) if m else ""


@router.post("/fetch-models", response_model=dict)
async def fetch_models_from_server(req: LLMFetchModelsRequest):
    models = []
    provider_type = req.provider_type
    base_url = req.base_url.rstrip("/")

    if provider_type == "ollama":
        tags_url = base_url.replace("/v1", "").rstrip("/") + "/api/tags"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(tags_url)
                if resp.status_code == 200:
                    raw_models = resp.json().get("models", [])
                    for m in raw_models:
                        details = m.get("details", {})
                        models.append({
                            "name": m.get("name", ""),
                            "architecture": details.get("family", "") or details.get("format", ""),
                            "quantization": details.get("quantization_level", "") or _parse_quant_from_name(m.get("name", "")),
                            "size": m.get("size", 0),
                            "size_label": _format_size(m.get("size", 0)),
                            "parameter_size": details.get("parameter_size", "") or _parse_param_from_name(m.get("name", "")),
                            "family": details.get("family", ""),
                            "format": details.get("format", "gguf"),
                        })
        except Exception as e:
            return {"success": False, "error": f"连接 Ollama 失败: {str(e)[:150]}", "models": []}

    elif provider_type == "lm_studio":
        models_url = base_url.rstrip("/") + "/models"
        headers = {}
        if req.api_key:
            headers["Authorization"] = f"Bearer {req.api_key}"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(models_url, headers=headers)
                if resp.status_code == 200:
                    raw_models = resp.json().get("data", [])
                    for m in raw_models:
                        model_id = m.get("id", "")
                        models.append({
                            "name": model_id,
                            "architecture": "",
                            "quantization": _parse_quant_from_name(model_id),
                            "size": 0,
                            "size_label": "",
                            "parameter_size": _parse_param_from_name(model_id),
                            "family": "",
                            "format": "",
                        })
        except Exception as e:
            return {"success": False, "error": f"连接 LM Studio 失败: {str(e)[:150]}", "models": []}

    else:
        models_url = base_url.rstrip("/") + "/models"
        headers = {}
        if req.api_key:
            headers["Authorization"] = f"Bearer {req.api_key}"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(models_url, headers=headers)
                if resp.status_code == 200:
                    raw_models = resp.json().get("data", [])
                    for m in raw_models:
                        model_id = m.get("id", "")
                        models.append({
                            "name": model_id,
                            "architecture": "",
                            "quantization": _parse_quant_from_name(model_id),
                            "size": 0,
                            "size_label": "",
                            "parameter_size": _parse_param_from_name(model_id),
                            "family": "",
                            "format": "",
                        })
        except Exception as e:
            return {"success": False, "error": f"连接失败: {str(e)[:150]}", "models": []}

    return {
        "success": True,
        "provider_type": provider_type,
        "base_url": base_url,
        "models": models,
        "total": len(models),
    }


@router.get("/scan-local", response_model=dict)
async def scan_local_models():
    ollama_result = {"running": False, "models": [], "error": None}
    lm_studio_result = {"running": False, "models": [], "error": None}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://127.0.0.1:11434/api/tags")
            if resp.status_code == 200:
                ollama_result["running"] = True
                raw_models = resp.json().get("models", [])
                ollama_result["models"] = [
                    {"name": m.get("name", ""), "size": m.get("size", 0), "modified_at": m.get("modified_at", "")}
                    for m in raw_models
                ]
    except Exception as e:
        ollama_result["error"] = f"Ollama 未运行或连接失败: {str(e)[:100]}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://127.0.0.1:1234/v1/models")
            if resp.status_code == 200:
                lm_studio_result["running"] = True
                raw_models = resp.json().get("data", [])
                lm_studio_result["models"] = [
                    {"name": m.get("id", ""), "size": 0, "modified_at": ""}
                    for m in raw_models
                ]
    except Exception as e:
        lm_studio_result["error"] = f"LM Studio 未运行或连接失败: {str(e)[:100]}"

    total = len(ollama_result["models"]) + len(lm_studio_result["models"])

    return {
        "ollama": ollama_result,
        "lm_studio": lm_studio_result,
        "summary": {
            "total_models": total,
            "ollama_running": ollama_result["running"],
            "lm_studio_running": lm_studio_result["running"],
            "any_available": total > 0,
        }
    }


@router.post("/apply-model", response_model=dict)
async def apply_llm_model(req: LLMConfigRequest):
    from core.llm_adapter import get_llm_config_manager, get_llm_adapter

    config_manager = get_llm_config_manager()
    adapter = get_llm_adapter()

    chat_base_url = req.base_url
    if not chat_base_url:
        if req.chat_provider == "ollama":
            chat_base_url = "http://127.0.0.1:11434/v1"
        elif req.chat_provider == "lm_studio":
            chat_base_url = "http://127.0.0.1:1234/v1"
        else:
            config = Config()
            provider_cfg = config.llm.get("providers", {}).get(req.chat_provider, {})
            chat_base_url = provider_cfg.get("base_url", "")

    config = {
        "mode": req.mode,
        "chat_model": {
            "provider": req.chat_provider,
            "model": req.chat_model,
            "base_url": chat_base_url,
        },
        "generate_model": {
            "provider": req.generate_provider or req.chat_provider,
            "model": req.generate_model or req.chat_model,
            "base_url": chat_base_url,
        },
        "base_url": chat_base_url,
        "api_key": req.api_key,
    }

    success = config_manager.save_user_llm_config("default", config)

    try:
        provider_type_map = {
            "ollama": "openai_compatible",
            "lm_studio": "lm_studio",
            "openai": "openai",
            "claude": "anthropic",
        }
        provider_type = provider_type_map.get(req.chat_provider, "openai_compatible")
        provider_cfg = {
            "model": req.chat_model,
            "base_url": chat_base_url,
            "api_key": req.api_key or "",
            "type": provider_type,
        }
        from core.llm_factory import (
            OpenAIProvider, OpenAICompatibleProvider,
            LMStudioProvider, ClaudeProvider
        )
        if provider_type == "openai":
            LLMFactory._providers[req.chat_provider] = OpenAIProvider(provider_cfg)
        elif provider_type == "anthropic":
            LLMFactory._providers[req.chat_provider] = ClaudeProvider(provider_cfg)
        elif provider_type == "lm_studio":
            LLMFactory._providers[req.chat_provider] = LMStudioProvider(provider_cfg)
        else:
            LLMFactory._providers[req.chat_provider] = OpenAICompatibleProvider(provider_cfg)
        LLMFactory._default_provider = req.chat_provider
    except Exception as e:
        logger.warning(f"更新 LLMFactory provider 失败: {e}")

    model_info = await adapter.detect_and_configure(
        provider_name=req.chat_provider,
        model_name=req.chat_model,
        run_test=False
    )

    return {
        "success": success,
        "mode": req.mode,
        "chat_model": {
            "provider": req.chat_provider,
            "model": req.chat_model,
            "base_url": chat_base_url,
            "tier": model_info.tier.value,
            "tier_label": model_info.tier.label,
        },
        "generate_model": {
            "provider": req.generate_provider or req.chat_provider,
            "model": req.generate_model or req.chat_model,
        },
    }


@router.post("/speed-test", response_model=dict)
async def llm_speed_test(req: LLMSpeedTestRequest):
    base_url = req.base_url
    if not base_url:
        if req.provider_type == "ollama":
            base_url = "http://127.0.0.1:11434/v1"
        elif req.provider_type == "lm_studio":
            base_url = "http://127.0.0.1:1234/v1"
        else:
            config = Config()
            provider_cfg = config.llm.get("providers", {}).get(req.provider_type, {})
            base_url = provider_cfg.get("base_url", "")

    try:
        provider_type_map = {
            "ollama": "openai_compatible",
            "lm_studio": "lm_studio",
            "openai": "openai",
            "claude": "anthropic",
        }
        provider_type = provider_type_map.get(req.provider_type, "openai_compatible")
        provider_cfg = {
            "model": req.model_name,
            "base_url": base_url,
            "api_key": req.api_key or "",
            "type": provider_type,
        }

        from core.llm_factory import (
            OpenAIProvider, OpenAICompatibleProvider,
            LMStudioProvider, ClaudeProvider
        )
        if provider_type == "openai":
            provider = OpenAIProvider(provider_cfg)
        elif provider_type == "anthropic":
            provider = ClaudeProvider(provider_cfg)
        elif provider_type == "lm_studio":
            provider = LMStudioProvider(provider_cfg)
        else:
            provider = OpenAICompatibleProvider(provider_cfg)

        test_prompt = "请用50字简述什么是软件架构。"
        start_time = time.time()
        response = await provider.chat(
            messages=[{"role": "user", "content": test_prompt}],
            temperature=0.3,
            max_tokens=200
        )
        elapsed = time.time() - start_time

        char_count = len(response) if response else 0
        estimated_tokens = max(1, int(char_count / 1.5))
        tokens_per_second = round(estimated_tokens / elapsed, 1) if elapsed > 0 else 0

        return {
            "success": True,
            "elapsed_seconds": round(elapsed, 2),
            "response_length": char_count,
            "estimated_tokens": estimated_tokens,
            "tokens_per_second": tokens_per_second,
            "response_preview": (response or "")[:100],
            "model": req.model_name,
            "provider": req.provider_type,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "model": req.model_name,
            "provider": req.provider_type,
        }


@router.get("/health", response_model=dict)
async def llm_health_check(provider: Optional[str] = None):
    return await LLMFactory.health_check(provider)


@router.post("/reconnect", response_model=dict)
async def llm_reconnect(provider: Optional[str] = None):
    success = LLMFactory.reconnect(provider)
    return {"success": success, "provider": provider or LLMFactory.get_default_provider()}
