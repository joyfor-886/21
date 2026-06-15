from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import OpenAI, AsyncOpenAI
from anthropic import Anthropic, AsyncAnthropic
from core.config import Config
import httpx
import asyncio
import logging

DEFAULT_TIMEOUT = 300.0

DEFAULT_MAX_RETRIES = 2

logger = logging.getLogger('Ssuma.LLM')


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        pass

    @abstractmethod
    def chat_sync(self, messages: List[Dict[str, str]], **kwargs) -> str:
        pass

    @abstractmethod
    async def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        pass


class OpenAIStyleProvider(LLMProvider):
    DEFAULT_PARAMS = {"temperature": 0.7, "top_p": 0.9, "frequency_penalty": 0.0, "presence_penalty": 0.0}
    _log_name = "LLM"

    def __init__(self, config: Dict[str, Any]):
        self.model = config.get("model", "")
        self.base_url = config.get("base_url", "")
        self.api_key = config.get("api_key", "") or "dummy"
        self.timeout = config.get("timeout", DEFAULT_TIMEOUT)
        self.max_retries = config.get("max_retries", DEFAULT_MAX_RETRIES)

        timeout_config = httpx.Timeout(timeout=self.timeout, connect=10.0)
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=timeout_config
        )
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=timeout_config
        )

    def _extract_content(self, message) -> str:
        return message.content or ""

    def _process_delta(self, delta):
        if delta.content:
            return delta.content
        return None

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        params = {**self.DEFAULT_PARAMS, **kwargs}

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await self.async_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    **params
                )
                return self._extract_content(response.choices[0].message)
            except Exception as e:
                last_error = e
                logger.warning(f"{self._log_name} 请求失败 (尝试 {attempt + 1}/{self.max_retries + 1}): {str(e)}")
                if attempt < self.max_retries:
                    await asyncio.sleep(1 * (attempt + 1))
        raise last_error

    async def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        params = {**self.DEFAULT_PARAMS, **kwargs}

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                stream = await self.async_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=True,
                    **params
                )
                async for chunk in stream:
                    content = self._process_delta(chunk.choices[0].delta)
                    if content:
                        yield content
                return
            except Exception as e:
                last_error = e
                logger.warning(f"{self._log_name} 流式请求失败 (尝试 {attempt + 1}/{self.max_retries + 1}): {str(e)}")
                if attempt < self.max_retries:
                    await asyncio.sleep(1 * (attempt + 1))
        if last_error:
            raise last_error

    def chat_sync(self, messages: List[Dict[str, str]], **kwargs) -> str:
        params = {**self.DEFAULT_PARAMS, **kwargs}
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **params
        )
        return self._extract_content(response.choices[0].message)


class LMStudioProvider(OpenAIStyleProvider):
    DEFAULT_PARAMS = {**OpenAIStyleProvider.DEFAULT_PARAMS, "max_tokens": -1}
    _log_name = "LM Studio"

    def __init__(self, config: Dict[str, Any]):
        config = dict(config)
        if not config.get("base_url"):
            config["base_url"] = "http://127.0.0.1:1234/v1"
        super().__init__(config)
        self._auto_detect_model()

    def _extract_content(self, message) -> str:
        content = message.content
        if not content or not content.strip():
            reasoning = getattr(message, 'reasoning_content', None)
            if reasoning and reasoning.strip():
                content = reasoning
        return self._strip_thinking(content or "")

    @staticmethod
    def _strip_thinking(text: str) -> str:
        import re
        stripped = text

        stripped = re.sub(
            r'^\s*<think\b[^>]*>.*?</think\s*>\s*',
            '', stripped, count=1, flags=re.DOTALL
        )

        stripped = re.sub(
            r'^\s*Thinking Process:.*?(?=\n[^\s*]|\n\n)',
            '', stripped, count=1, flags=re.DOTALL
        )

        stripped = re.sub(
            r'(?:^|\n)\s*\d+\.\s+\*\*[^*]+\*\*:.*?(?=(?:\n\s*\d+\.\s+\*\*)|(?:\n\n)|$)',
            '', stripped, flags=re.DOTALL
        )

        stripped = re.sub(
            r'(?:^|\n)\s*\d+\.\s+\*\*[^*]+\*\*\s*(?=\n)',
            '', stripped
        )

        stripped = re.sub(
            r'(?:^|\n)\s*\*\*Self[- ]?Correction[^*]*\*\*.*?(?=(?:\n\s*\d+\.)|(?:\n\n)|$)',
            '', stripped, flags=re.DOTALL
        )

        stripped = re.sub(
            r'(?:^|\n)\s*\*\*Decision\*\*.*?(?=(?:\n\s*\d+\.)|(?:\n\n)|$)',
            '', stripped, flags=re.DOTALL
        )

        stripped = re.sub(
            r'(?:^|\n)\s*\*\*Drafting[^*]*\*\*.*?(?=(?:\n\s*\d+\.)|(?:\n\n)|$)',
            '', stripped, flags=re.DOTALL
        )

        stripped = re.sub(
            r'(?:^|\n)\s*\(Self[- ]?Correction[^)]*\)\s*',
            '', stripped
        )

        stripped = re.sub(
            r'(?:^|\n)\s*\*\*Final Polish[^*]*\*\*.*?(?=(?:\n\s*\d+\.)|(?:\n\n)|$)',
            '', stripped, flags=re.DOTALL
        )

        lines = stripped.split('\n')
        filtered = []
        for line in lines:
            if re.match(r'^\s*\d+\.\s+\*\*(Analyze|Determine|Check|Identify|Evaluate|Re-?evaluate|Self-?Correction|Decision|Drafting|Final)', line, re.IGNORECASE):
                continue
            if re.match(r'^\s*\d+\.\s+\*\*[A-Z][a-z]+[^*]*\*\*:', line):
                continue
            filtered.append(line)
        stripped = '\n'.join(filtered)

        stripped = re.sub(r'\n{3,}', '\n\n', stripped)

        return stripped.strip() if stripped.strip() else text.strip()

    def _process_delta(self, delta):
        if delta.content:
            return delta.content
        if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
            return delta.reasoning_content
        return None

    def _auto_detect_model(self):
        """验证 LM Studio 中用户配置的模型是否可用。

        策略：
        1. 仅验证用户配置的模型一次
        2. 不遍历测试所有模型（避免用户加载大量模型时导致系统卡顿）
        3. 配置无效时只记录警告，不做自动回退，让用户自行处理
        """
        try:
            import httpx as _httpx
            models_url = self.base_url.rstrip("/") + "/models"
            resp = _httpx.get(models_url, timeout=5.0)
            if resp.status_code != 200:
                logger.warning(f"LM Studio /models 端点返回 {resp.status_code}")
                return
            data = resp.json().get("data", [])
            if not data:
                logger.warning("LM Studio /models 端点返回空列表")
                return

            configured = self.model
            if not configured:
                logger.warning("LM Studio 未配置模型，请在设置中指定模型名称")
                return

            # 只验证用户配置的模型一次
            try:
                test_resp = _httpx.post(
                    self.base_url.rstrip("/") + "/chat/completions",
                    json={
                        "model": configured,
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 3,
                    },
                    timeout=8.0,
                )
                if test_resp.status_code == 200:
                    logger.info(f"LM Studio configured model verified: {self.model}")
                    return
                else:
                    logger.warning(
                        f"LM Studio 配置的模型 '{configured}' 不可用 "
                        f"(HTTP {test_resp.status_code})。"
                        f"请检查模型是否已加载，或在设置中更换模型。"
                    )
            except Exception as e:
                logger.warning(
                    f"LM Studio 配置的模型 '{configured}' 验证失败: {e}。"
                    f"请检查 LM Studio 是否正常运行，或在设置中更换模型。"
                )
        except Exception as e:
            logger.warning(f"LM Studio model auto-detect failed: {e}")


class OpenAICompatibleProvider(OpenAIStyleProvider):
    pass


class OpenAIProvider(OpenAIStyleProvider):
    def __init__(self, config: Dict[str, Any]):
        self.model = config.get("model", "gpt-4o")
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.timeout = config.get("timeout", DEFAULT_TIMEOUT)
        self.max_retries = config.get("max_retries", DEFAULT_MAX_RETRIES)

        timeout_config = httpx.Timeout(timeout=self.timeout, connect=10.0)
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=timeout_config)
        self.async_client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url, timeout=timeout_config)


class ClaudeProvider(LLMProvider):
    def __init__(self, config: Dict[str, Any]):
        self.model = config.get("model", "claude-sonnet-4-20250514")
        self.api_key = config.get("api_key", "")
        self.timeout = config.get("timeout", DEFAULT_TIMEOUT)

        timeout_config = httpx.Timeout(timeout=self.timeout, connect=10.0)
        self.client = Anthropic(api_key=self.api_key, timeout=timeout_config)
        self.async_client = AsyncAnthropic(api_key=self.api_key, timeout=timeout_config)

    def _convert_messages(self, messages: List[Dict[str, str]]) -> tuple:
        system_prompt = ""
        converted = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                converted.append(msg)
        return system_prompt, converted

    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        system_prompt, converted = self._convert_messages(messages)
        response = await self.async_client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=converted,
            max_tokens=kwargs.get("max_tokens", 4096),
            **{k: v for k, v in kwargs.items() if k != "max_tokens"}
        )
        return response.content[0].text

    async def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        system_prompt, converted = self._convert_messages(messages)
        stream = await self.async_client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=converted,
            max_tokens=kwargs.get("max_tokens", 4096),
            stream=True,
            **{k: v for k, v in kwargs.items() if k != "max_tokens" and k != "stream"}
        )
        async for chunk in stream:
            if chunk.type == "content_block_delta" and chunk.delta.text:
                yield chunk.delta.text

    def chat_sync(self, messages: List[Dict[str, str]], **kwargs) -> str:
        system_prompt, converted = self._convert_messages(messages)
        response = self.client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=converted,
            max_tokens=kwargs.get("max_tokens", 4096),
            **{k: v for k, v in kwargs.items() if k != "max_tokens"}
        )
        return response.content[0].text


class LLMFactory:
    _providers: Dict[str, LLMProvider] = {}
    _default_provider: str = ""
    _circuit_breakers: Dict[str, Any] = {}
    _init_lock: Optional[asyncio.Lock] = None
    _provider_configs: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def _get_init_lock(cls) -> asyncio.Lock:
        if cls._init_lock is None:
            cls._init_lock = asyncio.Lock()
        return cls._init_lock

    @classmethod
    def initialize(cls):
        config = Config()
        llm_config = config.llm
        cls._default_provider = llm_config.get("default_provider", "lm_studio")

        providers_config = llm_config.get("providers", {})
        for name, provider_cfg in providers_config.items():
            provider_type = provider_cfg.get("type", "openai_compatible")
            cls._provider_configs[name] = provider_cfg

            if provider_type == "openai":
                cls._providers[name] = OpenAIProvider(provider_cfg)
            elif provider_type == "anthropic":
                cls._providers[name] = ClaudeProvider(provider_cfg)
            elif provider_type == "lm_studio":
                cls._providers[name] = LMStudioProvider(provider_cfg)
            elif provider_type == "openai_compatible":
                cls._providers[name] = OpenAICompatibleProvider(provider_cfg)

            if name not in cls._circuit_breakers:
                from core.circuit_breaker import CircuitBreaker
                cls._circuit_breakers[name] = CircuitBreaker(
                    failure_threshold=3,
                    recovery_timeout=60.0,
                )

    @classmethod
    async def health_check(cls, name: Optional[str] = None) -> Dict[str, Any]:
        """检查 Provider 健康状态"""
        provider_name = name or cls._default_provider
        if provider_name not in cls._providers:
            return {"provider": provider_name, "healthy": False, "error": "not_found"}

        provider = cls._providers[provider_name]
        cb = cls._circuit_breakers.get(provider_name)

        try:
            response = await asyncio.wait_for(
                provider.chat(
                    [{"role": "user", "content": "Hi"}],
                    max_tokens=5,
                    temperature=0.1,
                ),
                timeout=10.0,
            )
            if cb:
                cb._on_success()
            return {
                "provider": provider_name,
                "healthy": True,
                "response_preview": response[:50] if response else "",
                "circuit_breaker": cb.stats() if cb else None,
            }
        except Exception as e:
            if cb:
                cb._on_failure()
            return {
                "provider": provider_name,
                "healthy": False,
                "error": str(e),
                "circuit_breaker": cb.stats() if cb else None,
            }

    @classmethod
    def reconnect(cls, name: Optional[str] = None) -> bool:
        """重新创建 Provider 实例"""
        provider_name = name or cls._default_provider
        if provider_name not in cls._provider_configs:
            logger.warning(f"Cannot reconnect '{provider_name}': no config stored")
            return False

        provider_cfg = cls._provider_configs[provider_name]
        provider_type = provider_cfg.get("type", "openai_compatible")

        try:
            if provider_type == "openai":
                cls._providers[provider_name] = OpenAIProvider(provider_cfg)
            elif provider_type == "anthropic":
                cls._providers[provider_name] = ClaudeProvider(provider_cfg)
            elif provider_type == "lm_studio":
                cls._providers[provider_name] = LMStudioProvider(provider_cfg)
            elif provider_type == "openai_compatible":
                cls._providers[provider_name] = OpenAICompatibleProvider(provider_cfg)

            cb = cls._circuit_breakers.get(provider_name)
            if cb:
                cb.reset()

            logger.info(f"Provider '{provider_name}' reconnected successfully")
            return True
        except Exception as e:
            logger.error(f"Provider '{provider_name}' reconnect failed: {e}")
            return False

    @classmethod
    def get_provider(cls, name: Optional[str] = None) -> LLMProvider:
        if not cls._providers:
            cls.initialize()

        provider_name = name or cls._default_provider
        if provider_name not in cls._providers:
            raise ValueError(f"Unknown LLM provider: {provider_name}. Available: {list(cls._providers.keys())}")

        cb = cls._circuit_breakers.get(provider_name)
        if cb and cb.state == "open":
            from core.circuit_breaker import CircuitBreakerOpenError
            raise CircuitBreakerOpenError(
                f"Provider '{provider_name}' is circuit-broken. "
                f"Stats: {cb.stats()}"
            )

        return cls._providers[provider_name]

    @classmethod
    def get_circuit_breaker(cls, name: Optional[str] = None) -> Any:
        provider_name = name or cls._default_provider
        return cls._circuit_breakers.get(provider_name)

    @classmethod
    def reset_circuit_breaker(cls, name: Optional[str] = None):
        provider_name = name or cls._default_provider
        cb = cls._circuit_breakers.get(provider_name)
        if cb:
            cb.reset()

    @classmethod
    def list_providers(cls) -> List[str]:
        if not cls._providers:
            cls.initialize()
        return list(cls._providers.keys())

    @classmethod
    def get_default_provider(cls) -> str:
        return cls._default_provider
