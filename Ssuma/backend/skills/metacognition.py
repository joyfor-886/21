import logging
import json
import re
from typing import Dict, Any, List
from datetime import datetime
from core.skill_registry import Skill, SkillResult
from core.learning_db import LearningDB

logger = logging.getLogger('Ssuma.MetacognitionSkill')


class MetacognitionSkill(Skill):
    name = "metacognition"
    description = "元认知模块 - 分析系统性能，识别改进方向，生成进化建议"
    trigger = "metacognition"

    def __init__(self):
        self.db = LearningDB()
        self.analysis_history = []

    async def run(self, conversation: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        context = context or {}

        try:
            system_data = self._collect_system_data()
            skill_analysis = self._analyze_skills(system_data)
            patterns = self._identify_patterns(system_data)
            suggestions = self._generate_suggestions(skill_analysis, patterns)

            analysis = {
                "timestamp": datetime.now().isoformat(),
                "system_data": system_data,
                "skill_analysis": skill_analysis,
                "patterns": patterns,
                "suggestions": suggestions,
                "evolution_needed": self._check_evolution_needed(skill_analysis)
            }

            self.analysis_history.append(analysis)
            self._save_analysis(analysis)

            return SkillResult(
                response=self._generate_summary(analysis),
                stage="metacognition",
                metadata={"analysis": analysis},
            )
        except Exception as e:
            logger.error(f"Metacognition skill failed: {e}")
            return self._fallback_response()

    def _fallback_response(self) -> SkillResult:
        return SkillResult(
            response=(
                "⚠️ 元认知分析服务暂时不可用。\n\n"
                "系统自检摘要：\n"
                "- 如遇技能响应异常，请检查 LLM 服务状态\n"
                "- 如需清理学习数据，可使用管理端点\n"
                "- 建议定期检查各技能的运行质量\n\n"
                "💡 AI服务恢复后，可以重新执行完整分析。"
            ),
            stage="metacognition",
        )

    def _collect_system_data(self) -> Dict[str, Any]:
        """收集系统运行数据"""
        try:
            # 获取各技能统计
            skill_stats = {}
            for skill_name in ["qishu", "caiheng", "zhenwei", "ceshu", "ningmo", "powang", "jianyan"]:
                stats = self.db.get_skill_stats(skill_name)
                skill_stats[skill_name] = stats

            # 获取学习数据质量
            learning_quality = self._assess_learning_quality()

            # 获取用户反馈趋势
            feedback_trend = self._analyze_feedback_trend()

            return {
                "skill_stats": skill_stats,
                "learning_quality": learning_quality,
                "feedback_trend": feedback_trend,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error collecting system data: {e}")
            return {"error": str(e)}

    def _analyze_skills(self, system_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析各技能表现"""
        skill_analysis = {}

        for skill_name, stats in system_data.get("skill_stats", {}).items():
            if not stats:
                continue

            analysis = {
                "total_calls": stats.get("total_calls", 0),
                "success_rate": stats.get("success_rate", 0),
                "avg_satisfaction": stats.get("avg_satisfaction", 0),
                "quality_issues": self._detect_quality_issues(stats),
                "performance_grade": self._grade_performance(stats)
            }

            skill_analysis[skill_name] = analysis

        return skill_analysis

    def _identify_patterns(self, system_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别系统运行模式"""
        patterns = []

        feedback_trend = system_data.get("feedback_trend", {})

        # 检测满意度下降趋势
        if feedback_trend.get("trend") == "declining":
            patterns.append({
                "type": "declining_satisfaction",
                "severity": "high",
                "description": "用户满意度持续下降"
            })

        # 检测学习数据质量下降
        learning_quality = system_data.get("learning_quality", {})
        if learning_quality.get("score", 1.0) < 0.7:
            patterns.append({
                "type": "low_learning_quality",
                "severity": "medium",
                "description": "学习数据质量偏低"
            })

        return patterns

    def _generate_suggestions(self, skill_analysis: Dict[str, Any],
                              patterns: List[Dict[str, Any]]) -> List[str]:
        """生成改进建议"""
        suggestions = []

        # 基于技能分析的建议
        for skill_name, analysis in skill_analysis.items():
            if analysis.get("performance_grade") in ["C", "D"]:
                suggestions.append(f"{skill_name} 技能表现不佳，建议优化 prompt 或增加训练数据")

            if analysis.get("quality_issues"):
                suggestions.append(f"{skill_name} 存在质量问题：{', '.join(analysis['quality_issues'])}")

        # 基于模式的建议
        for pattern in patterns:
            if pattern["type"] == "declining_satisfaction":
                suggestions.append("建议启动破妄(powang)模式，清理低质量学习数据")
            elif pattern["type"] == "low_learning_quality":
                suggestions.append("建议检查 QualityGate 配置，提高数据准入门槛")

        return suggestions

    def _check_evolution_needed(self, skill_analysis: Dict[str, Any]) -> bool:
        """检查是否需要进化"""
        # 如果有超过3个技能表现不佳，建议进化
        poor_performers = sum(
            1 for a in skill_analysis.values()
            if a.get("performance_grade") in ["C", "D"]
        )
        return poor_performers >= 3

    def _assess_learning_quality(self) -> Dict[str, Any]:
        """评估学习数据质量"""
        try:
            stats = self.db.get_learning_stats()
            total = stats.get("total_entries", 0)
            high_quality = stats.get("high_quality_entries", 0)

            score = high_quality / total if total > 0 else 0

            return {
                "total_entries": total,
                "high_quality_entries": high_quality,
                "score": score,
                "grade": "A" if score >= 0.8 else "B" if score >= 0.6 else "C"
            }
        except Exception as e:
            logger.error(f"Error assessing learning quality: {e}")
            return {"score": 0, "grade": "F"}

    def _analyze_feedback_trend(self) -> Dict[str, Any]:
        """分析反馈趋势"""
        try:
            # 获取最近100条反馈
            recent_feedbacks = self.db.get_recent_feedbacks(limit=100)

            if len(recent_feedbacks) < 10:
                return {"trend": "stable", "confidence": "low"}

            # 简单趋势分析
            scores = [f.get("satisfaction", 0) for f in recent_feedbacks]
            avg_score = sum(scores) / len(scores)

            if avg_score < 0.6:
                return {"trend": "declining", "confidence": "medium"}
            elif avg_score > 0.8:
                return {"trend": "improving", "confidence": "medium"}
            else:
                return {"trend": "stable", "confidence": "medium"}
        except Exception as e:
            logger.error(f"Error analyzing feedback trend: {e}")
            return {"trend": "unknown", "confidence": "none"}

    def _detect_quality_issues(self, stats: Dict[str, Any]) -> List[str]:
        """检测质量问题"""
        issues = []

        if stats.get("success_rate", 1) < 0.8:
            issues.append("成功率偏低")

        if stats.get("avg_satisfaction", 1) < 0.7:
            issues.append("满意度偏低")

        if stats.get("total_calls", 0) > 100 and stats.get("success_rate", 1) < 0.9:
            issues.append("调用量大但成功率不高")

        return issues

    def _grade_performance(self, stats: Dict[str, Any]) -> str:
        """给技能表现评级"""
        success_rate = stats.get("success_rate", 0)
        satisfaction = stats.get("avg_satisfaction", 0)

        score = (success_rate * 0.6 + satisfaction * 0.4)

        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.6:
            return "C"
        else:
            return "D"

    def _generate_summary(self, analysis: Dict[str, Any]) -> str:
        """生成分析摘要"""
        skill_analysis = analysis.get("skill_analysis", {})
        suggestions = analysis.get("suggestions", [])
        evolution_needed = analysis.get("evolution_needed", False)

        summary = f"系统分析完成，共分析 {len(skill_analysis)} 个技能。\n"

        if evolution_needed:
            summary += "⚠️ 系统表现不佳，建议启动进化流程。\n"

        if suggestions:
            summary += f"发现 {len(suggestions)} 个改进点：\n"
            for i, suggestion in enumerate(suggestions[:3], 1):
                summary += f"  {i}. {suggestion}\n"

        return summary

    def _save_analysis(self, analysis: Dict[str, Any]):
        """保存分析结果"""
        try:
            self.db.save_metacognition_analysis(analysis)
        except Exception as e:
            logger.error(f"Error saving analysis: {e}")
