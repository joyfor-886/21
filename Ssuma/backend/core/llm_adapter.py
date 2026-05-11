"""
枢墨 LLM 适配层：模型检测、分级与能力适配

核心功能：
1. 模型检测：精确匹配 → 模糊匹配 → 参数量推断 → 能力测试
2. 模型分级：达标档(≥32B) / 基础档(≥6B) / 不足档(<6B)
3. 功能降级：根据模型档次自动调整七艺功能
4. 接入模式：本地模型(Ollama/LM Studio) / API Key / 混合模式
5. AI 声明：根据档次生成差异化文档声明

设计依据：2026-05-06-ssuma-zero-to-hero-design.md 第十三章
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import re
import json
import logging
import httpx
import asyncio

from core.llm_factory import LLMFactory, LLMProvider, OpenAICompatibleProvider

logger = logging.getLogger('Ssuma.LLMAdapter')


class ModelTier(Enum):
    """模型能力档次"""
    ADEQUATE = "adequate"      # 🟢 达标档 - 完整七艺可用
    BASIC = "basic"            # 🟡 基础档 - 部分功能降级
    INSUFFICIENT = "insufficient"  # 🔴 不足档 - 仅启枢可用

    @property
    def label(self) -> str:
        labels = {
            ModelTier.ADEQUATE: "🟢 达标档",
            ModelTier.BASIC: "🟡 基础档",
            ModelTier.INSUFFICIENT: "🔴 不足档"
        }
        return labels[self]

    @property
    def color(self) -> str:
        colors = {
            ModelTier.ADEQUATE: "#22c55e",  # green
            ModelTier.BASIC: "#eab308",       # yellow
            ModelTier.INSUFFICIENT: "#ef4444" # red
        }
        return colors[self]


@dataclass
class ModelInfo:
    """模型信息"""
    name: str
    provider: str
    tier: ModelTier
    tier_source: str  # "known" / "inferred" / "tested"
    raw_name: str     # 原始模型名称
    estimated_params: Optional[float] = None  # 估计参数量(B)


@dataclass
class CapabilityConfig:
    """根据模型档次的能力配置"""
    qishu_enabled: bool = True           # 启枢（对话引导）
    qishu_depth: str = "full"            # full / simplified
    caiheng_enabled: bool = True         # 裁衡（CEO审视）
    caiheng_challenge_dims: int = 3      # 挑战维度数量
    zhenwei_enabled: bool = True         # 甄微（技术评审）
    zhenwei_scope: str = "full"         # full / core_only
    ceshu_enabled: bool = True           # 策书（执行计划）
    ceshu_granularity: str = "5min"      # 5min / 30min / milestone
    ningmo_passes: int = 4               # 凝墨生成遍数
    powang_enabled: bool = True          # 破妄（需求覆盖）
    jianyan_enabled: bool = True         # 渐衍（分阶段）
    jianyan_stages: Optional[int] = None  # None表示不限


# 已知模型库（内置匹配表）
KNOWN_MODELS: Dict[str, ModelTier] = {
    # 🟢 达标档 (≥32B)
    "gpt-4o": ModelTier.ADEQUATE,
    "gpt-4-turbo": ModelTier.ADEQUATE,
    "gpt-4": ModelTier.ADEQUATE,
    "claude-sonnet-4": ModelTier.ADEQUATE,
    "claude-3.5-sonnet": ModelTier.ADEQUATE,
    "claude-3-opus": ModelTier.ADEQUATE,
    "deepseek-chat": ModelTier.ADEQUATE,
    "deepseek-v3": ModelTier.ADEQUATE,
    "deepseek-v2.5": ModelTier.ADEQUATE,
    "qwen2.5-72b": ModelTier.ADEQUATE,
    "qwen2.5-72b-instruct": ModelTier.ADEQUATE,
    "qwen-72b": ModelTier.ADEQUATE,
    "qwen-max": ModelTier.ADEQUATE,
    "glm-4": ModelTier.ADEQUATE,
    "glm-4-plus": ModelTier.ADEQUATE,
    "gemini-1.5-pro": ModelTier.ADEQUATE,
    "gemini-2.0-pro": ModelTier.ADEQUATE,
    "moonshot-v1-128k": ModelTier.ADEQUATE,
    "yi-large": ModelTier.ADEQUATE,

    # 🟡 基础档 (≥6B, <32B)
    "llama3-8b-instruct": ModelTier.BASIC,
    "llama3-8b": ModelTier.BASIC,
    "llama3.1-8b-instruct": ModelTier.BASIC,
    "llama3.1-70b-instruct": ModelTier.ADEQUATE,  # 70B 是达标档
    "llama2-13b-chat": ModelTier.BASIC,
    "qwen2.5-7b": ModelTier.BASIC,
    "qwen2.5-7b-instruct": ModelTier.BASIC,
    "qwen2.5-14b": ModelTier.BASIC,
    "qwen2.5-14b-instruct": ModelTier.BASIC,
    "qwen2.5-32b": ModelTier.BASIC,
    "qwen2-72b-chat": ModelTier.ADEQUATE,
    "mistral-7b-instruct": ModelTier.BASIC,
    "mistral-nemo": ModelTier.BASIC,
    "mistral-large": ModelTier.ADEQUATE,
    "deepseek-7b": ModelTier.BASIC,
    "deepseek-67b": ModelTier.ADEQUATE,
    "yi-6b-chat": ModelTier.BASIC,
    "yi-34b-chat": ModelTier.BASIC,
    "codegeex4-all": ModelTier.BASIC,
    "codestral-22b": ModelTier.BASIC,

    # 🔴 不足档 (<6B)
    "qwen2.5-1.5b": ModelTier.INSUFFICIENT,
    "qwen2.5-1.5b-instruct": ModelTier.INSUFFICIENT,
    "qwen2.5-0.5b": ModelTier.INSUFFICIENT,
    "qwen2.5-3b": ModelTier.INSUFFICIENT,
    "qwen2-7b-chat": ModelTier.BASIC,
    "qwen2-1.8b": ModelTier.INSUFFICIENT,
    "tinyllama": ModelTier.INSUFFICIENT,
    "phi-2": ModelTier.INSUFFICIENT,
    "phi-3-mini": ModelTier.INSUFFICIENT,
    "gemma-2b": ModelTier.INSUFFICIENT,
    "gemma-7b": ModelTier.BASIC,
    "starling-lm-7b": ModelTier.BASIC,
}


# 档次 → 能力配置映射
TIER_CAPABILITY_CONFIGS: Dict[ModelTier, CapabilityConfig] = {
    ModelTier.ADEQUATE: CapabilityConfig(
        qishu_enabled=True,
        qishu_depth="full",
        caiheng_enabled=True,
        caiheng_challenge_dims=3,
        zhenwei_enabled=True,
        zhenwei_scope="full",
        ceshu_enabled=True,
        ceshu_granularity="5min",
        ningmo_passes=4,
        powang_enabled=True,
        jianyan_enabled=True,
        jianyan_stages=None,
    ),
    ModelTier.BASIC: CapabilityConfig(
        qishu_enabled=True,
        qishu_depth="full",
        caiheng_enabled=True,
        caiheng_challenge_dims=2,
        zhenwei_enabled=True,
        zhenwei_scope="core_only",
        ceshu_enabled=True,
        ceshu_granularity="30min",
        ningmo_passes=2,
        powang_enabled=True,
        jianyan_enabled=True,
        jianyan_stages=3,
    ),
    ModelTier.INSUFFICIENT: CapabilityConfig(
        qishu_enabled=True,
        qishu_depth="simplified",
        caiheng_enabled=False,
        caiheng_challenge_dims=0,
        zhenwei_enabled=False,
        zhenwei_scope="none",
        ceshu_enabled=True,
        ceshu_granularity="milestone",
        ningmo_passes=1,
        powang_enabled=False,
        jianyan_enabled=False,
        jianyan_stages=1,
    ),
}


# 档次 → AI 声明模板
TIER_AI_DECLARATIONS: Dict[ModelTier, str] = {
    ModelTier.ADEQUATE: """⚠️ 本方案由枢墨（Ssuma）AI 辅助生成
- 生成模型：{model_name}（达标档）
- 建议在执行前进行技术可行性验证
- 关键决策点已标注 [需确认]
- 方案版本：v{version} | 生成时间：{timestamp}""",

    ModelTier.BASIC: """⚠️ 本方案由枢墨（Ssuma）AI 辅助生成
- 生成模型：{model_name}（基础档）
- ⚠️ 当前模型为基础档，方案质量可能受限
- 强烈建议对以下内容人工复核：
  · 技术架构选型
  · 数据库设计
  · API 接口定义
- 关键决策点已标注 [需确认]
- 方案版本：v{version} | 生成时间：{timestamp}""",

    ModelTier.INSUFFICIENT: """🚫 本方案由枢墨（Ssuma）AI 辅助生成
- 生成模型：{model_name}（不足档）
- 🚫 当前模型能力严重不足，本方案仅为基础框架
- 本方案不可直接用于生产级开发
- 强烈建议：
  · 更换为14B+参数的本地模型
  · 或配置 API Key（DeepSeek/OpenAI/Claude）
  · 重新生成以获得可用方案
- 关键决策点已标注 [需确认]
- 方案版本：v{version}-简化版 | 生成时间：{timestamp}""",
}


class LLMAdapter:
    """
    LLM 适配器：模型检测、分级与能力适配

    核心流程：
    1. detect_tier() - 检测模型档次
    2. get_capability_config() - 获取能力配置
    3. generate_ai_declaration() - 生成 AI 声明
    4. run_capability_test() - 能力测试（用于未知模型）
    """

    def __init__(self, llm_factory: LLMFactory):
        self.llm_factory = llm_factory
        self._model_cache: Dict[str, ModelInfo] = {}

    def normalize_model_name(self, model_name: str) -> str:
        """标准化模型名称，用于匹配"""
        return model_name.lower().replace(":", "-").replace("_", "-").replace(".", "-")

    def extract_params(self, model_name: str) -> Optional[float]:
        """从模型名称中提取参数量"""
        normalized = self.normalize_model_name(model_name)
        # 匹配如 "72b", "7b", "1.5b", "1.8b"
        match = re.search(r'(\d+\.?\d*)b', normalized)
        if match:
            return float(match.group(1))
        return None

    def detect_tier(self, model_name: str) -> ModelTier:
        """
        检测模型档次

        流程：
        1. 精确匹配已知模型库
        2. 模糊匹配（包含关系）
        3. 参数量推断
        4. 未知模型返回 BASIC（保守估计）
        """
        normalized = self.normalize_model_name(model_name)

        # Step 1: 精确匹配
        if normalized in KNOWN_MODELS:
            return KNOWN_MODELS[normalized]

        # Step 2: 模糊匹配
        for known, tier in KNOWN_MODELS.items():
            if known in normalized or normalized in known:
                return tier

        # Step 3: 参数量推断
        params = self.extract_params(normalized)
        if params is not None:
            if params >= 32:
                return ModelTier.ADEQUATE
            elif params >= 6:
                return ModelTier.BASIC
            else:
                return ModelTier.INSUFFICIENT

        # Step 4: 未知模型，保守返回 BASIC
        logger.warning(f"未知模型 {model_name}，保守估计为 BASIC 档")
        return ModelTier.BASIC

    async def run_capability_test(self, provider: LLMProvider, model_name: str) -> int:
        """
        运行能力测试（3道题，约10秒）

        返回分数 0-6：
        - 5-6 分 → 🟢 达标
        - 3-4 分 → 🟡 基础
        - 0-2 分 → 🔴 不足
        """
        test_prompts = [
            # 结构化输出测试
            ("结构化输出", """请用 JSON 格式输出一个待办事项列表，包含3个待办项，每项有 title、priority、due_date 三个字段。只输出 JSON，不要其他内容。"""),
            # 复杂推理测试
            ("复杂推理", """分析以下矛盾需求：「用户希望APP既简单易用，又功能强大」——这个矛盾的本质是什么？如何解决？请用50字以内回答。"""),
            # 长文档生成测试
            ("长文档", """用100字生成一个PRD摘要，包含：产品名称、核心功能（3条）、目标用户。不需要标题，直接写正文。"""),
        ]

        total_score = 0

        for test_name, prompt in test_prompts:
            try:
                response = await provider.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=500
                )

                # 简单评分逻辑
                score = self._evaluate_response(test_name, response)
                total_score += score
                logger.info(f"能力测试 {test_name}: {score}/2 分")

            except Exception as e:
                logger.error(f"能力测试 {test_name} 失败: {e}")

        return total_score

    def _evaluate_response(self, test_name: str, response: str) -> int:
        """评估回答质量，返回 0-2 分"""
        if not response or len(response.strip()) < 10:
            return 0

        if test_name == "结构化输出":
            # 检查是否是有效 JSON
            try:
                json.loads(response.strip())
                return 2  # 完美 JSON
            except:
                if "{" in response and "}" in response:
                    return 1  # 部分 JSON
                return 0

        elif test_name == "复杂推理":
            # 检查是否包含分析性内容
            keywords = ["矛盾", "平衡", "权衡", "本质", "解决", "冲突"]
            if any(kw in response for kw in keywords):
                return 2
            elif len(response) > 20:
                return 1
            return 0

        elif test_name == "长文档":
            # 检查内容长度和结构
            if len(response) >= 80 and any(kw in response for kw in ["功能", "用户", "产品"]):
                return 2
            elif len(response) >= 40:
                return 1
            return 0

        return 1  # 默认给1分

    def get_capability_config(self, tier: ModelTier) -> CapabilityConfig:
        """获取模型档次对应的能力配置"""
        return TIER_CAPABILITY_CONFIGS[tier]

    def generate_ai_declaration(
        self,
        tier: ModelTier,
        model_name: str,
        version: str = "1.0",
        timestamp: Optional[str] = None
    ) -> str:
        """生成 AI 声明"""
        if timestamp is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d")

        template = TIER_AI_DECLARATIONS[tier]
        return template.format(
            model_name=model_name,
            version=version,
            timestamp=timestamp
        )

    async def detect_and_configure(
        self,
        provider_name: str,
        model_name: str,
        run_test: bool = False
    ) -> ModelInfo:
        """
        检测并配置模型

        返回 ModelInfo 包含完整的模型信息
        """
        provider = self.llm_factory.get_provider(provider_name)

        # 检测档次
        tier = self.detect_tier(model_name)
        tier_source = "known" if model_name.lower() in KNOWN_MODELS else "inferred"

        # 如果需要能力测试且模型未知
        if run_test and tier_source != "known":
            try:
                score = await self.run_capability_test(provider, model_name)
                if score >= 5:
                    tier = ModelTier.ADEQUATE
                elif score >= 3:
                    tier = ModelTier.BASIC
                else:
                    tier = ModelTier.INSUFFICIENT
                tier_source = "tested"
                logger.info(f"能力测试结果: {score}/6 分 → {tier.label}")
            except Exception as e:
                logger.error(f"能力测试失败: {e}，使用推断档次")

        model_info = ModelInfo(
            name=model_name,
            provider=provider_name,
            tier=tier,
            tier_source=tier_source,
            raw_name=model_name,
            estimated_params=self.extract_params(model_name)
        )

        # 缓存结果
        self._model_cache[model_name] = model_info
        return model_info


class LLMConfigManager:
    """
    LLM 配置管理器：处理用户配置、模型切换、混合模式
    """

    def __init__(self, db_path: str = "./ssuma.db"):
        self.db_path = db_path
        self._config_cache: Dict[str, Any] = {}

    def get_user_llm_config(self, user_id: str = "default") -> Dict[str, Any]:
        """获取用户 LLM 配置"""
        # TODO: 从数据库读取
        return self._config_cache.get(user_id, {
            "mode": "local",  # local / api / mixed
            "chat_model": {
                "provider": "ollama",
                "model": "qwen2.5:7b"
            },
            "generate_model": {
                "provider": "deepseek",
                "model": "deepseek-chat"
            }
        })

    def save_user_llm_config(self, user_id: str, config: Dict[str, Any]) -> bool:
        """保存用户 LLM 配置"""
        self._config_cache[user_id] = config
        # TODO: 写入数据库
        return True

    async def test_connection(
        self,
        provider_type: str,
        base_url: str,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """测试 LLM 连接"""
        try:
            if provider_type == "ollama":
                # Ollama 特殊处理
                client = httpx.AsyncClient(timeout=10.0)
                resp = await client.get(f"{base_url}/api/tags")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    return {
                        "success": True,
                        "available_models": [m.get("name", "") for m in models],
                        "detected_model": models[0].get("name", "") if models else None
                    }
            else:
                # 通用 OpenAI 兼容接口
                config = {
                    "base_url": base_url,
                    "api_key": api_key or "dummy",
                    "model": model_name or "auto"
                }
                provider = OpenAICompatibleProvider(config)
                response = await provider.chat(
                    messages=[{"role": "user", "content": "Hi"}],
                    max_tokens=10
                )
                return {
                    "success": True,
                    "detected_model": model_name,
                    "response_preview": response[:50] if response else ""
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def list_available_models(
        self,
        provider_type: str,
        base_url: str,
        api_key: Optional[str] = None
    ) -> List[str]:
        """列出可用模型"""
        try:
            if provider_type == "ollama":
                client = httpx.AsyncClient(timeout=10.0)
                resp = await client.get(f"{base_url}/api/tags")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    return [m.get("name", "") for m in models]
            elif provider_type in ["lm_studio", "openai", "deepseek", "claude"]:
                # 这些使用标准 API，模型列表通过配置获取
                return []
        except Exception as e:
            logger.error(f"列出可用模型失败: {e}")
        return []


# 全局实例
_llm_adapter: Optional[LLMAdapter] = None
_llm_config_manager: Optional[LLMConfigManager] = None


def get_llm_adapter() -> LLMAdapter:
    """获取 LLM 适配器全局实例"""
    global _llm_adapter
    if _llm_adapter is None:
        _llm_adapter = LLMAdapter(LLMFactory)
    return _llm_adapter


def get_llm_config_manager() -> LLMConfigManager:
    """获取 LLM 配置管理器全局实例"""
    global _llm_config_manager
    if _llm_config_manager is None:
        _llm_config_manager = LLMConfigManager()
    return _llm_config_manager
