"""反思循环（Reflexion）— 输出→反思→纠正→再输出

参考 NeoLabHQ/reflexion 的自精炼循环设计。

核心机制：
  1. 生成初始输出
  2. LLM 反思：检查输出是否遗漏了关键信息
  3. 如果发现问题，生成纠正后的输出
  4. 最多循环 max_rounds 次

使用场景：
  - 凝墨阶段（方案生成后自检）
  - 甄微阶段（架构设计后检查遗漏）

与 EvolutionEngine 的区别：
  - EvolutionEngine 是跨项目的长期进化（第三层记忆）
  - Reflexion 是单次会话内的短期自纠正（第一层记忆增强）
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger('Ssuma.Reflexion')


class ReflexionResult:
    """反思循环结果"""

    def __init__(
        self,
        final_output: str,
        initial_output: str,
        reflections: List[str],
        corrections: List[str],
        rounds: int,
        improved: bool,
    ):
        self.final_output = final_output
        self.initial_output = initial_output
        self.reflections = reflections
        self.corrections = corrections
        self.rounds = rounds
        self.improved = improved

    def to_dict(self) -> Dict[str, Any]:
        return {
            "final_output": self.final_output,
            "rounds": self.rounds,
            "improved": self.improved,
            "reflections_count": len(self.reflections),
            "corrections_count": len(self.corrections),
        }


async def reflexion_loop(
    initial_output: str,
    phase: str,
    conversation: str,
    llm_provider=None,
    max_rounds: int = 2,
    phase_dimensions: Optional[Dict[str, str]] = None,
) -> ReflexionResult:
    """反思循环

    Args:
        initial_output: 初始生成的输出
        phase: 当前阶段
        conversation: 对话上下文
        llm_provider: LLM 提供者
        max_rounds: 最大反思轮数
        phase_dimensions: 阶段必须覆盖的维度 {key: description}

    Returns:
        ReflexionResult 包含最终输出和反思过程
    """
    if llm_provider is None:
        try:
            from core.llm_factory import LLMFactory
            llm_provider = LLMFactory.get_provider()
        except Exception:
            return ReflexionResult(
                final_output=initial_output,
                initial_output=initial_output,
                reflections=[],
                corrections=[],
                rounds=0,
                improved=False,
            )

    current_output = initial_output
    all_reflections = []
    all_corrections = []

    for round_num in range(max_rounds):
        # 反思：检查当前输出是否有遗漏
        reflection = await _reflect(
            current_output, phase, conversation, llm_provider, phase_dimensions
        )

        if not reflection or reflection.get("is_complete", True):
            break

        all_reflections.append(reflection.get("reasoning", ""))

        # 纠正：基于反思结果改进输出
        correction = await _correct(
            current_output, reflection, phase, llm_provider
        )

        if correction and correction != current_output:
            all_corrections.append(correction)
            current_output = correction
        else:
            break

    improved = current_output != initial_output

    if improved:
        logger.info(f"Reflexion improved output for {phase} in {len(all_reflections)} rounds")
    else:
        logger.debug(f"Reflexion found no improvements for {phase}")

    return ReflexionResult(
        final_output=current_output,
        initial_output=initial_output,
        reflections=all_reflections,
        corrections=all_corrections,
        rounds=len(all_reflections),
        improved=improved,
    )


async def _reflect(
    output: str,
    phase: str,
    conversation: str,
    llm_provider,
    phase_dimensions: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, Any]]:
    """反思：检查输出是否有遗漏"""
    dim_text = ""
    if phase_dimensions:
        dim_text = "\n必须覆盖的维度：\n" + "\n".join(
            f"- {k}: {v}" for k, v in phase_dimensions.items()
        )

    prompt = f"""请反思以下{phase}阶段的输出是否完整。

{dim_text}

用户对话摘要：
{conversation[-1500:]}

当前输出：
{output[:2000]}

请用 JSON 返回：
{{
  "is_complete": true/false,
  "reasoning": "简短说明遗漏了什么",
  "missing_points": ["遗漏点1", "遗漏点2"]
}}

只返回 JSON。"""

    try:
        import asyncio
        response = await asyncio.wait_for(
            llm_provider.chat(
                [{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.1,
            ),
            timeout=15.0,
        )

        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            import json
            return json.loads(json_match.group())

    except Exception as e:
        logger.warning(f"Reflect failed: {e}")

    return None


async def _correct(
    current_output: str,
    reflection: Dict[str, Any],
    phase: str,
    llm_provider,
) -> Optional[str]:
    """纠正：基于反思结果改进输出"""
    missing = reflection.get("missing_points", [])
    reasoning = reflection.get("reasoning", "")

    if not missing and not reasoning:
        return None

    prompt = f"""请改进以下{phase}阶段的输出，补充遗漏的内容。

当前输出：
{current_output[:2000]}

遗漏的内容：
{reasoning}
{chr(10).join(f"- {m}" for m in missing)}

请输出改进后的完整内容（不要只输出补充部分）："""

    try:
        import asyncio
        response = await asyncio.wait_for(
            llm_provider.chat(
                [{"role": "user", "content": prompt}],
                max_tokens=4096,
                temperature=0.3,
            ),
            timeout=30.0,
        )
        return response.strip() if response else None

    except Exception as e:
        logger.warning(f"Correct failed: {e}")

    return None
