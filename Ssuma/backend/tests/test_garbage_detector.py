import pytest
from core.garbage_detector import GarbageDetector


def test_detect_normal_response():
    text = (
        "## 技术方案\n\n"
        "根据需求分析，建议采用以下架构：\n\n"
        "1. 前端使用 React + TypeScript\n"
        "2. 后端使用 Go + PostgreSQL\n"
        "3. 采用 RESTful API 设计\n\n"
        "核心模块包括用户认证、数据管理和实时通知。\n\n"
        "```python\n"
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n\n"
        "@app.get('/api/health')\n"
        "async def health():\n"
        "    return {'status': 'ok'}\n"
        "```\n\n"
        "以上方案覆盖了项目的核心功能需求。"
    )
    is_garbage, details = GarbageDetector.detect(text)
    assert is_garbage == False, f"Expected clean, got garbage: {details}"


def test_detect_too_short():
    is_garbage, details = GarbageDetector.detect("好的")
    assert is_garbage == True
    assert details.get("reason") == "回复过短"


def test_detect_empty():
    is_garbage, details = GarbageDetector.detect("")
    assert is_garbage == True


def test_detect_garbage_pattern():
    text = "好的，我来帮你分析一下。" + "a" * 300
    is_garbage, details = GarbageDetector.detect(text)
    assert is_garbage == True


def test_detect_code_response():
    text = (
        "以下是根据需求生成的完整实现方案：\n\n"
        "```python\n"
        "import asyncio\n\n"
        "async def main():\n"
        "    print('hello world')\n"
        "    await asyncio.sleep(1)\n\n"
        "if __name__ == '__main__':\n"
        "    asyncio.run(main())\n"
        "```\n\n"
        "以上代码实现了异步任务调度功能，可根据实际需求调整参数。"
    )
    is_garbage, details = GarbageDetector.detect(text)
    assert is_garbage == False, f"Expected clean, got garbage: {details}"


def test_detect_structured_response():
    text = (
        "## 需求分析结果\n\n"
        "经过与用户的深入讨论，明确了以下核心需求：\n\n"
        "### 核心需求\n"
        "- 用户需要一个便捷的记账工具来管理日常收支\n"
        "- 支持多设备之间的数据同步和备份功能\n"
        "- 自动分类统计各项支出并生成可视化报表\n\n"
        "### 目标用户\n"
        "- 25-35岁的自由职业者群体\n"
        "- 需要管理多个收入来源和税务记录\n\n"
        "### 推荐技术方案\n"
        "采用前后端分离架构，前端使用 React 构建响应式界面，"
        "后端提供 RESTful API 进行数据交互，数据库选用 PostgreSQL"
        "来存储用户信息和交易记录，确保数据安全和一致性。"
    )
    is_garbage, details = GarbageDetector.detect(text)
    assert is_garbage == False, f"Expected clean, got garbage: {details}"


def test_detect_generic_greeting():
    text = "好的，我来帮你。好的，我来帮你。好的，我来帮你。好的，我来帮你。好的，我来帮你。好的，我来帮你。这是一些内容。"
    is_garbage, details = GarbageDetector.detect(text)
    assert is_garbage == True


def test_get_improvement_suggestions():
    _, details = GarbageDetector.detect("好的，我来帮你分析一下。" + "x" * 200)
    suggestions = GarbageDetector.get_improvement_suggestions(details)
    assert isinstance(suggestions, list)
    assert len(suggestions) > 0
