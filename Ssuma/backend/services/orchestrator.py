import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger('Ssuma.Orchestrator')

STATE_SERVICE_NAME = "orchestrator"


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

    def to_dict_value(self) -> str:
        return self.value

    @classmethod
    def from_dict_value(cls, val: str) -> "TaskStatus":
        try:
            return cls(val)
        except ValueError:
            return cls.PENDING


@dataclass
class OrchestratorTask:
    id: str
    title: str
    description: str
    file_path: str
    test_path: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    prompt: str = ""
    verification: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "test_path": self.test_path,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "prompt": self.prompt,
            "verification": self.verification,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrchestratorTask":
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            file_path=data.get("file_path", ""),
            test_path=data.get("test_path"),
            dependencies=data.get("dependencies", []),
            status=TaskStatus.from_dict_value(data.get("status", "pending")),
            prompt=data.get("prompt", ""),
            verification=data.get("verification", ""),
            error=data.get("error"),
        )


@dataclass
class OrchestratorProject:
    project_id: str
    tasks: List[OrchestratorTask] = field(default_factory=list)
    current_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "tasks": [t.to_dict() for t in self.tasks],
            "current_index": self.current_index,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrchestratorProject":
        return cls(
            project_id=data.get("project_id", ""),
            tasks=[OrchestratorTask.from_dict(t) for t in data.get("tasks", [])],
            current_index=data.get("current_index", 0),
        )


class OrchestratorService:
    """Beta: Step-by-step task execution orchestrator."""

    _projects: Dict[str, OrchestratorProject] = {}
    _MAX_INMEMORY_PROJECTS = 100

    @classmethod
    def _evict_if_needed(cls):
        if len(cls._projects) <= cls._MAX_INMEMORY_PROJECTS:
            return
        evict_count = len(cls._projects) - cls._MAX_INMEMORY_PROJECTS + 10
        keys_to_evict = list(cls._projects.keys())[:evict_count]
        for key in keys_to_evict:
            del cls._projects[key]
        logger.info(f"Evicted {len(keys_to_evict)} orchestrator projects from memory")

    @classmethod
    def _ensure_loaded(cls, project_id: str):
        if project_id not in cls._projects:
            from core.state_repository import StateRepository
            data = StateRepository.load(STATE_SERVICE_NAME, project_id)
            if data is not None:
                cls._projects[project_id] = OrchestratorProject.from_dict(data)
            else:
                cls._projects[project_id] = OrchestratorProject(project_id=project_id)
            cls._evict_if_needed()

    @classmethod
    def _save_to_repo(cls, project_id: str):
        from core.state_repository import StateRepository
        project = cls._projects.get(project_id)
        if project:
            StateRepository.save(STATE_SERVICE_NAME, project_id, project.to_dict())

    @classmethod
    async def create_project_tasks(cls, project_id: str, spec: Dict[str, Any]) -> List[OrchestratorTask]:
        """Create task queue from project spec."""
        cls._ensure_loaded(project_id)
        tasks = []
        
        for i, task_spec in enumerate(spec.get("tasks", [])):
            task = OrchestratorTask(
                id=f"task-{i+1}",
                title=task_spec.get("title", f"Task {i+1}"),
                description=task_spec.get("description", ""),
                file_path=task_spec.get("file", ""),
                test_path=task_spec.get("test", ""),
                dependencies=task_spec.get("dependencies", []),
                prompt=task_spec.get("prompt", ""),
                verification=task_spec.get("verification", "")
            )
            tasks.append(task)
        
        project = OrchestratorProject(project_id=project_id, tasks=tasks)
        cls._projects[project_id] = project
        cls._save_to_repo(project_id)
        
        logger.info(f"Created {len(tasks)} tasks for {project_id}")
        return tasks

    @classmethod
    def get_current_task(cls, project_id: str) -> Optional[OrchestratorTask]:
        """Get the current task to work on."""
        cls._ensure_loaded(project_id)
        project = cls._projects.get(project_id)
        if not project:
            return None
        
        for task in project.tasks:
            if task.status == TaskStatus.IN_PROGRESS:
                return task
        
        if project.current_index < len(project.tasks):
            task = project.tasks[project.current_index]
            if cls._can_start(task, project.tasks):
                return task
        
        return None

    @classmethod
    def _can_start(cls, task: OrchestratorTask, all_tasks: List[OrchestratorTask]) -> bool:
        """Check if task dependencies are met."""
        for dep_id in task.dependencies:
            for t in all_tasks:
                if t.id == dep_id and t.status != TaskStatus.COMPLETED:
                    return False
        return True

    @classmethod
    def get_task_prompt(cls, project_id: str) -> Optional[str]:
        """Get the prompt for current task."""
        task = cls.get_current_task(project_id)
        if not task:
            return None
        
        task.status = TaskStatus.IN_PROGRESS
        cls._save_to_repo(project_id)
        
        return f"""## {task.title}

### 描述
{task.description}

### 文件
{task.file_path}

{f"### 测试文件\n{task.test_path}" if task.test_path else ""}

### 验证步骤
{task.verification}

### 执行步骤
1. 查看/创建 {task.file_path}
2. 运行测试验证失败
3. 实现最小功能
4. 运行测试验证通过
5. 提交更改"""

    @classmethod
    def complete_task(cls, project_id: str, task_id: str) -> bool:
        """Mark task as complete."""
        cls._ensure_loaded(project_id)
        project = cls._projects.get(project_id)
        if not project:
            return False
        
        for task in project.tasks:
            if task.id == task_id:
                task.status = TaskStatus.COMPLETED
                project.current_index += 1
                cls._save_to_repo(project_id)
                return True
        return False

    @classmethod
    def fail_task(cls, project_id: str, task_id: str, error: str) -> bool:
        """Mark task as failed with error."""
        cls._ensure_loaded(project_id)
        project = cls._projects.get(project_id)
        if not project:
            return False
        
        for task in project.tasks:
            if task.id == task_id:
                task.status = TaskStatus.FAILED
                task.error = error
                cls._save_to_repo(project_id)
                return True
        return False

    @classmethod
    async def analyze_error(cls, project_id: str, error_message: str) -> Dict[str, Any]:
        """Analyze error and generate fix prompt."""
        from core.llm_factory import LLMFactory
        
        project = cls._projects.get(project_id)
        current_task = None
        if project:
            for task in project.tasks:
                if task.status == TaskStatus.IN_PROGRESS:
                    current_task = task
                    break
        
        prompt = f"""你是一个错误分析专家。请分析以下错误并提供修复方案。

错误信息：
```
{error_message}
```

{f"当前任务：{current_task.title}\n任务描述：{current_task.description}" if current_task else ""}

请分析：
1. 错误类型
2. 根本原因
3. 修复步骤（具体代码）

请简洁回答。"""

        try:
            provider = LLMFactory.get_provider()
            fix_suggestion = await provider.chat(
                [{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.3
            )
            
            return {
                "error": error_message,
                "fix": fix_suggestion,
                "task_id": current_task.id if current_task else None,
                "can_retry": True
            }
        except Exception as e:
            logger.error(f"Error analysis failed: {e}")
            return {
                "error": error_message,
                "fix": f"分析失败: {str(e)}",
                "can_retry": False
            }

    @classmethod
    def get_progress(cls, project_id: str) -> Dict[str, Any]:
        """Get project progress."""
        cls._ensure_loaded(project_id)
        project = cls._projects.get(project_id)
        if not project:
            return {"total": 0, "completed": 0, "current": None}
        
        completed = sum(1 for t in project.tasks if t.status == TaskStatus.COMPLETED)
        current = None
        for task in project.tasks:
            if task.status == TaskStatus.IN_PROGRESS:
                current = {"id": task.id, "title": task.title}
                break
        
        return {
            "total": len(project.tasks),
            "completed": completed,
            "current": current,
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status.value,
                    "error": t.error
                }
                for t in project.tasks
            ]
        }

    @classmethod
    def reset_project(cls, project_id: str):
        """Reset project state."""
        if project_id in cls._projects:
            del cls._projects[project_id]
        from core.state_repository import StateRepository
        StateRepository.delete(STATE_SERVICE_NAME, project_id)