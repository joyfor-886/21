import os
import uuid
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File

from db.sqlite import Database
from core.errors import SsumaError, ErrorCode

logger = logging.getLogger('Ssuma.ProjectsAPI')

router = APIRouter(prefix="", tags=["projects"])


@router.post("/projects", response_model=dict)
async def create_project(project: dict):
    db = Database()
    project_id = project.get("id", str(uuid.uuid4()))
    name = project.get("name", "New Project")
    description = project.get("description", "")
    db.execute(
        "INSERT INTO projects (id, name, description) VALUES (?, ?, ?)",
        (project_id, name, description)
    )
    return {"project_id": project_id, "name": name}


@router.get("/projects", response_model=list)
async def list_projects():
    db = Database()
    projects = db.fetchall("SELECT * FROM projects ORDER BY created_at DESC")
    return [dict(p) for p in projects]


@router.get("/projects/{project_id}/messages", response_model=list)
async def get_messages(project_id: str):
    db = Database()
    messages = db.fetchall(
        "SELECT * FROM messages WHERE project_id = ? ORDER BY timestamp ASC",
        (project_id,)
    )
    return [dict(m) for m in messages]


@router.get("/projects/{project_id}/stats", response_model=dict)
async def get_project_stats(project_id: str):
    db = Database()
    msg_count = db.fetchone("SELECT COUNT(*) as count FROM messages WHERE project_id = ?", (project_id,))
    return {
        "project_id": project_id,
        "message_count": msg_count["count"] if msg_count else 0
    }


@router.post("/projects/{project_id}/generate-spec", response_model=dict)
async def generate_spec(project_id: str):
    return {"success": True, "message": "Spec generation started"}


@router.post("/projects/{project_id}/generate-mindmap", response_model=dict)
async def generate_mindmap(project_id: str):
    return {"success": True, "message": "Mindmap generation started"}


@router.post("/projects/{project_id}/upload", response_model=dict)
async def upload_file(project_id: str, file: UploadFile = File(...)):
    try:
        content = await file.read()
        save_dir = Path("uploads") / project_id
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / file.filename
        file_path.write_bytes(content)
        return {"success": True, "filename": file.filename, "path": str(file_path)}
    except Exception as e:
        raise SsumaError(ErrorCode.INTERNAL_ERROR, str(e))


@router.get("/projects/{project_id}/documents", response_model=list)
async def list_documents(project_id: str):
    return []


@router.get("/projects/{project_id}/documents/{doc_id}", response_model=dict)
async def get_document(project_id: str, doc_id: str):
    return {"id": doc_id, "content": ""}


@router.post("/projects/{project_id}/compare-documents", response_model=dict)
async def compare_documents(project_id: str):
    return {"success": True, "diff": ""}


@router.get("/projects/{project_id}/local-files", response_model=list)
async def list_local_files(project_id: str):
    try:
        db = Database()
        project_row = db.fetchone("SELECT name FROM projects WHERE id = ?", (project_id,))
        if not project_row:
            return []

        import re
        safe_project_name = re.sub(r'[^\w\s-]', '', project_row["name"]).strip() or f"project_{project_id[:8]}"
        save_dir = Path(os.path.expanduser("~/Documents/Ssuma")) / safe_project_name

        if not save_dir.exists():
            return []

        files = []
        for file_path in save_dir.glob("*.md"):
            stat = file_path.stat()
            files.append({
                "filename": file_path.name,
                "path": str(file_path),
                "size": stat.st_size,
                "modified_at": stat.st_mtime
            })

        files.sort(key=lambda x: x["modified_at"], reverse=True)
        return files
    except Exception as e:
        logger.error(f"获取本地文件列表失败: {str(e)}")
        return []


@router.get("/projects/{project_id}/local-files/{filename}", response_model=dict)
async def get_local_file_content(project_id: str, filename: str):
    try:
        db = Database()
        project_row = db.fetchone("SELECT name FROM projects WHERE id = ?", (project_id,))
        if not project_row:
            raise SsumaError(ErrorCode.PROJECT_NOT_FOUND, "Project not found")

        import re
        safe_project_name = re.sub(r'[^\w\s-]', '', project_row["name"]).strip() or f"project_{project_id[:8]}"
        file_path = Path(os.path.expanduser("~/Documents/Ssuma")) / safe_project_name / filename

        if not file_path.exists() or not file_path.is_file():
            raise SsumaError(ErrorCode.PROJECT_NOT_FOUND, "File not found")

        content = file_path.read_text(encoding="utf-8")
        return {"filename": filename, "content": content}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取本地文件失败: {str(e)}")
        raise SsumaError(ErrorCode.INTERNAL_ERROR, f"Failed to read file: {str(e)}")


@router.post("/templates/{template_id}/create-project", response_model=dict)
async def create_project_from_template(template_id: str):
    db = Database()
    project_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO projects (id, name, description) VALUES (?, ?, ?)",
        (project_id, f"Template Project {template_id}", "")
    )
    return {"project_id": project_id}
