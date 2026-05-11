import pytest
from services.scaffold_generator import ScaffoldGenerator
import os
import tempfile

def test_generate_nextjs_supabase_scaffold():
    config = {
        "name": "My App",
        "tech_stack": "Next.js + Supabase",
        "data_model": {"users": ["id", "email", "name"]}
    }
    
    # Generate scaffold returns a dict of file_path -> content
    files = ScaffoldGenerator.generate(config)
    
    assert isinstance(files, dict)
    assert len(files) > 0
    # Check essential Next.js files
    assert any("package.json" in path for path in files.keys())
    assert any("next.config" in path for path in files.keys())
    assert any("tailwind.config" in path for path in files.keys())
    # Check context files are included
    assert any("context.md" in path for path in files.keys())
