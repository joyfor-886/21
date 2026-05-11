from typing import Dict, Any, List, Optional
from core.skill_registry import Skill, SkillResult
from core.llm_factory import LLMFactory

SPEC_GENERATOR_SYSTEM_PROMPT = """你是 Ssuma 的方案整合与输出专家。
你的任务是将前面多轮对话（头脑风暴、CEO审查、架构审查、执行计划拆解）产生的所有结论，整合为一份严谨的、可以直接喂给 AI IDE 的结构化 Markdown 文档。

【输出结构严格要求】

# 📄 [项目名称] - Ssuma 执行方案

> 生成时间：[当前系统时间]
> 这是一个经过多轮深度评审的、达到投产级别的项目方案。

## 🎯 第一部分：产品共识 (Product Definition)
- **核心问题**: (用户最大的痛点，必须具体)
- **解决方案的最小切入点 (Wedge)**: (为什么用户现在就要用它)
- **非目标 (Out of scope)**: (明确我们**不**做什么，避免范围蔓延)
- **成功指标 (Metrics)**: (什么数据证明我们做对了)

## 🏗️ 第二部分：系统架构与设计 (Architecture & Design)
- **全局架构描述**: (一两段话描述技术选型和整体流转)
- **核心数据模型**: (数据库表或对象结构的 Markdown 表格)
- **关键 API/接口规范**:
- **状态与边缘情况覆盖**: (列举最重要的异常及其恢复策略)

## 🛡️ 第三部分：风险与缓解 (Risks & Mitigations)
- 列出 2-3 个最大的技术或产品风险，以及计划中是如何规避的。

## 🚀 第四部分：TDD 执行步骤 (Execution Plan)
(严格照搬计划专家给出的分步列表，确保每个 Task 都是 2-5 分钟的可执行单元，带有文件路径和明确的验证步骤)

【语言风格】
专业、严谨、排版精美。大量使用粗体、列表、引用块和 Markdown 表格来增强可读性。只输出文档本身，不要有任何前言或后语。"""

# 多遍生成的各遍专用 prompt
PRODUCT_SPEC_PROMPT = """你是 Ssuma 的方案整合专家（第1遍：产品定义）。

请仅基于以下讨论内容，生成方案的**产品共识**部分。

【前序阶段成果】
{artifact_context}

【对话历史】
{conversation}

【输出要求】
只输出以下章节，不要输出其他内容：

# 📄 [项目名称] - Ssuma 执行方案

## 🎯 第一部分：产品共识 (Product Definition)
- **核心问题**: ...
- **解决方案的最小切入点 (Wedge)**: ...
- **非目标 (Out of scope)**: ...
- **成功指标 (Metrics)**: ...

专业、严谨、排版精美。"""

TECH_SPEC_PROMPT = """你是 Ssuma 的方案整合专家（第2遍：技术方案）。

基于已经生成的产品定义，请生成方案的**系统架构与设计**以及**风险与缓解**部分。

【前序阶段成果】
{artifact_context}

【产品定义（第1遍产出）】
{product_spec}

【对话历史】
{conversation}

【输出要求】
只输出以下章节，不要重复产品定义部分：

## 🏗️ 第二部分：系统架构与设计 (Architecture & Design)
- **全局架构描述**: ...
- **核心数据模型**: ...
- **关键 API/接口规范**: ...
- **状态与边缘情况覆盖**: ...

## 🛡️ 第三部分：风险与缓解 (Risks & Mitigations)
- ...

专业、严谨，包含 ASCII 架构图和 Markdown 表格。"""

EXEC_SPEC_PROMPT = """你是 Ssuma 的方案整合专家（第3遍：执行计划）。

基于已经生成的技术方案，请生成方案的**TDD执行步骤**部分。

【前序阶段成果】
{artifact_context}

【技术方案（第2遍产出）】
{tech_spec}

【对话历史】
{conversation}

【输出要求】
只输出以下章节，不要重复前面的部分：

## 🚀 第四部分：TDD 执行步骤 (Execution Plan)
- 每个 Task 必须是 2-5 分钟的可执行单元
- 带有文件路径和明确的验证步骤
- 遵循 TDD 红绿循环：先写失败测试 → 实现代码 → 测试通过

严格、细致、无歧义。这是给机器执行的计划。"""

MERGE_SPEC_PROMPT = """你是 Ssuma 的方案整合专家（最终合并）。

请将以下三部分内容合并为一份完整的、格式统一的 Markdown 文档。
只做格式调整和重复内容去重，不要修改实质内容。

【第一部分：产品共识】
{product_spec}

【第二部分：系统架构与风险】
{tech_spec}

【第三部分：执行步骤】
{exec_spec}

【输出要求】
输出完整的 Markdown 文档，格式统一、排版精美。"""


class SpecGeneratorSkill(Skill):
    """凝墨 - 生成完整的AI可执行项目方案

    改进点：
    1. 多遍生成（产品→技术→执行→合并），而非一次性输出
       参考 NeoLabHQ/reflexion 的自精炼循环模式
    2. 每遍接收前序阶段的 Artifact 上下文
    3. 后续遍可引用前遍的产出，确保一致性
    """
    name = "ningmo"
    description = "凝墨 - 生成完整的AI可执行项目方案"
    trigger = "生成方案"
    required_outputs = ["product_definition", "architecture_design", "execution_plan"]

    async def run(self, conversation: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        context = context or {}
        artifact_context = context.get("artifact_context", "")

        use_multi_pass = bool(artifact_context) or len(conversation) > 500

        try:
            if use_multi_pass:
                return await self._multi_pass_generate(conversation, artifact_context, context)
            else:
                return await self._single_pass_generate(conversation, context)
        except Exception as e:
            import logging
            logging.getLogger('Ssuma.NingmoSkill').error(f"Ningmo skill failed: {e}")
            return self._fallback_response(conversation)

    def _fallback_response(self, conversation: str) -> SkillResult:
        return SkillResult(
            response=(
                "⚠️ 方案生成服务暂时不可用。以下是基于当前讨论的框架性方案：\n\n"
                "# 📄 项目执行方案（草稿）\n\n"
                "## 🎯 产品共识\n"
                "请基于之前的讨论，明确核心问题、最小切入点和非目标。\n\n"
                "## 🏗️ 系统架构\n"
                "请根据讨论内容，确定技术选型、数据模型和接口规范。\n\n"
                "## 🛡️ 风险与缓解\n"
                "请识别2-3个最大风险并制定缓解策略。\n\n"
                "## 🚀 TDD执行步骤\n"
                "请将方案拆解为2-5分钟可执行的任务单元。\n\n"
                "💡 AI服务恢复后，可以重新生成完整方案。"
            ),
            stage="ningmo",
        )

    async def _multi_pass_generate(
        self,
        conversation: str,
        artifact_context: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """多遍生成：产品定义 → 技术方案 → 执行步骤 → 合并

        参考 NeoLabHQ/reflexion：每遍生成后验证，
        后续遍基于前遍产出进行精炼。
        """
        provider = LLMFactory.get_provider()

        # 第1遍：产品定义
        try:
            product_prompt = PRODUCT_SPEC_PROMPT.format(
                artifact_context=artifact_context or "无",
                conversation=conversation[:4000]
            )
            product_spec = await provider.chat(
                [
                    {"role": "system", "content": "你是方案整合专家。只输出指定章节。"},
                    {"role": "user", "content": product_prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
        except Exception as e:
            product_spec = "（产品定义生成失败，请基于对话自行补充）"

        # 第2遍：技术方案（基于产品定义）
        try:
            tech_prompt = TECH_SPEC_PROMPT.format(
                artifact_context=artifact_context or "无",
                product_spec=product_spec[:2000],
                conversation=conversation[:3000]
            )
            tech_spec = await provider.chat(
                [
                    {"role": "system", "content": "你是方案整合专家。只输出指定章节。"},
                    {"role": "user", "content": tech_prompt}
                ],
                max_tokens=1500,
                temperature=0.3
            )
        except Exception as e:
            tech_spec = "（技术方案生成失败，请基于对话自行补充）"

        # 第3遍：执行步骤（基于技术方案）
        try:
            exec_prompt = EXEC_SPEC_PROMPT.format(
                artifact_context=artifact_context or "无",
                tech_spec=tech_spec[:2000],
                conversation=conversation[:3000]
            )
            exec_spec = await provider.chat(
                [
                    {"role": "system", "content": "你是方案整合专家。只输出指定章节。"},
                    {"role": "user", "content": exec_prompt}
                ],
                max_tokens=1500,
                temperature=0.3
            )
        except Exception as e:
            exec_spec = "（执行步骤生成失败，请基于对话自行补充）"

        # 第4遍：合并为完整文档
        try:
            merge_prompt = MERGE_SPEC_PROMPT.format(
                product_spec=product_spec,
                tech_spec=tech_spec,
                exec_spec=exec_spec
            )
            final_spec = await provider.chat(
                [
                    {"role": "system", "content": "你是方案整合专家。合并并格式化文档。"},
                    {"role": "user", "content": merge_prompt}
                ],
                max_tokens=2000,
                temperature=0.2
            )
        except Exception:
            # 合并失败时手动拼接
            final_spec = f"{product_spec}\n\n---\n\n{tech_spec}\n\n---\n\n{exec_spec}"

        return SkillResult(
            response=final_spec,
            stage="ningmo",
            artifacts={
                "product_spec": product_spec,
                "tech_spec": tech_spec,
                "exec_spec": exec_spec,
            },
        )

    async def _single_pass_generate(
        self,
        conversation: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """单遍生成（信息不足时的降级模式）"""
        provider = LLMFactory.get_provider()

        messages = [
            {"role": "system", "content": SPEC_GENERATOR_SYSTEM_PROMPT},
            {"role": "user", "content": f"请将以下所有的讨论内容，整合提炼为一份最终的执行方案 Spec：\n\n{conversation}"}
        ]

        response = await provider.chat(messages, max_tokens=2000, temperature=0.3)

        return SkillResult(
            response=response,
            stage="ningmo",
        )
