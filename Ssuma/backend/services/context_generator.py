from typing import Dict, Any

class ContextGenerator:
    """Generates structured Markdown context files for AI IDEs."""
    
    @classmethod
    def generate(cls, spec: Dict[str, Any]) -> Dict[str, str]:
        """Generate context files from project spec."""
        return {
            "context.md": cls._generate_context_md(spec),
            "spec.md": cls._generate_spec_md(spec),
            "tech_stack.md": cls._generate_tech_stack_md(spec),
            "data_model.md": cls._generate_data_model_md(spec)
        }

    @classmethod
    def _generate_context_md(cls, spec: Dict[str, Any]) -> str:
        return f"""# {spec.get('name', 'Untitled Project')} - AI IDE Context

> **INSTRUCTION FOR AI IDE:** Read this entire file before starting any work. This is your project bible.

## Project Overview
- **Name:** {spec.get('name', 'Untitled')}
- **Description:** {spec.get('description', '')}

## Core Features
{cls._format_list(spec.get('features', []))}

## Technology Stack
{spec.get('tech_stack', 'Not specified')}

## Data Model Summary
{cls._format_dict(spec.get('data_model', {}))}

## Implementation Rules
1. Always read `spec.md` for detailed requirements before coding.
2. Follow the tech stack defined in `tech_stack.md`.
3. Use the data model defined in `data_model.md`.
4. Write clean, commented, and testable code.
"""

    @classmethod
    def _generate_spec_md(cls, spec: Dict[str, Any]) -> str:
        return f"""# Product Specification: {spec.get('name', 'Untitled')}

## 1. Problem Statement
{spec.get('description', 'No description provided.')}

## 2. User Stories
{cls._format_user_stories(spec.get('features', []))}

## 3. Acceptance Criteria
- All core features must be functional.
- UI must be responsive and accessible.
- Data must be validated on both client and server side.
"""

    @classmethod
    def _generate_tech_stack_md(cls, spec: Dict[str, Any]) -> str:
        return f"""# Technology Stack

**Primary Stack:** {spec.get('tech_stack', 'Not specified')}

## Recommended Packages
- **Frontend:** Next.js, React, TailwindCSS
- **Backend:** FastAPI (Python) or Next.js API Routes
- **Database:** Supabase (PostgreSQL)
- **Auth:** Supabase Auth
"""

    @classmethod
    def _generate_data_model_md(cls, spec: Dict[str, Any]) -> str:
        models = spec.get('data_model', {})
        if not models:
            return "# Data Model\n\n*To be defined based on project requirements.*\n"
            
        tables = []
        for table, columns in models.items():
            cols = " | ".join(columns)
            tables.append(f"### {table}\n| Column | Type |\n|--------|------|\n{cls._format_columns(columns)}")
            
        return f"""# Data Model\n\n{chr(10).join(tables)}\n"""

    @classmethod
    def _format_list(cls, items: list) -> str:
        return "\n".join([f"- {item}" for item in items]) if items else "- None specified"

    @classmethod
    def _format_dict(cls, data: dict) -> str:
        return "\n".join([f"- **{k}**: {v}" for k, v in data.items()]) if data else "- Not specified"

    @classmethod
    def _format_user_stories(cls, features: list) -> str:
        stories = []
        for i, feature in enumerate(features, 1):
            stories.append(f"### Story {i}: {feature}\n**As a** user\n**I want to** {feature.lower()}\n**So that** I can achieve my goal efficiently.")
        return "\n".join(stories) if stories else "*No features specified.*"

    @classmethod
    def _format_columns(cls, columns: list) -> str:
        rows = []
        for col in columns:
            col_type = "TEXT"
            if col == "id": col_type = "UUID PRIMARY KEY"
            elif "email" in col: col_type = "VARCHAR(255) UNIQUE"
            elif "date" in col or "time" in col: col_type = "TIMESTAMP"
            rows.append(f"| {col} | {col_type} |")
        return "\n".join(rows)
