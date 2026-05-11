import uuid
import logging
from typing import Optional, Tuple
from db.sqlite import Database

logger = logging.getLogger('Ssuma.ProjectService')


class ProjectService:

    @staticmethod
    def ensure_project(project_id: Optional[str], message: str, db: Database) -> str:
        if not project_id:
            project_id = str(uuid.uuid4())
            clean_msg = message.strip()
            if clean_msg:
                project_name = clean_msg[:20] + ("..." if len(clean_msg) > 20 else "")
            else:
                project_name = "新项目"
            project_name = project_name.replace('\n', ' ').replace('\r', '')
            with db.transaction():
                db.execute(
                    "INSERT INTO projects (id, name, description) VALUES (?, ?, ?)",
                    (project_id, project_name, "")
                )
        return project_id

    @staticmethod
    def save_message(
        project_id: str,
        role: str,
        content: str,
        skill_used: str = None,
        db: Database = None,
    ) -> str:
        message_id = str(uuid.uuid4())
        if db is None:
            db = Database()
        with db.transaction():
            db.execute(
                "INSERT INTO messages (id, project_id, role, content, skill_used) VALUES (?, ?, ?, ?, ?)",
                (message_id, project_id, role, content, skill_used)
            )
        return message_id
