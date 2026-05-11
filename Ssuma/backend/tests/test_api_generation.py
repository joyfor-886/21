from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_generate_context_endpoint():
    response = client.post("/api/v1/generate/context", json={
        "project_id": "test-123",
        "name": "Test App",
        "description": "A test app",
        "features": ["Auth", "Chat"]
    })
    assert response.status_code == 200
    data = response.json()
    assert "files" in data
    assert "context.md" in data["files"]
    assert "download_url" in data

def test_generate_scaffold_endpoint():
    response = client.post("/api/v1/generate/scaffold", json={
        "project_id": "test-123",
        "name": "Test App",
        "tech_stack": "Next.js + Supabase"
    })
    assert response.status_code == 200
    data = response.json()
    assert "files_count" in data
    assert data["files_count"] > 0
