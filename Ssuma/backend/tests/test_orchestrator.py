import pytest
from services.orchestrator import OrchestratorService, OrchestratorTask, TaskStatus


class TestOrchestrator:

    @pytest.mark.asyncio
    async def test_create_project_tasks(self):
        spec = {
            "tasks": [
                {
                    "title": "Setup project",
                    "description": "Initialize project files",
                    "file": "package.json",
                    "test": "test/package.test.ts",
                    "dependencies": []
                },
                {
                    "title": "Implement auth",
                    "description": "Add authentication",
                    "file": "src/auth.ts",
                    "dependencies": ["task-1"]
                }
            ]
        }
        
        tasks = await OrchestratorService.create_project_tasks("test-proj", spec)
        
        assert len(tasks) == 2
        assert tasks[0].id == "task-1"
        assert tasks[0].title == "Setup project"
        assert tasks[0].status == TaskStatus.PENDING
        assert tasks[1].dependencies == ["task-1"]

    @pytest.mark.asyncio
    async def test_get_current_task(self):
        spec = {
            "tasks": [
                {"title": "Task 1", "description": "First task", "file": "f1.ts", "dependencies": []},
                {"title": "Task 2", "description": "Second task", "file": "f2.ts", "dependencies": ["task-1"]}
            ]
        }
        
        await OrchestratorService.create_project_tasks("proj-2", spec)
        current = OrchestratorService.get_current_task("proj-2")
        
        assert current is not None
        assert current.id == "task-1"

    @pytest.mark.asyncio
    async def test_complete_task(self):
        spec = {
            "tasks": [
                {"title": "Task 1", "description": "First", "file": "f1.ts", "dependencies": []}
            ]
        }
        
        await OrchestratorService.create_project_tasks("proj-3", spec)
        result = OrchestratorService.complete_task("proj-3", "task-1")
        
        assert result is True
        current = OrchestratorService.get_current_task("proj-3")
        assert current is None

    @pytest.mark.asyncio
    async def test_get_progress(self):
        spec = {
            "tasks": [
                {"title": "Task 1", "description": "First", "file": "f1.ts", "dependencies": []},
                {"title": "Task 2", "description": "Second", "file": "f2.ts", "dependencies": []}
            ]
        }
        
        await OrchestratorService.create_project_tasks("proj-4", spec)
        OrchestratorService.complete_task("proj-4", "task-1")
        
        progress = OrchestratorService.get_progress("proj-4")
        
        assert progress["total"] == 2
        assert progress["completed"] == 1

    @pytest.mark.asyncio
    async def test_reset_project(self):
        spec = {
            "tasks": [
                {"title": "Task 1", "description": "First", "file": "f1.ts", "dependencies": []}
            ]
        }
        
        await OrchestratorService.create_project_tasks("proj-5", spec)
        OrchestratorService.reset_project("proj-5")
        
        progress = OrchestratorService.get_progress("proj-5")
        assert progress["total"] == 0