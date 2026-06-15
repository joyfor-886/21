"""凝墨 (Ningmo) - AI IDE 可执行方案生成器

核心改进：
1. 多遍生成 + 自我批判 + 精炼，而非一次性输出
2. 每遍更高的 token 预算，确保输出完整性
3. 技术方案中自动推断推荐技术栈
4. 最终输出包含 AI IDE 可直接使用的结构化内容
5. 自评分机制 —— 不达标的方案自动迭代
"""

from typing import Dict, Any, List, Optional
import json
import logging
from datetime import datetime
from core.skill_registry import Skill, SkillResult
from core.llm_factory import LLMFactory

logger = logging.getLogger('Ssuma.NingmoSkill')

# ============================================================
#  多遍生成 Prompt —— 每遍聚焦一个维度，深度思考
# ============================================================

PRODUCT_SPEC_PROMPT = """你是 Ssuma 的方案整合专家（第 1 遍：产品共识）。

你的任务：基于前序阶段的讨论成果，提炼出无歧义、可直接指导开发的产品定义。

【输入】
【前序阶段成果】
{artifact_context}

【对话历史】
{conversation}

【输出要求】
请严格按以下结构输出。每个字段必须具体、无歧义。不可留空，不可写"待定"。

## 1. 产品共识

### 一句话描述
（用户 + 场景 + 核心价值，20 字以内）

### 目标用户画像
- **主要用户**: （谁在用？什么场景下用？有什么技术背景？）
- **次要用户**: （如果有）

### 核心痛点
（用户当前不用这个产品时，是怎么解决问题的？有多痛苦？）

### MVP 功能（P0 —— 必须有）
1. （功能名）：（一句话描述 + 为什么是 P0）
2. ...

### P1 功能（应该有，但可以第二版做）
1. ...

### 明确的非目标（现在绝对不做的事）
1. ...
2. ...

### 成功指标（可量化）
- **激活指标**: （用户做了什么就算"用起来了"？）
- **留存指标**: （什么行为证明用户会持续用？）
- **满意度指标**: （如何衡量用户满意度？）

请专业、精准。每个条目都必须是有信息量的，拒绝空话。"""

TECH_SPEC_PROMPT = """你是 Ssuma 的方案整合专家（第 2 遍：技术架构）。

你的任务：基于产品定义，设计可落地的技术方案。你产出的架构将直接指导代码编写。

【输入】
【前序阶段成果】
{artifact_context}

【产品定义（第 1 遍产出）】
{product_spec}

【对话历史】
{conversation}

【输出要求】
请严格按以下结构输出：

## 2. 技术架构

### 技术栈推荐
| 层级 | 首选方案 | 版本要求 | 选择理由 |
|------|---------|---------|---------|
| 前端框架 | | | |
| UI 库 | | | |
| 后端框架 | | | |
| 数据库 | | | |
| ORM/数据层 | | | |
| 认证 | | | |
| 部署 | | | |

### 备选方案
（什么情况下应该考虑备选方案？备选方案是什么？）

### 项目目录结构
```
project-root/
├── src/
│   ├── app/          # 页面路由（Next.js）或 views/
│   ├── components/   # 可复用 UI 组件
│   │   ├── ui/       # 基础 UI 组件（Button, Input 等）
│   │   └── layout/   # 布局组件
│   ├── lib/          # 工具函数、API 客户端
│   ├── hooks/        # 自定义 React Hooks
│   └── types/        # TypeScript 类型定义
├── tests/
│   ├── unit/
│   └── integration/
├── docs/
├── .env.example
└── README.md
```
（根据实际技术栈调整此结构）

### 核心数据模型
（列出 3-6 个核心表/模型，用表格：表名 | 关键字段 | 关系）

### API 设计
（列出 3-5 个最关键的 API 端点：方法 | 路径 | 请求体 | 响应体 | 认证要求）

### 数据流
（用文字描述关键业务流程的数据流动，如：用户注册 → 验证 → 写入数据库 → 发送欢迎邮件）

### 状态管理策略
（全局状态用什么？服务端状态用什么？本地状态用什么？）

请确保所有技术选型有明确理由。版本号精确到主版本。"""

EXEC_SPEC_PROMPT = """你是 Ssuma 的方案整合专家（第 3 遍：执行计划）。

你的任务：将技术方案拆解为 AI IDE（Cursor/Trae/Copilot）可以逐条执行的 TDD 任务序列。

【输入】
【前序阶段成果】
{artifact_context}

【技术方案（第 2 遍产出）】
{tech_spec}

【对话历史】
{conversation}

【核心原则】
1. 每个 Task 必须能在 2-5 分钟内完成
2. TDD：先写失败测试 → 实现 → 通过 → commit
3. 每个 Task 带完整文件路径和验收标准
4. 零 TODO，零占位符

【输出格式】
## 4. 执行计划

### Phase 1: 项目骨架（Tasks 1-3）
（搭建项目结构、配置文件、依赖安装，确保项目能跑起来）

### Phase 2: 核心数据层（Tasks 4-7）
（数据模型、数据库连接、基础 CRUD）

### Phase 3: 业务逻辑（Tasks 8-15）
（核心功能实现，按依赖关系排序）

### Phase 4: UI 实现（Tasks 16-N）
（页面和组件，从核心页面开始）

### Phase 5: 集成与部署（Tasks N+1-N+3）
（端到端测试、部署配置、文档）

对每个 Task 使用以下精确格式：
```
### Task {N}: {任务名称}
**复杂度**: 🟢简单 / 🟡中等 / 🔴复杂
**预估**: {X} 分钟
**依赖**: 无 / Task {N-1}

**文件**:
- [NEW] `path/to/file.ext`
- [MODIFY] `path/to/existing.ext`

**步骤**:
- [ ] 1. 编写测试 `tests/path/to/test.ext`：验证 {具体行为}
- [ ] 2. 运行 `{test command}`，确认失败（红线）
- [ ] 3. 实现 `path/to/impl.ext` 的最少代码
- [ ] 4. 运行测试，确认通过（绿线）
- [ ] 5. `git add -A && git commit -m "{type}: {描述}"`

**验收**: {可验证的完成标准}
```

确保总 Task 数量：简单项目 5-10 个，中等 10-20 个，复杂 20-35 个。"""

SELF_CRITIQUE_PROMPT = """你是 Ssuma 的方案审查专家（第 4 遍：自我批判）。

你的任务：以挑剔的眼光审查刚生成的方案，找出问题并给出修改建议。

【待审查方案】
{full_spec}

【审查维度】
1. **完整性**：原始需求是否 100% 覆盖？有没有遗漏的功能或场景？
2. **可行性**：以 AI IDE 的能力，这真的能执行吗？有没有需要人判断的模糊地方？
3. **精确性**：文件路径是否完整？命令是否可以直接复制运行？版本号是否明确？
4. **一致性**：产品定义 → 技术架构 → 执行计划之间有没有矛盾？
5. **简洁性**：有没有不必要的复杂度？MVP 阶段可以砍掉什么？

【输出格式】
```
## 方案审查报告

### 评分
| 维度 | 评分(1-10) | 说明 |
|------|-----------|------|
| 完整性 | X/10 | ... |
| 可行性 | X/10 | ... |
| 精确性 | X/10 | ... |
| 一致性 | X/10 | ... |
| 简洁性 | X/10 | ... |
| **总评** | **X/10** | ... |

### 发现的问题
1. **{问题类型}**: {具体问题描述} → 建议：{修改建议}
2. ...

### 修改建议摘要
（3-5 条最重要的修改建议，按优先级排列）
```

如果总评 >= 8/10，请在报告末尾写"✅ 方案达标，可以直接执行。"
如果总评 < 8/10，请写"⚠️ 方案需要修改，主要问题是：{最严重的 1-2 个问题}"。"""

FINAL_MERGE_PROMPT = """你是 Ssuma 的方案整合专家（最终合并）。

请将以下各部分合并为一份完整的 Markdown 文档。

【产品共识】
{product_spec}

【技术架构】
{tech_spec}

【执行计划】
{exec_spec}

【自我批判】
{critique}

【输出要求】
1. 合并为统一格式的完整文档
2. 将自我批判中的修改建议融入对应章节（这是关键 —— 不要只是罗列，要真正修改）
3. 在最前面添加项目元信息（生成时间、复杂度评估、预估开发时间）
4. 在最后添加「AI IDE 快速启动」部分：
   - 环境要求（Node/Python 等版本）
   - 安装和启动命令
   - 关键文档索引
   - 环境变量清单
5. 确保全文格式统一、排版精美、无重复内容

输出完整文档，不要省略。"""


class SpecGeneratorSkill(Skill):
    """凝墨 - 生成完整的 AI IDE 可执行项目方案

    改进点：
    1. 多遍生成（产品→技术→执行→自我批判→合并），每遍聚焦一个维度
    2. 大幅提高 token 预算（4096-8192），确保输出完整
    3. 自评分机制：不达标的方案会自动标记
    4. 批判性思维：方案生成后进行自我审查
    5. 最终输出可直接作为 AI IDE 上下文使用
    """

    name = "ningmo"
    description = "凝墨 - 生成完整的 AI IDE 可执行项目方案"
    trigger = "生成方案"
    required_outputs = ["product_definition", "architecture_design", "execution_plan", "quality_score"]

    async def run(self, conversation: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        context = context or {}
        artifact_context = context.get("artifact_context", "")

        use_multi_pass = bool(artifact_context) or len(conversation) > 300

        try:
            if use_multi_pass:
                return await self._multi_pass_generate(conversation, artifact_context, context)
            else:
                return await self._single_pass_generate(conversation, context)
        except Exception as e:
            logger.error(f"Ningmo skill failed: {e}")
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
                "请识别 2-3 个最大风险并制定缓解策略。\n\n"
                "## 🚀 TDD 执行步骤\n"
                "请将方案拆解为 2-5 分钟可执行的任务单元。\n\n"
                "💡 AI 服务恢复后，可以重新生成完整方案。"
            ),
            stage="ningmo",
        )

    async def _multi_pass_generate(
        self,
        conversation: str,
        artifact_context: str,
        context: Dict[str, Any]
    ) -> SkillResult:
        """多遍生成：产品定义 → 技术方案 → 执行步骤 → 自我批判 → 合并

        参考 reflexion 模式：每遍基于前一遍的产出进行精炼，
        最后通过自我批判发现并修复问题。
        """
        provider = LLMFactory.get_provider()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        # ===== 第 1 遍：产品定义 =====
        product_spec = await self._generate_pass(
            provider,
            PRODUCT_SPEC_PROMPT.format(
                artifact_context=artifact_context or "（无前序阶段成果，请基于对话历史推断）",
                conversation=conversation[:6000]
            ),
            max_tokens=4096,
            label="产品定义"
        )

        # ===== 第 2 遍：技术架构 =====
        tech_spec = await self._generate_pass(
            provider,
            TECH_SPEC_PROMPT.format(
                artifact_context=artifact_context or "（无前序阶段成果，请基于对话历史和产品定义推断）",
                product_spec=product_spec[:4000],
                conversation=conversation[:4000]
            ),
            max_tokens=4096,
            label="技术架构"
        )

        # ===== 第 3 遍：执行计划 =====
        exec_spec = await self._generate_pass(
            provider,
            EXEC_SPEC_PROMPT.format(
                artifact_context=artifact_context or "（无前序阶段成果）",
                tech_spec=tech_spec[:4000],
                conversation=conversation[:3000]
            ),
            max_tokens=6144,
            label="执行计划"
        )

        # ===== 第 4 遍：自我批判 =====
        full_draft = f"{product_spec}\n\n---\n\n{tech_spec}\n\n---\n\n{exec_spec}"
        critique = await self._generate_pass(
            provider,
            SELF_CRITIQUE_PROMPT.format(full_spec=full_draft[:10000]),
            max_tokens=3072,
            label="自我批判"
        )

        # ===== 解析自评分 =====
        quality_score = self._extract_score(critique)

        # ===== 第 5 遍：最终合并（融入修改建议）=====
        final_spec = await self._generate_pass(
            provider,
            FINAL_MERGE_PROMPT.format(
                product_spec=product_spec,
                tech_spec=tech_spec,
                exec_spec=exec_spec,
                critique=critique,
            ),
            max_tokens=8192,
            label="最终合并"
        )

        # 如果合并失败，手动拼接
        if final_spec.startswith("（生成失败"):
            final_spec = (
                f"# 📄 Ssuma 执行方案\n\n"
                f"> 生成时间：{timestamp}\n\n"
                f"{product_spec}\n\n---\n\n{tech_spec}\n\n---\n\n{exec_spec}\n\n---\n\n{critique}"
            )

        return SkillResult(
            response=final_spec,
            stage="ningmo",
            artifacts={
                "product_spec": product_spec,
                "tech_spec": tech_spec,
                "exec_spec": exec_spec,
                "critique": critique,
                "quality_score": quality_score,
                "generated_at": timestamp,
            },
        )

    async def _generate_pass(
        self,
        provider,
        prompt: str,
        max_tokens: int,
        label: str
    ) -> str:
        """执行单遍生成，带错误处理和超时保护"""
        try:
            import asyncio
            response = await asyncio.wait_for(
                provider.chat(
                    [
                        {"role": "system", "content": f"你是 Ssuma 方案整合专家。你正在进行「{label}」阶段的生成。请输出完整、专业、结构化的内容。技术术语允许使用英文。不要输出思考过程，直接输出结果。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=0.3
                ),
                timeout=180.0
            )
            return response.strip()
        except asyncio.TimeoutError:
            logger.warning(f"Ningmo {label} 阶段超时")
            return f"（{label}阶段生成超时，请增加 token 预算或缩短对话历史后重试）"
        except Exception as e:
            logger.error(f"Ningmo {label} 阶段失败: {e}")
            return f"（{label}阶段生成失败: {str(e)}）"

    def _extract_score(self, critique: str) -> Optional[float]:
        """从自我批判文本中提取总评分"""
        import re
        # 匹配 "**总评**: **X/10**" 或 "总评: X/10" 等格式
        patterns = [
            r'\*\*总评\*\*[：:]\s*\*?\*?(\d+(?:\.\d+)?)\s*/\s*10',
            r'总评[：:]\s*(\d+(?:\.\d+)?)\s*/\s*10',
            r'总评[：:]\s*\*?\*?(\d+(?:\.\d+)?)',
        ]
        for pattern in patterns:
            match = re.search(pattern, critique)
            if match:
                score = float(match.group(1))
                return min(score, 10.0) / 10.0  # normalize to 0-1
        return None

    async def _single_pass_generate(
        self,
        conversation: str,
        context: Dict[str, Any]
    ) -> SkillResult:
        """单遍生成（对话历史较短时的简化模式）"""
        provider = LLMFactory.get_provider()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        system_prompt = """你是 Ssuma 的方案整合专家。请将以下所有讨论内容整合为一份结构化的项目执行方案。

【输出结构】
```
# {项目名称} - AI IDE 执行方案
> 生成时间: {当前时间}

## 1. 产品共识
- 一句话描述
- 目标用户
- MVP 功能
- 非目标
- 成功指标

## 2. 技术架构
- 推荐技术栈（含版本号）
- 项目目录结构
- 核心数据模型
- API 设计
- 状态管理策略

## 3. 风险与缓解

## 4. 执行计划
（每个 Task 2-5 分钟可完成，TDD 格式，带文件路径和验收标准）
```

【要求】
- 技术术语和代码可用英文，描述用中文
- 所有命令可直接复制运行
- 文件路径完整，验收标准具体可量化
- 不要输出思考过程"""

        try:
            import asyncio
            response = await asyncio.wait_for(
                provider.chat(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"请基于以下讨论内容生成完整的项目执行方案：\n\n{conversation[:8000]}"}
                    ],
                    max_tokens=4096,
                    temperature=0.3
                ),
                timeout=180.0
            )
        except Exception as e:
            logger.error(f"Ningmo single pass failed: {e}")
            response = self._fallback_response(conversation).response

        return SkillResult(
            response=response,
            stage="ningmo",
        )
