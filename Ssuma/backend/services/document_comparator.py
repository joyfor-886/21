from typing import List, Dict, Any
from core.llm_factory import LLMFactory


class DocumentComparator:
    @staticmethod
    async def compare(documents: List[Dict[str, Any]], provider: str = "lm_studio") -> str:
        if len(documents) < 2:
            return "需要至少两个文档才能进行对比"
        
        doc_contents = []
        for doc in documents:
            doc_contents.append(f"### {doc['filename']}\n{doc['content'][:3000]}")
        
        prompt = f"""请对比以下文档，分析它们的异同点、关联性和潜在冲突：

{'\n\n---\n\n'.join(doc_contents)}

请从以下角度进行分析：
1. 主题和内容重叠度
2. 关键差异点
3. 潜在的矛盾或冲突
4. 互补性
5. 综合建议

请用中文回答。"""
        
        provider_instance = LLMFactory.get_provider(provider)
        messages = [
            {"role": "system", "content": "你是一个专业的文档分析助手，擅长对比和分析多个文档的内容。"},
            {"role": "user", "content": prompt}
        ]
        
        return await provider_instance.chat(messages, max_tokens=4096)
