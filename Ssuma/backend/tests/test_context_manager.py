import pytest
from services.context_manager import ContextManager, ContextWindow
import uuid


def test_context_window_add_message():
    window = ContextWindow()
    window.add_message("user", "Hello")
    window.add_message("assistant", "Hi there")
    assert len(window.recent_messages) == 2

def test_context_window_trim_to_size():
    window = ContextWindow()
    for i in range(10):
        window.add_message("user", "x" * 1000)
    assert window.total_chars <= 8000
    assert len(window.recent_messages) >= 1

def test_needs_summary():
    window = ContextWindow()
    window.total_chars = 6000
    assert window.needs_summary() == True
    window.total_chars = 3000
    assert window.needs_summary() == False

def test_to_messages_format():
    window = ContextWindow()
    window.add_message("user", "Hello")
    window.add_message("assistant", "Hi")
    window.summary = "Previous conversation summary"
    messages = window.to_messages_format()
    assert len(messages) >= 2
    assert messages[0]["role"] == "system"
    assert "摘要" in messages[0]["content"]

def test_add_decision():
    project_id = str(uuid.uuid4())
    ContextManager.add_decision(project_id, "Use Next.js for frontend")
    window = ContextManager.get_window(project_id)
    assert "Use Next.js for frontend" in window.key_decisions

def test_context_manager_status():
    project_id = str(uuid.uuid4())
    ContextManager.add_message(project_id, "user", "Test message")
    status = ContextManager.get_status(project_id)
    assert "summary_length" in status
    assert "recent_messages_count" in status
    assert status["recent_messages_count"] == 1

def test_context_manager_reset():
    project_id = str(uuid.uuid4())
    ContextManager.add_message(project_id, "user", "Test")
    ContextManager.reset(project_id)
    window = ContextManager.get_window(project_id)
    assert len(window.recent_messages) == 0
