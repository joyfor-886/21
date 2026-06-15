"""上下文文件生成器 —— 为 AI IDE 生成高质量的项目上下文文件。

生成的文件：
- context.md: 项目完整上下文（AI IDE 的「圣经」）
- spec.md: 需求规范（用户故事 + 验收标准）
- tech_stack.md: 技术栈详情（含安装和运行命令）
- data_model.md: 数据模型定义
"""

from typing import Dict, Any, List, Optional


class ContextGenerator:
    """为 AI IDE 生成结构化上下文文件"""

    @classmethod
    def generate(cls, spec: Dict[str, Any]) -> Dict[str, str]:
        """从项目 spec 生成所有上下文文件"""
        return {
            "context.md": cls._generate_context_md(spec),
            "spec.md": cls._generate_spec_md(spec),
            "tech_stack.md": cls._generate_tech_stack_md(spec),
            "data_model.md": cls._generate_data_model_md(spec),
        }

    @classmethod
    def _generate_context_md(cls, spec: Dict[str, Any]) -> str:
        """生成最核心的项目上下文文档"""
        name = spec.get("name", "Untitled Project")
        description = spec.get("description", "")
        stack = spec.get("tech_stack", "Not specified")

        sections = [
            f"# {name} — Project Context",
            "",
            "> **INSTRUCTION FOR AI IDE**: Read this entire file before starting any work. "
            "This is your project bible. It contains everything you need to know to work on this project.",
            "",
            "## Quick Facts",
            f"- **Name**: {name}",
            f"- **Stack**: {stack}",
            f"- **Description**: {description}",
            "",
            "## What We're Building",
            cls._get_value(spec, "product_spec", description),
            "",
            "## Why We're Building It",
            cls._get_value(spec, "why", "See the product spec for motivation."),
            "",
            "## Core Features (MVP)",
            cls._format_features(spec.get("features", [])),
            "",
            "## What We're NOT Building (Yet)",
            cls._format_list(spec.get("out_of_scope", [])),
            "",
            "## Architecture Overview",
            cls._get_value(spec, "architecture_summary", "See docs/tech-stack.md for architecture details."),
            "",
            "## Project Structure",
            cls._get_value(
                spec,
                "directory_structure",
                "```\nsrc/\n├── app/        # Pages & routes\n├── components/ # Reusable UI\n├── lib/        # Utilities & API\n└── styles/     # Global styles\n```"
            ),
            "",
            "## Key Decisions",
            cls._format_decisions(spec.get("decisions", [])),
            "",
            "## Development Rules",
            "1. **Read docs first**: spec.md, tech-stack.md, data-model.md",
            "2. **TDD**: Write failing test → implement → pass → commit",
            "3. **Type safety**: Use strict TypeScript; avoid `any`",
            "4. **No hallucination**: Don't invent APIs or schemas",
            "5. **Small commits**: Each commit = one logical change",
            "6. **Handle all states**: Loading, empty, error, edge cases",
            "",
            "## Getting Started",
            "```bash",
            cls._get_value(spec, "dev_command", "npm install && npm run dev"),
            "```",
            "",
            "## Testing",
            "```bash",
            cls._get_value(spec, "test_command", "npm test"),
            "```",
            "",
            "## References",
            "- Product Spec: `docs/spec.md`",
            "- Tech Stack: `docs/tech-stack.md`",
            "- Data Model: `docs/data-model.md`",
            "- Tasks: `docs/tasks.json`",
        ]

        return "\n".join(sections)

    @classmethod
    def _generate_spec_md(cls, spec: Dict[str, Any]) -> str:
        """生成需求规范"""
        name = spec.get("name", "Untitled")
        description = spec.get("description", "")
        features = spec.get("features", [])

        # 如果有完整的产品 spec，直接使用
        product_spec = spec.get("product_spec", "")
        if product_spec and len(product_spec) > 200:
            return product_spec

        sections = [
            f"# Product Specification: {name}",
            "",
            "## Problem Statement",
            description or "No description provided.",
            "",
            "## Target Users",
            cls._get_value(spec, "target_users", "*To be defined.*"),
            "",
            "## User Stories",
            cls._format_user_stories(features),
            "",
            "## Acceptance Criteria",
            "- All core features are functional and tested",
            "- UI is responsive (mobile + desktop)",
            "- Data is validated on both client and server",
            "- Error states are handled gracefully",
            "- Loading states are shown for async operations",
            "- Empty states have helpful guidance",
            "",
            "## Out of Scope (MVP)",
            cls._format_list(spec.get("out_of_scope", ["*Not yet defined*"])),
            "",
            "## Success Metrics",
            cls._format_list(spec.get("success_metrics", ["*Not yet defined*"])),
        ]

        return "\n".join(sections)

    @classmethod
    def _generate_tech_stack_md(cls, spec: Dict[str, Any]) -> str:
        """生成技术栈文档"""
        tech_spec = spec.get("tech_spec", "")

        # 如果有完整的技术 spec，直接使用
        if tech_spec and len(tech_spec) > 200:
            return tech_spec

        stack = spec.get("tech_stack", "Not specified")
        stack_details = spec.get("stack_details", {})

        sections = [
            f"# Technology Stack",
            "",
            f"**Primary Stack**: {stack}",
            "",
            "## Layers",
        ]

        if stack_details and isinstance(stack_details, dict):
            layers = stack_details.get("layers", stack_details)
            for layer, tech in layers.items():
                sections.append(f"- **{layer}**: {tech}")
        else:
            sections.extend([
                "- **Frontend**: React / Next.js",
                "- **Language**: TypeScript",
                "- **Styling**: TailwindCSS",
                "- **Backend**: Next.js API Routes / FastAPI",
                "- **Database**: PostgreSQL (Supabase) / SQLite",
                "- **Auth**: Supabase Auth / NextAuth.js",
            ])

        sections.extend([
            "",
            "## Development Commands",
            "```bash",
            "# Install dependencies",
            "npm install",
            "",
            "# Start dev server",
            "npm run dev",
            "",
            "# Run tests",
            "npm test",
            "",
            "# Run E2E tests",
            "npm run test:e2e",
            "",
            "# Build for production",
            "npm run build",
            "",
            "# Lint",
            "npm run lint",
            "```",
            "",
            "## Environment Variables",
            "Copy `.env.example` to `.env.local` and fill in:",
            "```bash",
            "# App",
            "NEXT_PUBLIC_APP_URL=http://localhost:3000",
            "",
            "# Database",
            "DATABASE_URL=...",
            "",
            "# Auth",
            "AUTH_SECRET=...",
            "```",
        ])

        return "\n".join(sections)

    @classmethod
    def _generate_data_model_md(cls, spec: Dict[str, Any]) -> str:
        """生成数据模型文档"""
        data_model = spec.get("data_model", {})

        if not data_model:
            return f"""# Data Model

*Data model not yet defined. Define core entities based on the product spec.*

## Design Conventions
1. Use **UUID** as primary key for all entities
2. Add `created_at` and `updated_at` timestamps to every table
3. Use **snake_case** for database columns, **camelCase** in application code
4. Foreign keys must be indexed
5. Sensitive data must be encrypted or hashed

## Example Schema

```sql
-- users
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```
"""

        lines = ["# Data Model", ""]

        if isinstance(data_model, dict):
            for table_name, columns in data_model.items():
                lines.append(f"## {table_name}")
                if isinstance(columns, list):
                    lines.append("| Column | Type | Constraints | Description |")
                    lines.append("|--------|------|-------------|-------------|")
                    for col in columns:
                        if isinstance(col, str):
                            lines.append(f"| {col} | TEXT | NOT NULL | |")
                        elif isinstance(col, dict):
                            lines.append(
                                f"| {col.get('name', '?')} | "
                                f"{col.get('type', 'TEXT')} | "
                                f"{col.get('constraints', '')} | "
                                f"{col.get('description', '')} |"
                            )
                elif isinstance(columns, str):
                    lines.append(columns)
                lines.append("")

        return "\n".join(lines)

    # ===== 格式化辅助方法 =====

    @classmethod
    def _get_value(cls, spec: Dict[str, Any], key: str, default: str) -> str:
        val = spec.get(key, "")
        return val if val else default

    @classmethod
    def _format_features(cls, features: List[Any]) -> str:
        if not features:
            return "- *No features specified yet.*"

        lines = []
        for i, f in enumerate(features, 1):
            if isinstance(f, dict):
                name = f.get("name", f"Feature {i}")
                priority = f.get("priority", "")
                desc = f.get("description", "")
                priority_str = f" (P{priority})" if priority else ""
                lines.append(f"{i}. **{name}**{priority_str}: {desc}")
            else:
                lines.append(f"{i}. {f}")
        return "\n".join(lines)

    @classmethod
    def _format_list(cls, items: List[Any]) -> str:
        if not items:
            return "- *None specified*"
        return "\n".join(f"- {item}" for item in items)

    @classmethod
    def _format_decisions(cls, decisions: List[Any]) -> str:
        if not decisions:
            return "- *No key decisions recorded yet.*"
        return "\n".join(f"- {d}" for d in decisions)

    @classmethod
    def _format_user_stories(cls, features: List[Any]) -> str:
        if not features:
            return "*No user stories defined yet.*"

        stories = []
        for i, f in enumerate(features, 1):
            if isinstance(f, dict):
                name = f.get("name", f"Feature {i}")
                desc = f.get("description", "")
                stories.append(
                    f"### Story {i}: {name}\n"
                    f"**As a** user\n"
                    f"**I want to** {desc or name}\n"
                    f"**So that** I can achieve my goal efficiently."
                )
            else:
                stories.append(
                    f"### Story {i}\n"
                    f"**As a** user\n"
                    f"**I want to** {f}\n"
                    f"**So that** I can achieve my goal."
                )
        return "\n".join(stories)

    @classmethod
    def _format_columns(cls, columns: List[Any]) -> str:
        rows = []
        for col in columns:
            if isinstance(col, str):
                col_type = "TEXT"
                if col == "id": col_type = "UUID PRIMARY KEY"
                elif "email" in col: col_type = "VARCHAR(255) UNIQUE"
                elif any(t in col for t in ["date", "time", "at"]): col_type = "TIMESTAMPTZ"
                rows.append(f"| {col} | {col_type} | NOT NULL | |")
            elif isinstance(col, dict):
                rows.append(
                    f"| {col.get('name', '?')} | "
                    f"{col.get('type', 'TEXT')} | "
                    f"{col.get('constraints', 'NOT NULL')} | "
                    f"{col.get('description', '')} |"
                )
        return "\n".join(rows) if rows else "| *No columns defined* |"
