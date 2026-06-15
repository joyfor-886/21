"""Voice TTS & STT API"""
import io
import logging
import os
import tempfile
import edge_tts
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger("Ssuma.voice")

router = APIRouter(prefix="/voice", tags=["voice"])

AVAILABLE_VOICES = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",
    "yunxi": "zh-CN-YunxiNeural",
    "xiaoyi": "zh-CN-XiaoyiNeural",
    "yunjian": "zh-CN-YunjianNeural",
    "xiaochen": "zh-CN-XiaochenNeural",
    "xiaohan": "zh-CN-XiaohanNeural",
    "xiaomeng": "zh-CN-XiaomengNeural",
    "xiaoqiu": "zh-CN-XiaoqiuNeural",
    "xiaorui": "zh-CN-XiaoruiNeural",
    "xiaoshuang": "zh-CN-XiaoshuangNeural",
    "xiaoxuan": "zh-CN-XiaoxuanNeural",
    "xiaoyan": "zh-CN-XiaoyanNeural",
    "xiaoyou": "zh-CN-XiaoyouNeural",
    "xiaozhen": "zh-CN-XiaozhenNeural",
    "yunfeng": "zh-CN-YunfengNeural",
    "yunhao": "zh-CN-YunhaoNeural",
    "yunxia": "zh-CN-YunxiaNeural",
    "yunze": "zh-CN-YunzeNeural",
}

# 机械音色预设：低音 + 降调 + 稍快语速
ROBOT_VOICE_PRESETS = {
    "robot": {
        "voice_id": "zh-CN-YunjianNeural",
        "pitch": "-15Hz",
        "rate": "+10%",
    },
    "robot_deep": {
        "voice_id": "zh-CN-YunzeNeural",
        "pitch": "-25Hz",
        "rate": "-5%",
    },
    "robot_cold": {
        "voice_id": "zh-CN-YunfengNeural",
        "pitch": "-10Hz",
        "rate": "+5%",
    },
}

DEFAULT_VOICE = "robot"


class TTSRequest(BaseModel):
    text: str
    voice: str = DEFAULT_VOICE
    rate: str = "+0%"
    volume: str = "+0%"


@router.get("/tts")
async def text_to_speech(
    text: str = Query(..., max_length=2000, description="要转换的文本"),
    voice: str = Query(DEFAULT_VOICE, description="音色名称"),
    rate: str = Query("+0%", description="语速调整"),
    volume: str = Query("+0%", description="音量调整"),
):
    """将文本转换为语音，返回 MP3 音频流"""
    if not text.strip():
        raise HTTPException(status_code=400, detail="文本不能为空")

    # Check robot voice presets first
    preset = ROBOT_VOICE_PRESETS.get(voice)
    if preset:
        voice_id = preset["voice_id"]
        # Merge preset pitch/rate with explicit overrides
        pitch = preset["pitch"]
        actual_rate = preset["rate"]
    else:
        voice_id = AVAILABLE_VOICES.get(voice, AVAILABLE_VOICES["xiaoxiao"])
        pitch = "+0Hz"

    try:
        communicate = edge_tts.Communicate(text, voice_id, rate=actual_rate if preset else rate, volume=volume, pitch=pitch)
        audio_buffer = io.BytesIO()

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer.write(chunk["data"])

        audio_buffer.seek(0)

        return StreamingResponse(
            audio_buffer,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=tts.mp3",
                "Cache-Control": "no-cache",
                "X-Audio-Duration": str(len(audio_buffer.getvalue()) // 32000),
            },
        )
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")


@router.get("/voices")
async def list_voices():
    """列出可用的音色"""
    voices = [
        {"id": key, "name": key, "voice_id": val, "type": "neural"}
        for key, val in AVAILABLE_VOICES.items()
    ]
    voices += [
        {"id": key, "name": key, "voice_id": val["voice_id"], "type": "robot", "pitch": val["pitch"], "rate": val["rate"]}
        for key, val in ROBOT_VOICE_PRESETS.items()
    ]
    return {"voices": voices, "default": DEFAULT_VOICE}


@router.post("/stt")
async def speech_to_text(
    audio: UploadFile = File(..., description="音频文件 (webm/wav/mp3)"),
    language: str = Query("zh", description="语言代码"),
):
    """语音转文字 — 优先复用已配置的 LLM Provider API Key，回退到本地 faster-whisper"""
    # Read audio data
    audio_data = await audio.read()
    if len(audio_data) < 100:
        raise HTTPException(status_code=400, detail="音频数据过短")

    # Determine filename with extension
    filename = audio.filename or "audio.webm"
    content_type = audio.content_type or "audio/webm"

    import httpx

    # --- Strategy 1: Reuse configured LLM providers' API keys ---
    try:
        from core.llm_factory import LLMFactory
        # 确保 LLMFactory 已初始化
        if not LLMFactory._providers:
            LLMFactory.initialize()
        for provider_name, provider in LLMFactory._providers.items():
            api_key = getattr(provider, "api_key", "")
            base_url = getattr(provider, "base_url", "")
            # 跳过无有效 API Key 的本地 Provider
            if not api_key or api_key in ("dummy", ""):
                continue
            # 跳过本地服务（lm_studio, ollama）
            if any(local in base_url for local in ("127.0.0.1", "localhost")):
                continue

            # Determine Whisper endpoint based on provider
            if "groq" in provider_name.lower() or "groq" in base_url.lower():
                whisper_url = "https://api.groq.com/openai/v1/audio/transcriptions"
                whisper_model = "whisper-large-v3"
            elif "openai" in provider_name.lower() or "openai" in base_url.lower():
                whisper_url = "https://api.openai.com/v1/audio/transcriptions"
                whisper_model = "whisper-1"
            elif "deepseek" in provider_name.lower() or "deepseek" in base_url.lower():
                # DeepSeek doesn't have STT, skip
                continue
            else:
                # Try OpenAI-compatible /v1/audio/transcriptions on the same base_url
                whisper_url = f"{base_url.rstrip('/')}/audio/transcriptions"
                whisper_model = "whisper-1"

            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        whisper_url,
                        headers={"Authorization": f"Bearer {api_key}"},
                        files={"file": (filename, audio_data, content_type)},
                        data={"model": whisper_model, "language": language, "response_format": "json"},
                    )
                    if resp.status_code == 200:
                        result = resp.json()
                        text = result.get("text", "").strip()
                        if text:
                            logger.info(f"STT via {provider_name}: {text[:50]}")
                            return {"text": text, "engine": provider_name}
                    else:
                        logger.debug(f"STT via {provider_name} failed: {resp.status_code}")
            except Exception as e:
                logger.debug(f"STT via {provider_name} error: {e}")
    except Exception as e:
        logger.debug(f"LLMFactory lookup error: {e}")

    # --- Strategy 2: Environment variable API keys ---
    for env_key, url, model in [
        ("GROQ_API_KEY", "https://api.groq.com/openai/v1/audio/transcriptions", "whisper-large-v3"),
        ("OPENAI_API_KEY", "https://api.openai.com/v1/audio/transcriptions", "whisper-1"),
        ("SILICONFLOW_API_KEY", "https://api.siliconflow.cn/v1/audio/transcriptions", "FunAudioLLM/SenseVoiceSmall"),
    ]:
        api_key = os.environ.get(env_key, "")
        if api_key:
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        url,
                        headers={"Authorization": f"Bearer {api_key}"},
                        files={"file": (filename, audio_data, content_type)},
                        data={"model": model, "language": language, "response_format": "json"},
                    )
                    if resp.status_code == 200:
                        result = resp.json()
                        text = result.get("text", "").strip()
                        if text:
                            logger.info(f"STT via {env_key}: {text[:50]}")
                            return {"text": text, "engine": env_key.lower().replace("_key", "")}
            except Exception as e:
                logger.warning(f"STT via {env_key} error: {e}")

    # --- Strategy 3: Local faster-whisper ---
    try:
        from faster_whisper import WhisperModel
        if not os.environ.get("HF_ENDPOINT"):
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        try:
            segments, _ = model.transcribe(tmp_path, language=language if language != "zh" else "zh")
            text = " ".join(s.text for s in segments).strip()
            logger.info(f"Local STT result: '{text[:100]}' (len={len(text)})")
            # Return result even if empty — client can handle it
            return {"text": text, "engine": "local-whisper"}
        finally:
            os.unlink(tmp_path)
    except ImportError:
        logger.info("faster-whisper not installed, skipping local STT")
    except Exception as e:
        logger.warning(f"Local STT error: {e}")

    raise HTTPException(
        status_code=503,
        detail="语音识别服务不可用。请安装 faster-whisper 或配置 API Key",
    )
