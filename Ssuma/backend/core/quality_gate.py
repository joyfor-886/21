"""
QualityGate - 数据质量门控
确保所有进入学习系统的数据都是高质量的
"""

from typing import Dict, Any, Optional
from enum import Enum


class DataQuality(Enum):
    APPROVED = "approved"      # 通过
    REJECTED = "rejected"      # 拒绝
    PENDING = "pending"         # 待审核


class QualityGate:
    """质量门控 - 防止垃圾数据污染"""
    
    # 质量阈值
    MIN_SATISFACTION = 0.8      # 最低满意度
    MIN_SUCCESS_RATE = 0.9      # 最低成功率
    MIN_USAGE_COUNT = 5          # 最少使用次数
    MIN_RESPONSE_LENGTH = 100      # 最短回复长度
    MAX_RESPONSE_LENGTH = 10000    # 最长回复长度
    
    # 拒绝模式（垃圾特征）
    GARBAGE_KEYWORDS = [
        "好的，我来", "作为AI助手", "作为一个AI",
        "抱歉", "感谢", "当然可以",
        "让我想想", "这是一个好问题"
    ]
    
    @classmethod
    def evaluate_feedback(cls, feedback_data: Dict[str, Any]) -> DataQuality:
        """
        评估用户反馈质量
        返回: APPROVED / REJECTED / PENDING
        """
        score = feedback_data.get("score", 0)
        comments = feedback_data.get("comments", "")
        
        # 1. 满意度必须高
        if score < cls.MIN_SATISFACTION:
            return DataQuality.REJECTED
        
        # 2. 必须有评论（防止误触）
        if not comments or len(comments.strip()) < 10:
            return DataQuality.PENDING  # 待补充评论
        
        return DataQuality.APPROVED
    
    @classmethod
    def evaluate_response(cls, response: str, context: Dict[str, Any]) -> DataQuality:
        """
        评估AI回复质量
        """
        # 1. 长度检查
        if len(response) < cls.MIN_RESPONSE_LENGTH:
            return DataQuality.REJECTED
        if len(response) > cls.MAX_RESPONSE_LENGTH:
            return DataQuality.REJECTED
        
        # 2. 垃圾关键词检测
        for keyword in cls.GARBAGE_KEYWORDS:
            if keyword in response[:200]:  # 只检查开头
                return DataQuality.REJECTED
        
        # 3. 检查是否真正的"分析"而非"复述"
        if response.count("？") < 2 and "分析" not in response:
            # 太简单的回复
            if len(response) < 300:
                return DataQuality.REJECTED
        
        # 4. 检查是否包含实际内容（文件路径、代码示例等）
        has_code = "```" in response
        has_file_path = any(c in response for c in ["src/", "app/", ".tsx", ".py"])
        has_structure = "|" in response and "-" in response  # 表格
        
        if not (has_code or has_file_path or has_structure):
            # 纯文字回复，需要更长
            if len(response) < 500:
                return DataQuality.REJECTED
        
        return DataQuality.APPROVED
    
    @classmethod
    def evaluate_pattern(cls, pattern_data: Dict[str, Any]) -> DataQuality:
        """
        评估模式（pattern）是否值得学习
        """
        success_rate = pattern_data.get("success_rate", 0)
        usage_count = pattern_data.get("usage_count", 0)
        avg_satisfaction = pattern_data.get("avg_satisfaction", 0)
        
        if success_rate < cls.MIN_SUCCESS_RATE:
            return DataQuality.REJECTED
        
        if usage_count < cls.MIN_USAGE_COUNT:
            return DataQuality.PENDING  # 样本不足
        
        if avg_satisfaction < cls.MIN_SATISFACTION:
            return DataQuality.REJECTED
        
        return DataQuality.APPROVED
    
    @classmethod
    def should_learn(cls, data: Dict[str, Any], data_type: str = "response") -> tuple:
        """
        判断是否应该学习
        返回: (should_learn: bool, reason: str)
        """
        if data_type == "feedback":
            quality = cls.evaluate_feedback(data)
        elif data_type == "response":
            quality = cls.evaluate_response(data.get("text", ""), data)
        elif data_type == "pattern":
            quality = cls.evaluate_pattern(data)
        else:
            return False, f"Unknown data_type: {data_type}"
        
        if quality == DataQuality.APPROVED:
            return True, "Quality approved"
        elif quality == DataQuality.PENDING:
            return False, "Data pending (insufficient samples or details)"
        else:
            return False, "Data quality too low"


# 全局实例
quality_gate = QualityGate()
