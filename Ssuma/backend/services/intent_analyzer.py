from typing import Dict, Any, List, Optional
import json
import logging

from domain.enums import UserIntent, ClarityLevel
from domain.results import IntentAnalysisResult, INTENT_LABELS

logger = logging.getLogger(__name__)


INTENT_DESCRIPTIONS = {
    UserIntent.QISHU: "帮助用户澄清想法，通过问答引导深入思考",
    UserIntent.TANYIN: "通过探隐阶段系统化收集需求信息",
    UserIntent.CAIHENG: "从CEO视角审视产品价值和范围",
    UserIntent.ZHENWEI: "讨论技术架构和实现细节",
    UserIntent.CESHU: "拆分为可执行的实施任务",
    UserIntent.NINGMO: "生成完整的AI可执行项目方案",
    UserIntent.CHAT: "普通对话，不进入特定工作流",
}


class FlowState:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.current_intent: Optional[UserIntent] = None
        self.current_clarity: ClarityLevel = ClarityLevel.PARTIAL
        self.workflow_history: List[Dict[str, Any]] = []
        self.conversation_turns = 0
        self.tanyin_completed = False
        self.analysis_completed = False
        self.plan_completed = False
        self.spec_generated = False
        self.channel: str = "standard"
        self.phase_completion: Dict[str, float] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "current_intent": self.current_intent.value if self.current_intent else None,
            "current_clarity": self.current_clarity.value,
            "workflow_history": self.workflow_history,
            "conversation_turns": self.conversation_turns,
            "tanyin_completed": self.tanyin_completed,
            "analysis_completed": self.analysis_completed,
            "plan_completed": self.plan_completed,
            "spec_generated": self.spec_generated,
            "channel": self.channel,
            "phase_completion": self.phase_completion,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FlowState":
        state = cls(project_id=data.get("project_id", ""))
        intent_val = data.get("current_intent")
        if intent_val:
            try:
                state.current_intent = UserIntent(intent_val)
            except ValueError:
                state.current_intent = None
        clarity_val = data.get("current_clarity", "partial")
        try:
            state.current_clarity = ClarityLevel(clarity_val)
        except ValueError:
            state.current_clarity = ClarityLevel.PARTIAL
        state.workflow_history = data.get("workflow_history", [])
        state.conversation_turns = data.get("conversation_turns", 0)
        state.tanyin_completed = data.get("tanyin_completed", False)
        state.analysis_completed = data.get("analysis_completed", False)
        state.plan_completed = data.get("plan_completed", False)
        state.spec_generated = data.get("spec_generated", False)
        state.channel = data.get("channel", "standard")
        state.phase_completion = data.get("phase_completion", {})
        return state


class IntentAnalyzer:
    _instances: Dict[str, FlowState] = {}
    MAX_INMEMORY_PROJECTS = 200

    STATE_SERVICE_NAME = "intent_analyzer"

    @classmethod
    def _evict_if_needed(cls):
        if len(cls._instances) <= cls.MAX_INMEMORY_PROJECTS:
            return
        excess = len(cls._instances) - cls.MAX_INMEMORY_PROJECTS
        keys_to_evict = sorted(
            cls._instances.keys(),
            key=lambda k: cls._instances[k].conversation_turns
        )[:excess]
        for key in keys_to_evict:
            del cls._instances[key]
            logger.info(f"IntentAnalyzer evicted project {key} (LRU)")

    @classmethod
    def _ensure_loaded(cls, project_id: str):
        if project_id not in cls._instances:
            from core.state_repository import StateRepository
            data = StateRepository.load(cls.STATE_SERVICE_NAME, project_id)
            if data is not None:
                cls._instances[project_id] = FlowState.from_dict(data)
            else:
                cls._instances[project_id] = FlowState(project_id)
            cls._evict_if_needed()

    @classmethod
    def _save_to_repo(cls, project_id: str):
        from core.state_repository import StateRepository
        state = cls._instances.get(project_id)
        if state:
            StateRepository.save(cls.STATE_SERVICE_NAME, project_id, state.to_dict())

    @classmethod
    def get_state(cls, project_id: str) -> FlowState:
        cls._ensure_loaded(project_id)
        if project_id not in cls._instances:
            cls._instances[project_id] = FlowState(project_id)
        return cls._instances[project_id]

    @classmethod
    def reset_state(cls, project_id: str):
        if project_id in cls._instances:
            del cls._instances[project_id]
        from core.state_repository import StateRepository
        StateRepository.delete(cls.STATE_SERVICE_NAME, project_id)

    @classmethod
    def update_state(cls, project_id: str, updates: Dict[str, Any]):
        state = cls.get_state(project_id)
        for key, value in updates.items():
            if hasattr(state, key):
                setattr(state, key, value)
        cls._save_to_repo(project_id)

    @classmethod
    async def analyze(
        cls,
        project_id: str,
        message: str,
        conversation_history: str = "",
        force_workflow: Optional[str] = None
    ) -> IntentAnalysisResult:
        """分析用户意图并推荐工作流

        优化策略：
        - 首条消息：使用 LLM 分析（需要理解上下文）
        - force_workflow：直接映射（零延迟）
        - 后续消息：优先规则匹配（<1ms），仅在工作流切换时调用 LLM
        """

        if force_workflow:
            return cls._analyze_forced_workflow(force_workflow, message)

        state = cls.get_state(project_id)

        has_history = bool(conversation_history.strip())

        if not has_history and state.conversation_turns == 0:
            result = await cls._analyze_initial_message(message, state)
        elif state.conversation_turns <= 1:
            result = cls._rule_based_analysis(message, state)
            if result is None or result.context.get("workflow_change"):
                result = await cls._analyze_continuation(message, conversation_history, state)
            elif result.intent == UserIntent.CHAT and has_history:
                result = await cls._analyze_continuation(message, conversation_history, state)
        else:
            result = cls._rule_based_analysis(message, state)
            if result is None:
                result = await cls._analyze_continuation(message, conversation_history, state)
            elif result.intent == UserIntent.CHAT and has_history:
                result = await cls._analyze_continuation(message, conversation_history, state)

        state.current_intent = result.intent
        state.current_clarity = result.clarity
        state.conversation_turns += 1
        cls._save_to_repo(project_id)

        return result

    @classmethod
    def _rule_based_analysis(cls, message: str, state: FlowState) -> Optional[IntentAnalysisResult]:
        """基于规则和当前状态的快速意图判断（不调用 LLM）

        返回 None 表示规则无法判断，需要回退到 LLM 分析。
        """
        keyword_intent = cls._keyword_override(message, state.current_intent or UserIntent.CHAT)

        if keyword_intent != state.current_intent:
            return IntentAnalysisResult(
                intent=keyword_intent,
                clarity=state.current_clarity,
                confidence=0.7,
                reasoning="基于关键词的状态内分析",
                recommended_workflow=keyword_intent.value,
                next_action=cls._get_next_action(keyword_intent),
                context={"rule_based": True, "workflow_change": True}
            )

        return IntentAnalysisResult(
            intent=state.current_intent or UserIntent.CHAT,
            clarity=state.current_clarity,
            confidence=0.8,
            reasoning="保持当前工作流",
            recommended_workflow=(state.current_intent or UserIntent.CHAT).value,
            next_action=cls._get_next_action(state.current_intent or UserIntent.CHAT),
            context={"rule_based": True, "unchanged": True}
        )

    @classmethod
    def _analyze_forced_workflow(
        cls,
        workflow: str,
        message: str
    ) -> IntentAnalysisResult:
        """强制使用特定工作流

        [BUG FIX] 修复了原来使用不存在的枚举值的问题：
        - UserIntent.BRAINSTORM → UserIntent.QISHU
        - UserIntent.CEO_REVIEW → UserIntent.CAIHENG
        - UserIntent.ENG_REVIEW → UserIntent.ZHENWEI
        - UserIntent.PLAN_WRITING → UserIntent.CESHU
        - UserIntent.SPEC_GENERATE → UserIntent.NINGMO
        """
        workflow_map = {
            "qishu": UserIntent.QISHU,
            "tanyin": UserIntent.TANYIN,
            "caiheng": UserIntent.CAIHENG,
            "zhenwei": UserIntent.ZHENWEI,
            "ceshu": UserIntent.CESHU,
            "ningmo": UserIntent.NINGMO,
            "chat": UserIntent.CHAT,
        }

        intent = workflow_map.get(workflow, UserIntent.CHAT)

        return IntentAnalysisResult(
            intent=intent,
            clarity=ClarityLevel.CLEAR,
            confidence=1.0,
            reasoning=f"用户明确选择了 {workflow} 工作流",
            recommended_workflow=workflow,
            next_action=cls._get_next_action(intent),
            context={"forced": True}
        )

    @classmethod
    async def _analyze_initial_message(
        cls,
        message: str,
        state: FlowState
    ) -> IntentAnalysisResult:
        """分析用户的第一条消息

        [BUG FIX] LLM prompt 中的 intent 枚举值必须与 UserIntent 一致：
        "qishu" | "tanyin" | "caiheng" | "zhenwei" | "ceshu" | "ningmo" | "chat"
        """
        from core.llm_factory import LLMFactory

        prompt = f"""你是一位AI产品助手。请分析用户的输入，判断其需求的清晰程度和意图。你必须始终使用中文回复。

用户输入: "{message}"

请分析以下方面：
1. 需求清晰程度：用户的需求有多明确？是模糊地描述想法，还是已经有清晰的目标？
2. 用户意图：用户想要做什么？头脑风暴？澄清需求？生成方案？还是只是闲聊？
3. 紧迫程度：用户是否急于要结果，还是只是探索可能性？

请以JSON格式输出分析结果：
{{
    "clarity": "fuzzy" | "partial" | "clear" | "technical",
    "intent": "qishu" | "tanyin" | "caiheng" | "zhenwei" | "ceshu" | "ningmo" | "chat",
    "confidence": 0.0-1.0,
    "reasoning": "简短的分析说明（50字以内）",
    "key_insights": ["用户可能真正想要的", "可能的盲点"],
    "suggested_approach": "建议的下一步动作"
}}

只输出JSON，不要其他内容。"""

        try:
            provider = LLMFactory.get_provider()
            response = await provider.chat(
                [{"role": "user", "content": prompt}],
                max_tokens=3000,
                temperature=0.3
            )

            result = cls._extract_json(response)

            clarity = ClarityLevel(result.get("clarity", "partial"))

            # [BUG FIX] 使用正确的枚举值映射
            intent = cls._parse_intent(result.get("intent", "chat"))
            # 关键词二次校验：如果 LLM 返回的意图与用户输入的关键词明显不符，修正
            intent = cls._keyword_override(message, intent)

            # 根据首条消息判定通道类型
            channel = cls._determine_channel(clarity, result.get("confidence", 0.5))
            state.channel = channel

            return IntentAnalysisResult(
                intent=intent,
                clarity=clarity,
                confidence=result.get("confidence", 0.5),
                reasoning=result.get("reasoning", ""),
                recommended_workflow=intent.value,
                next_action=result.get("suggested_approach", cls._get_next_action(intent)),
                context={
                    "key_insights": result.get("key_insights", []),
                    "is_initial": True,
                    "channel": channel,
                }
            )
        except Exception as e:
            logger.warning(f"Intent analysis failed: {e}, using fallback")
            return cls._fallback_analysis(message)

    @classmethod
    async def _analyze_continuation(
        cls,
        message: str,
        conversation_history: str,
        state: FlowState
    ) -> IntentAnalysisResult:
        """分析对话的持续内容，判断是否需要切换工作流

        [BUG FIX] LLM prompt 中的 intent 枚举值与 UserIntent 保持一致
        """
        from core.llm_factory import LLMFactory

        prompt = f"""你是一位AI产品助手。请分析对话历史，判断用户当前的意图和需求清晰程度。你必须始终使用中文回复。

对话历史（最近5轮）:
{conversation_history}

最新消息: "{message}"

请分析：
1. 需求是否变得更加清晰？还是越来越模糊？
2. 用户是否暗示想要转换到其他工作流？
3. 当前是否已经收集了足够的信息来生成方案？
4. 用户是否在寻求确认、建议还是只是闲聊？

请以JSON格式输出：
{{
    "clarity": "fuzzy" | "partial" | "clear" | "technical",
    "intent": "qishu" | "tanyin" | "caiheng" | "zhenwei" | "ceshu" | "ningmo" | "chat",
    "confidence": 0.0-1.0,
    "reasoning": "分析说明（50字以内）",
    "workflow_change": true | false,
    "change_reason": "如果切换工作流，说明原因",
    "suggested_approach": "建议的下一步"
}}

只输出JSON，不要其他内容。"""

        try:
            provider = LLMFactory.get_provider()
            response = await provider.chat(
                [{"role": "user", "content": prompt}],
                max_tokens=3000,
                temperature=0.3
            )

            result = cls._extract_json(response)

            clarity = ClarityLevel(result.get("clarity", "partial"))
            intent = cls._parse_intent(result.get("intent", "chat"))
            intent = cls._keyword_override(message, intent)

            return IntentAnalysisResult(
                intent=intent,
                clarity=clarity,
                confidence=result.get("confidence", 0.5),
                reasoning=result.get("reasoning", ""),
                recommended_workflow=intent.value,
                next_action=result.get("suggested_approach", cls._get_next_action(intent)),
                context={
                    "workflow_change": result.get("workflow_change", False),
                    "change_reason": result.get("change_reason", ""),
                    "is_initial": False,
                    "channel": state.channel,
                }
            )
        except Exception as e:
            logger.warning(f"Continuation analysis failed: {e}")
            return cls._fallback_analysis(message)

    @classmethod
    def _keyword_override(cls, message: str, intent: UserIntent) -> UserIntent:
        """关键词二次校验：当 LLM 意图与用户输入关键词明显不符时修正

        本地小模型可能对意图分类不够准确，关键词校验作为安全网。
        """
        msg_lower = message.lower()

        # 强关键词映射（优先级高于 LLM 结果）
        strong_patterns = {
            UserIntent.QISHU: ["我想做", "帮我做", "我想开发", "我想创建", "帮我设计", "我需要做", "想要一个", "想做个", "做个app", "做个应用"],
            UserIntent.ZHENWEI: ["技术栈", "架构设计", "api设计", "数据库设计", "实现方案", "技术实现"],
            UserIntent.NINGMO: ["生成方案", "完整方案", "生成项目", "出方案", "写方案", "完整项目方案"],
            UserIntent.CESHU: ["实施计划", "任务拆分", "里程碑", "排期", "开发计划"],
            UserIntent.CAIHENG: ["产品价值", "商业模式", "ceo审视", "产品审视", "盈利模式"],
        }

        for expected_intent, keywords in strong_patterns.items():
            if any(kw in msg_lower for kw in keywords):
                if intent != expected_intent:
                    logger.info(f"Keyword override: {intent.value} -> {expected_intent.value} for message: {message[:30]}")
                    return expected_intent

        return intent

    @classmethod
    def _extract_json(cls, text: str) -> dict:
        """从 LLM 响应中提取 JSON，兼容 thinking 模型的推理内容

        Qwen3 等 thinking 模型可能将 JSON 放在 reasoning_content 中，
        也可能将思考过程和 JSON 混在一起输出。此方法：
        1. 先尝试直接解析
        2. 提取 ```json ... ``` 代码块
        3. 用正则匹配最外层 { }
        4. 尝试修复截断的 JSON
        """
        import re

        if not text or not text.strip():
            raise ValueError("Empty response from LLM")

        # 尝试1：直接解析
        cleaned = text.strip().strip("```json").strip("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 尝试2：提取 ```json ... ``` 代码块
        json_block = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if json_block:
            try:
                return json.loads(json_block.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 尝试3：用正则匹配最外层 { }
        brace_pattern = re.search(r'\{[\s\S]*\}', text)
        if brace_pattern:
            candidate = brace_pattern.group(0)
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                # 尝试4：修复截断的 JSON
                repaired = cls._repair_truncated_json(candidate)
                if repaired:
                    return repaired

        # 尝试5：找最长的 { 开头的片段并修复
        brace_start = re.search(r'\{', text)
        if brace_start:
            fragment = text[brace_start.start():]
            repaired = cls._repair_truncated_json(fragment)
            if repaired:
                return repaired

        raise ValueError(f"Cannot extract JSON from response: {text[:200]}")

    @classmethod
    def _repair_truncated_json(cls, text: str) -> dict | None:
        """尝试修复被截断的 JSON（max_tokens 不足导致）

        策略：先去掉尾部不完整内容，再补全闭合括号。
        """
        import re

        text = text.strip()

        # 先去掉尾部的逗号
        text = text.rstrip(',')

        # 尝试直接解析（可能只是多了个逗号）
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

        # 补全闭合括号
        def try_close(t):
            open_braces = t.count('{') - t.count('}')
            open_brackets = t.count('[') - t.count(']')
            t2 = t
            if open_brackets > 0:
                t2 += ']' * open_brackets
            if open_braces > 0:
                t2 += '}' * open_braces
            try:
                result = json.loads(t2)
                return result if isinstance(result, dict) else None
            except json.JSONDecodeError:
                return None

        # 尝试1：直接补全
        r = try_close(text)
        if r:
            return r

        # 尝试2：去掉最后一个不完整的键值对（值没有闭合引号或括号）
        # 匹配 , "key": value 其中 value 不完整
        cleaned = re.sub(r',\s*"[^"]*"\s*:\s*"[^"]*$', '', text)  # 字符串值被截断
        r = try_close(cleaned)
        if r:
            return r

        cleaned = re.sub(r',\s*"[^"]*"\s*:\s*\[[^\]]*$', '', text)  # 数组值被截断
        r = try_close(cleaned)
        if r:
            return r

        cleaned = re.sub(r',\s*"[^"]*"\s*:\s*\{[^}]*$', '', text)  # 对象值被截断
        r = try_close(cleaned)
        if r:
            return r

        # 尝试3：更激进 - 去掉最后一个键值对
        cleaned = re.sub(r',\s*"[^"]*"\s*:\s*[^,}]*$', '', text)
        r = try_close(cleaned)
        if r:
            return r

        return None

    @classmethod
    def _parse_intent(cls, intent_str: str) -> UserIntent:
        """安全解析意图字符串为枚举值

        [BUG FIX] 兼容旧版 LLM 可能返回的错误枚举值
        """
        try:
            return UserIntent(intent_str)
        except ValueError:
            pass

        legacy_map = {
            "brainstorm": UserIntent.QISHU,
            "ceo_review": UserIntent.CAIHENG,
            "eng_review": UserIntent.ZHENWEI,
            "plan_writing": UserIntent.CESHU,
            "spec_generate": UserIntent.NINGMO,
        }
        return legacy_map.get(intent_str, UserIntent.CHAT)

    @classmethod
    def _determine_channel(cls, clarity: ClarityLevel, confidence: float) -> str:
        """根据首条消息判定通道类型

        参考 Garry Tan /gstack 的工作流分层模式：
        - 快速通道（3步）：启枢 → 裁衡 → 凝墨
        - 标准通道（5步）：启枢 → 探隐 → 裁衡 → 甄微 → 凝墨
        - 深度通道（7步）：全阶段
        """
        if clarity == ClarityLevel.CLEAR and confidence > 0.8:
            return "fast"
        elif clarity == ClarityLevel.FUZZY:
            return "deep"
        else:
            return "standard"

    @classmethod
    def _fallback_analysis(cls, message: str) -> IntentAnalysisResult:
        """备用分析逻辑（当LLM调用失败时）

        [BUG FIX] 修复了原来使用不存在的枚举值的问题：
        - UserIntent.BRAINSTORM → UserIntent.QISHU
        - UserIntent.ENG_REVIEW → UserIntent.ZHENWEI
        - UserIntent.CEO_REVIEW → UserIntent.CAIHENG
        - UserIntent.PLAN_WRITING → UserIntent.CESHU
        - UserIntent.SPEC_GENERATE → UserIntent.NINGMO
        """
        message_lower = message.lower()

        if any(kw in message_lower for kw in ["生成方案", "spec", "方案", "完整项目"]):
            intent = UserIntent.NINGMO
            clarity = ClarityLevel.CLEAR
        elif any(kw in message_lower for kw in ["技术", "架构", "实现", "api"]):
            intent = UserIntent.ZHENWEI
            clarity = ClarityLevel.TECHNICAL
        elif any(kw in message_lower for kw in ["ceo", "产品价值", "商业模式"]):
            intent = UserIntent.CAIHENG
            clarity = ClarityLevel.CLEAR
        elif any(kw in message_lower for kw in ["计划", "task", "实施", "milestone"]):
            intent = UserIntent.CESHU
            clarity = ClarityLevel.CLEAR
        elif any(kw in message_lower for kw in ["探隐", "问卷", "问问题", "需求收集"]):
            intent = UserIntent.TANYIN
            clarity = ClarityLevel.PARTIAL
        else:
            intent = UserIntent.QISHU
            clarity = ClarityLevel.PARTIAL

        return IntentAnalysisResult(
            intent=intent,
            clarity=clarity,
            confidence=0.6,
            reasoning="基于关键词的fallback分析",
            recommended_workflow=intent.value,
            next_action=cls._get_next_action(intent),
            context={"fallback": True}
        )

    @classmethod
    def _get_next_action(cls, intent: UserIntent) -> str:
        actions = {
            UserIntent.QISHU: "继续提问，深入了解需求",
            UserIntent.TANYIN: "进入探隐，收集需求信息",
            UserIntent.CAIHENG: "从产品价值角度重新审视",
            UserIntent.ZHENWEI: "讨论技术实现方案",
            UserIntent.CESHU: "分解为可执行的任务",
            UserIntent.NINGMO: "生成完整的项目方案",
            UserIntent.CHAT: "继续对话",
        }
        return actions.get(intent, "继续对话")

    @classmethod
    def get_recommended_workflow(cls, clarity: ClarityLevel, intent: UserIntent) -> str:
        """根据清晰程度和意图推荐工作流"""
        if clarity == ClarityLevel.FUZZY:
            return "tanyin"
        elif clarity == ClarityLevel.PARTIAL:
            return "qishu"
        elif clarity == ClarityLevel.TECHNICAL:
            return "zhenwei"
        else:
            intent_workflow_map = {
                UserIntent.QISHU: "qishu",
                UserIntent.TANYIN: "tanyin",
                UserIntent.CAIHENG: "caiheng",
                UserIntent.ZHENWEI: "zhenwei",
                UserIntent.CESHU: "ceshu",
                UserIntent.NINGMO: "ningmo",
                UserIntent.CHAT: "chat",
            }
            return intent_workflow_map.get(intent, "chat")

    @classmethod
    def get_workflow_options(cls, clarity: ClarityLevel) -> List[Dict[str, str]]:
        """获取给定清晰程度下的可选工作流"""
        options = [
            {"id": "qishu", "label": "启枢", "description": "追问澄清，深入思考"},
            {"id": "tanyin", "label": "探隐", "description": "探求隐情，系统化收集需求"},
            {"id": "caiheng", "label": "裁衡", "description": "审视产品价值"},
            {"id": "zhenwei", "label": "甄微", "description": "评审技术实现"},
            {"id": "ningmo", "label": "凝墨", "description": "产出具执行方案"},
        ]

        if clarity == ClarityLevel.FUZZY:
            return options[:2]
        elif clarity == ClarityLevel.PARTIAL:
            return options[:3]
        else:
            return options
