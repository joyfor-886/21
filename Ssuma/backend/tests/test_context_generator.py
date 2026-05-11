import pytest
from services.context_generator import ContextGenerator

def test_generate_context_returns_dict():
    spec = {
        "name": "Test Project",
        "description": "A simple test project",
        "features": ["Feature 1", "Feature 2"],
        "tech_stack": "Next.js + Supabase"
    }
    result = ContextGenerator.generate(spec)
    
    assert isinstance(result, dict)
    assert "context.md" in result
    assert "spec.md" in result
    assert "data_model.md" in result
    assert "tech_stack.md" in result

def test_context_md_contains_all_info():
    spec = {
        "name": "My App",
        "description": "An AI-powered writing assistant",
        "features": ["Chat", "Export", "Auth"],
        "tech_stack": "Next.js + Supabase",
        "data_model": {"users": ["id", "name", "email"]}
    }
    result = ContextGenerator.generate(spec)
    
    context_md = result["context.md"]
    assert "My App" in context_md
    assert "An AI-powered writing assistant" in context_md
    assert "Chat" in context_md
    assert "Next.js + Supabase" in context_md
