"""自动流水线服务 —— 一句话生成完整项目方案 + IDE 文件

流程：
  fast:     qishu → caiheng → ningmo → export
  standard: qishu → caiheng → ceshu → ningmo → powang → export
  deep:     qishu → caiheng → zhenwei → ceshu → ningmo → powang → jianyan → export

全程自动，无需用户介入。
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from dataclasses import dataclass, field

from domain.enums import WORKFLOW_SYSTEM_PROMPTS

logger = logging.getLogger('Ssuma.AutoPilot')

# 自动流水线阶段序列 —— 按通道分级
# fast: 快速验证（简单项目）
FAST_AUTOPILOT_PHASES = ["qishu", "caiheng", "ningmo"]

# standard: 标准流程（中等项目）
STANDARD_AUTOPILOT_PHASES = ["qishu", "caiheng", "ceshu", "ningmo", "powang"]

# deep: 完整七艺（复杂/平台级项目）
DEEP_AUTOPILOT_PHASES = ["qishu", "caiheng", "zhenwei", "ceshu", "ningmo", "powang", "jianyan"]

# 兼容旧代码
AUTOPILOT_PHASES = DEEP_AUTOPILOT_PHASES

# 各阶段的自动推进 prompt —— 以上一阶段的产出作为输入
PHASE_PROMPTS = {
    "qishu": """你是一位资深产品经理。用户有一个模糊的想法，请帮他厘清需求。

用户的想法：{idea}

请按以下步骤思考并输出：
1. 一句话总结用户想做什么
2. 目标用户画像
3. 核心痛点分析
4. MVP 功能清单（3-5 个 P0 功能）
5. 明确不做什么（非目标）
6. 成功指标建议

输出格式：结构化的 Markdown，清晰分段。""",

    "caiheng": """你是 CEO 视角的产品审查专家。请审查以下产品方案。

【产品方案】
{qishu_output}

【用户原始想法】
{idea}

请按 5 个维度审查：
1. **价值主张**：用户真的有这个痛点吗？方案是维生素还是止痛药？
2. **范围聚焦**：MVP 范围是否合适？有没有可以砍掉或遗漏的功能？
3. **竞争壁垒**：为什么是你做？护城河在哪？
4. **风险识别**：最可能失败的地方是什么？
5. **成功指标**：指标是否可量化？是否容易获取？

每个维度给出：评估 → 风险 → 改进建议。输出结构化的审查报告。""",

    "zhenwei": """你是首席架构师的视角。请基于产品方案设计技术架构。

【产品方案 + CEO 审查结论】
{context}

【用户原始想法】
{idea}

请输出：
1. **推荐技术栈**（前端/后端/数据库/部署，含版本号和选择理由）
2. **备选方案**（什么情况下考虑切换）
3. **项目目录结构**（树形图）
4. **核心数据模型**（3-6 个表，含字段和关系）
5. **关键 API 设计**（3-5 个端点，含请求/响应格式）
6. **安全与性能考量**
7. **风险评估**（每个风险标注 🔴高/🟡中/🟢低）""",

    "ceshu": """你是执行计划专家。请将以下技术方案拆解为 AI IDE 可逐条执行的 TDD 任务序列。

【技术方案 + 架构设计】
{context}

【原始需求】
{idea}

核心原则：
- 每个 Task 2-5 分钟可完成
- TDD 铁律：先写失败测试 → 实现最小代码 → 通过 → commit
- 每个 Task 带完整文件路径和验收标准
- 零 TODO，零占位符

请按 Phase 分组输出：
- Phase 1: 项目骨架（1-3 tasks）
- Phase 2: 核心数据层（3-5 tasks）
- Phase 3: 业务逻辑（5-10 tasks）
- Phase 4: UI 实现（N tasks）
- Phase 5: 集成与部署（1-3 tasks）

每个 Task 格式：
```
### Task {N}: {名称}
**复杂度**: 🟢/🟡/🔴
**预估**: X 分钟
**文件**: [NEW/MODIFY] `path/to/file`
**步骤**:
- [ ] 1. 编写测试: `tests/path`，验证 {行为}
- [ ] 2. 确认测试失败
- [ ] 3. 实现最少代码
- [ ] 4. 确认测试通过
- [ ] 5. git commit
**验收**: {标准}
```""",

    "ningmo": """你是方案整合专家。请将以下所有阶段的产出整合为一份完整的 AI IDE 执行方案。

【全部前序产出】
{context}

【用户原始想法】
{idea}

请输出完整的 Markdown 方案文档，包含：
1. 产品共识（一句话描述、用户画像、MVP 功能、非目标、成功指标）
2. 技术架构（技术栈推荐、项目结构、数据模型、API 设计）
3. 风险与缓解
4. 执行计划（TDD 任务序列）
5. AI IDE 快速启动指南（环境要求、安装命令、测试命令、环境变量清单）

要求：技术术语可用英文，命令可直接复制运行。""",

    "jianyan": """你是分阶段规划专家。请将以下完整方案拆分为多个独立可交付的演进阶段。

【完整方案 + 覆盖验证结论】
{context}

【用户原始想法】
{idea}

请按以下格式输出：

## 演进路线图

### Phase 1: 核心验证 ({预估时间})
**目标**: 证明产品价值的最小功能集
**交付物**: 具体文件和功能列表
**验收标准**: 可量化的完成条件
**依赖**: 需要的前置条件

### Phase 2: 基本可用 ({预估时间})
...

### Phase 3: 体验完善 ({预估时间})
...

每个 Phase 必须：
- 独立可交付、可验证、可部署
- 交付物是具体文件路径
- 验收标准可量化
- 标注风险点""",
}


@dataclass
class AutoPilotState:
    """自动流水线运行状态"""
    project_id: str
    idea: str
    current_phase_index: int = 0
    phase_outputs: Dict[str, str] = field(default_factory=dict)
    status: str = "pending"  # pending | running | completed | failed
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class AutoPilotService:
    """自动流水线：一句话 → 完整方案 + IDE 文件"""

    _active_jobs: Dict[str, AutoPilotState] = {}

    @classmethod
    async def run(
        cls,
        project_id: str,
        idea: str,
        channel: str = "standard",
    ) -> Dict[str, Any]:
        """执行完整的自动流水线

        Args:
            project_id: 项目 ID
            idea: 用户的一句话想法
            channel: 通道 (fast/standard/deep)

        Returns:
            {
                "project_id": str,
                "final_spec": str,
                "ide_files": {path: content},
                "phase_summary": [{phase, duration}],
                "quality_score": float,
            }
        """
        from core.llm_factory import LLMFactory

        state = AutoPilotState(
            project_id=project_id,
            idea=idea,
            started_at=datetime.now().isoformat(),
        )
        cls._active_jobs[project_id] = state

        try:
            provider = LLMFactory.get_provider()

            # 确定阶段序列
            if channel == "fast":
                phases = FAST_AUTOPILOT_PHASES
            elif channel == "deep":
                phases = DEEP_AUTOPILOT_PHASES
            else:
                phases = STANDARD_AUTOPILOT_PHASES

            state.status = "running"
            phase_summary = []

            for i, phase_name in enumerate(phases):
                state.current_phase_index = i
                phase_start = datetime.now()

                # 构建阶段 context（累积前面的产出）
                context = cls._build_context(phase_name, state)
                prompt = PHASE_PROMPTS.get(phase_name, PHASE_PROMPTS["qishu"]).format(
                    idea=idea,
                    qishu_output=state.phase_outputs.get("qishu", ""),
                    context=context,
                )

                logger.info(f"AutoPilot [{project_id}] phase {i+1}/{len(phases)}: {phase_name}")

                try:
                    system_prompt = WORKFLOW_SYSTEM_PROMPTS.get(
                        phase_name,
                        f"你是 Ssuma 的{phase_name}专家。请输出完整的分析报告。"
                    )
                    response = await asyncio.wait_for(
                        provider.chat(
                            [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": prompt},
                            ],
                            max_tokens=cls._max_tokens_for_phase(phase_name),
                            temperature=0.3 if phase_name != "qishu" else 0.7,
                        ),
                        timeout=180.0,
                    )
                    state.phase_outputs[phase_name] = response.strip()

                except asyncio.TimeoutError:
                    logger.warning(f"AutoPilot phase {phase_name} timeout, using fallback")
                    state.phase_outputs[phase_name] = f"[{phase_name} 阶段超时，请在后续对话中补充]"
                except Exception as e:
                    logger.error(f"AutoPilot phase {phase_name} failed: {e}")
                    state.phase_outputs[phase_name] = f"[{phase_name} 阶段失败: {str(e)}]"

                phase_duration = (datetime.now() - phase_start).total_seconds()
                phase_summary.append({
                    "phase": phase_name,
                    "duration_seconds": round(phase_duration, 1),
                    "output_length": len(state.phase_outputs[phase_name]),
                })

                # 产出到日志
                logger.info(
                    f"AutoPilot [{project_id}] {phase_name} done "
                    f"({phase_duration:.1f}s, {len(state.phase_outputs[phase_name])} chars)"
                )

            # 阶段全部完成
            final_spec = state.phase_outputs.get("ningmo", "")
            if not final_spec:
                final_spec = state.phase_outputs.get("ceshu", "")

            # 导出 IDE 文件
            ide_files = {}
            quality_score = None

            try:
                from services.ide_exporter import IDEExporter

                exported = IDEExporter.export({
                    "name": project_id.replace("proj-", "project-"),
                    "description": idea,
                    "product_spec": state.phase_outputs.get("qishu", ""),
                    "tech_spec": state.phase_outputs.get("zhenwei", "")
                                or state.phase_outputs.get("caiheng", ""),
                    "exec_spec": state.phase_outputs.get("ceshu", ""),
                    "features": [],
                    "decisions": [
                        state.phase_outputs.get("caiheng", ""),
                        state.phase_outputs.get("zhenwei", ""),
                    ],
                })
                ide_files = exported.files
                logger.info(f"AutoPilot [{project_id}] exported {len(ide_files)} IDE files")
            except Exception as e:
                logger.error(f"AutoPilot IDE export failed: {e}")

            # 提取质量分
            powang_output = state.phase_outputs.get("powang", "")
            if powang_output:
                import re
                match = re.search(r'coverage_percent["\']?\s*[:=]\s*(\d+)', powang_output)
                if match:
                    quality_score = int(match.group(1)) / 100.0

            state.status = "completed"
            state.completed_at = datetime.now().isoformat()

            total_duration = sum(p["duration_seconds"] for p in phase_summary)

            return {
                "project_id": project_id,
                "final_spec": final_spec,
                "ide_files": ide_files,
                "file_count": len(ide_files),
                "phase_summary": phase_summary,
                "total_duration_seconds": round(total_duration, 1),
                "quality_score": quality_score,
                "all_outputs": {
                    phase: output[:500]
                    for phase, output in state.phase_outputs.items()
                },
            }

        except Exception as e:
            state.status = "failed"
            state.error = str(e)
            logger.error(f"AutoPilot [{project_id}] failed: {e}")
            raise
        finally:
            # 保留结果 30 分钟供查询
            pass

    @classmethod
    async def run_stream(
        cls,
        project_id: str,
        idea: str,
        channel: str = "standard",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式执行自动流水线，逐步返回每个阶段的进度"""
        from core.llm_factory import LLMFactory

        state = AutoPilotState(
            project_id=project_id,
            idea=idea,
            started_at=datetime.now().isoformat(),
            status="running",
        )
        cls._active_jobs[project_id] = state

        yield {"type": "start", "project_id": project_id, "total_phases": len(AUTOPILOT_PHASES)}

        try:
            provider = LLMFactory.get_provider()
            if channel == "fast":
                phases = FAST_AUTOPILOT_PHASES
            elif channel == "deep":
                phases = DEEP_AUTOPILOT_PHASES
            else:
                phases = STANDARD_AUTOPILOT_PHASES

            for i, phase_name in enumerate(phases):
                state.current_phase_index = i

                yield {
                    "type": "phase_start",
                    "phase": phase_name,
                    "index": i + 1,
                    "total": len(phases),
                    "label": cls._phase_label(phase_name),
                }

                context = cls._build_context(phase_name, state)
                prompt = PHASE_PROMPTS.get(phase_name, PHASE_PROMPTS["qishu"]).format(
                    idea=idea,
                    qishu_output=state.phase_outputs.get("qishu", ""),
                    context=context,
                )

                try:
                    # 流式输出当前阶段的生成内容
                    system_prompt = WORKFLOW_SYSTEM_PROMPTS.get(
                        phase_name,
                        f"你是 Ssuma 的{phase_name}专家。请输出完整的分析报告。"
                    )
                    full_response = ""
                    async for chunk in provider.chat_stream(
                        [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=cls._max_tokens_for_phase(phase_name),
                    ):
                        full_response += chunk
                        yield {
                            "type": "phase_content",
                            "phase": phase_name,
                            "content": chunk,
                        }

                    state.phase_outputs[phase_name] = full_response.strip()

                except Exception as e:
                    logger.error(f"AutoPilot stream phase {phase_name} failed: {e}")
                    state.phase_outputs[phase_name] = f"[{phase_name} 阶段失败: {str(e)}]"
                    yield {
                        "type": "phase_error",
                        "phase": phase_name,
                        "error": str(e),
                    }

                yield {
                    "type": "phase_complete",
                    "phase": phase_name,
                    "index": i + 1,
                    "total": len(phases),
                    "output_length": len(state.phase_outputs.get(phase_name, "")),
                }

            # 导出 IDE 文件
            yield {"type": "export_start"}
            try:
                from services.ide_exporter import IDEExporter

                exported = IDEExporter.export({
                    "name": project_id.replace("proj-", "project-"),
                    "description": idea,
                    "product_spec": state.phase_outputs.get("qishu", ""),
                    "tech_spec": state.phase_outputs.get("zhenwei", "")
                                or state.phase_outputs.get("caiheng", ""),
                    "exec_spec": state.phase_outputs.get("ceshu", ""),
                    "features": [],
                })
                yield {
                    "type": "export_complete",
                    "file_count": len(exported.files),
                    "files": exported.files,
                }
            except Exception as e:
                yield {"type": "export_error", "error": str(e)}

            state.status = "completed"
            state.completed_at = datetime.now().isoformat()
            yield {"type": "complete", "project_id": project_id}

        except Exception as e:
            state.status = "failed"
            state.error = str(e)
            yield {"type": "error", "error": str(e)}

    @classmethod
    def _build_context(cls, current_phase: str, state: AutoPilotState) -> str:
        """为当前阶段构建累积上下文"""
        # 定义每个阶段可以看到的前序阶段
        phase_deps = {
            "qishu": [],
            "caiheng": ["qishu"],
            "zhenwei": ["qishu", "caiheng"],
            "ceshu": ["qishu", "caiheng", "zhenwei"],
            "ningmo": ["qishu", "caiheng", "zhenwei", "ceshu"],
            "powang": ["qishu", "caiheng", "zhenwei", "ceshu", "ningmo"],
            "jianyan": ["qishu", "caiheng", "zhenwei", "ceshu", "ningmo", "powang"],
        }

        deps = phase_deps.get(current_phase, [])
        if not deps:
            return "（无需前序上下文）"

        parts = []
        for dep in deps:
            output = state.phase_outputs.get(dep, "")
            if output:
                # 限制每个阶段的输入长度
                parts.append(f"【{dep} 阶段产出】\n{output[:3000]}")

        return "\n\n---\n\n".join(parts)

    @classmethod
    def _max_tokens_for_phase(cls, phase: str) -> int:
        return {
            "qishu": 2048,
            "caiheng": 2048,
            "zhenwei": 3072,
            "ceshu": 4096,
            "ningmo": 6144,
            "powang": 2048,
            "jianyan": 3072,
        }.get(phase, 2048)

    @classmethod
    def _phase_label(cls, phase: str) -> str:
        labels = {
            "qishu": "启枢 · 追问澄清",
            "caiheng": "裁衡 · 价值审视",
            "zhenwei": "甄微 · 技术评审",
            "ceshu": "策书 · 任务规划",
            "ningmo": "凝墨 · 方案整合",
            "powang": "破妄 · 覆盖验证",
            "jianyan": "渐衍 · 分阶段生成",
        }
        return labels.get(phase, phase)

    @classmethod
    def get_status(cls, project_id: str) -> Optional[Dict[str, Any]]:
        """查询自动流水线状态"""
        state = cls._active_jobs.get(project_id)
        if not state:
            return None
        return {
            "project_id": state.project_id,
            "status": state.status,
            "current_phase_index": state.current_phase_index,
            "phase_outputs": {
                k: len(v) for k, v in state.phase_outputs.items()
            },
            "error": state.error,
            "started_at": state.started_at,
            "completed_at": state.completed_at,
        }

    @classmethod
    def cancel(cls, project_id: str) -> bool:
        """取消自动流水线"""
        if project_id in cls._active_jobs:
            cls._active_jobs[project_id].status = "cancelled"
            return True
        return False
