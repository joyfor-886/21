"""
GarbageDetector - 垃圾输出检测
实时检测并标记低质量输出
"""

from typing import List, Dict, Any, Tuple
import re


class GarbageDetector:
    """垃圾输出检测"""
    
    # 垃圾特征模式
    GARBAGE_PATTERNS = [
        # 空洞开头
        (r"^好的，我来", "空洞开头"),
        (r"^作为一个AI", "角色混乱"),
        (r"^作为AI助手", "角色混乱"),
        (r"^很高兴", "客套话"),
        (r"^当然可以", "无实质"),
        # 空洞结尾
        (r"总之，[^。]{0,20}$", "无结论结尾"),
        (r"如有其他问题", "模板结尾"),
        (r"希望对你有帮助", "模板结尾"),
        # 重复内容
        (r"(.{50,})\1", "内容重复"),  # 同一段重复
        # 全是套话
        (r"^(好的，|当然，|好的，)", "全是客套"),
    ]
    
    # 高质量特征（加分项）
    HIGH_QUALITY_PATTERNS = [
        (r"```[\s\S]*```", "包含代码块"),  # 代码块
        (r"\|.*\|.*\|", "包含表格"),       # Markdown 表格
        (r"src/|app/|\.tsx|\.py", "包含文件路径"),
        (r"^\d+\.", "包含编号列表"),
        (r"^#+\s", "包含标题结构"),
    ]
    
    @classmethod
    def detect(cls, text: str, threshold: float = 0.3) -> Tuple[bool, Dict[str, Any]]:
        """
        检测是否为垃圾输出
        返回: (is_garbage, details)
        """
        if not text or len(text.strip()) < 50:
            return True, {
                "reason": "回复过短",
                "length": len(text),
                "final_score": 1.0,
                "matched_patterns": [],
                "quality_bonus": 0,
                "substance_ratio": 0.0,
            }
        
        text = text.strip()
        score = 0.0  # 垃圾分数 (越高越垃圾)
        details = {
            "length": len(text),
            "matched_patterns": [],
            "quality_bonus": 0,
            "final_score": 0.0
        }
        
        # 1. 检查垃圾模式
        for pattern, desc in cls.GARBAGE_PATTERNS:
            if re.search(pattern, text, re.MULTILINE):
                score += 0.15
                details["matched_patterns"].append(desc)
        
        # 2. 检查高质量特征（减分）
        bonus = 0
        for pattern, desc in cls.HIGH_QUALITY_PATTERNS:
            if re.search(pattern, text, re.MULTILINE):
                bonus += 1
                details["quality_bonus"] += 1
        
        # 3. 长度权重
        if len(text) < 200:
            score += 0.3
        elif len(text) < 500:
            score += 0.1
        
        # 4. 实质性内容检查
        # 计算"非客套话"比例
        substance = cls._calculate_substance(text)
        if substance < 0.3:
            score += 0.2
        
        # 5. 应用高质量加分
        score -= bonus * 0.1
        score = max(0.0, min(1.0, score))
        
        details["substance_ratio"] = substance
        details["final_score"] = round(score, 2)
        
        is_garbage = score > threshold
        return is_garbage, details
    
    @classmethod
    def _calculate_substance(cls, text: str) -> float:
        """计算实质性内容比例"""
        # 去除代码块
        code_blocks = re.findall(r"```[\s\S]*?```", text)
        text_without_code = re.sub(r"```[\s\S]*?```", "", text)
        
        # 去除常见客套话
        filler_phrases = [
            "好的，", "当然，", "作为AI", "很高兴",
            "希望对你有帮助", "如有其他问题", "请随时告诉我"
        ]
        
        cleaned = text_without_code
        for phrase in filler_phrases:
            cleaned = cleaned.replace(phrase, "")
        
        if not cleaned.strip():
            return 0.0
        
        # 实质性内容 = 包含具体信息的句子
        sentences = re.split(r"[。！？\n]+", cleaned)
        substantial = sum(1 for s in sentences if len(s.strip()) > 20)
        
        return substantial / max(len(sentences), 1)
    
    @classmethod
    def get_improvement_suggestions(cls, details: Dict[str, Any]) -> List[str]:
        suggestions = []

        if details.get("length", 0) < 500:
            suggestions.append("回复太短，需要更详细的分析")

        if "空洞开头" in details.get("matched_patterns", []):
            suggestions.append("避免空洞的客套话开头，直接切入主题")

        if "角色混乱" in details.get("matched_patterns", []):
            suggestions.append("保持专业角色定位，不要强调自己是AI")

        if details.get("substance_ratio", 1) < 0.5:
            suggestions.append("增加实质性内容，减少客套话")
        
        if not suggestions:
            suggestions.append("输出质量良好")
        
        return suggestions


# 全局实例
garbage_detector = GarbageDetector()
