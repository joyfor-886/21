"""AI IDE 导出器 —— 将生成的项目方案转化为各种 AI IDE 可以理解的项目文件。

支持的 IDE / Agent：
- Cursor (.cursorrules)
- Claude Code (CLAUDE.md)
- GitHub Copilot (.github/copilot-instructions.md)
- Windsurf (.windsurfrules)
- 通用 (AGENTS.md)
- 结构化任务 (tasks.json)
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging

logger = logging.getLogger('Ssuma.IDEExporter')


@dataclass
class ExportedProject:
    """导出项目的完整文件集合"""
    project_name: str
    files: Dict[str, str] = field(default_factory=dict)  # path -> content

    def add_file(self, path: str, content: str):
        self.files[path] = content


class IDEExporter:
    """将 Ssuma 方案导出为 AI IDE 可用的项目文件"""

    # ===== 公共入口 =====

    @classmethod
    def export(cls, spec: Dict[str, Any]) -> ExportedProject:
        """从方案字典生成完整的 IDE 项目文件

        spec 应包含:
            - name: 项目名称
            - description: 项目描述
            - tech_stack: 技术栈描述
            - product_spec: 产品定义
            - tech_spec: 技术架构
            - exec_spec: 执行计划
            - features: 核心功能列表
            - data_model: 数据模型
        """
        project_name = spec.get("name", "my-project").lower().replace(" ", "-")
        project = ExportedProject(project_name=project_name)

        # 1. 通用 AI Agent 上下文（最重要，所有 IDE 都能读）
        project.add_file("AGENTS.md", cls._generate_agents_md(spec))

        # 2. Cursor IDE 规则
        project.add_file(".cursorrules", cls._generate_cursor_rules(spec))

        # 3. Claude Code 规则
        project.add_file("CLAUDE.md", cls._generate_claude_md(spec))

        # 4. GitHub Copilot 指令
        project.add_file(".github/copilot-instructions.md", cls._generate_copilot_instructions(spec))

        # 5. Windsurf 规则
        project.add_file(".windsurfrules", cls._generate_windsurf_rules(spec))

        # 6. 项目规范文档
        project.add_file("docs/spec.md", cls._generate_spec_md(spec))
        project.add_file("docs/context.md", cls._generate_context_md(spec))
        project.add_file("docs/tech-stack.md", cls._generate_tech_stack_md(spec))
        project.add_file("docs/data-model.md", cls._generate_data_model_md(spec))

        # 7. 结构化任务清单（可被 AI IDE 解析）
        project.add_file("docs/tasks.json", cls._generate_tasks_json(spec))

        # 8. .env.example
        project.add_file(".env.example", cls._generate_env_example(spec))

        # 9. .gitignore（基础版）
        project.add_file(".gitignore", cls._generate_gitignore(spec))

        logger.info(f"Exported {len(project.files)} files for project '{project_name}'")
        return project

    # ===== 各 IDE 特定文件生成 =====

    @classmethod
    def _generate_agents_md(cls, spec: Dict[str, Any]) -> str:
        """AGENTS.md —— 最通用的 AI 代理上下文文件"""
        name = spec.get("name", "Untitled")
        description = spec.get("description", "")
        tech_stack = spec.get("tech_stack", "待定")

        lines = [
            f"# {name} — AI Agent 项目上下文",
            "",
            "> **指令**：在开始任何编码工作前，请完整阅读此文件。这是项目的「圣经」。",
            "",
            "## 项目概述",
            f"- **名称**：{name}",
            f"- **一句话描述**：{description}",
            "",
            "## 技术栈",
            f"{tech_stack}",
            "",
            "## 项目结构约定",
            "- 所有新代码使用 TypeScript（或项目指定的主要语言）",
            "- 组件文件使用 PascalCase",
            "- 工具函数使用 camelCase",
            "- 每个模块应有对应的测试文件（`*.test.ts` 或 `*.spec.ts`）",
            "",
            "## 开发规则",
            "1. **先读文档**：`docs/spec.md` 是需求规范，`docs/tech-stack.md` 是技术选型",
            "2. **先写测试**：遵循 TDD 红-绿-重构循环",
            "3. **小步提交**：每个 Task 完成后独立 commit",
            "4. **类型优先**：使用严格类型，避免 `any`",
            "5. **不臆造 API**：只使用项目中已定义或文档中已规划的 API",
            "6. **保持一致**：遵循项目已有的代码风格和目录结构",
            "",
            "## 禁止事项",
            "- ❌ 不要创建未被请求的新功能",
            "- ❌ 不要修改核心配置文件（package.json, tsconfig 等）除非 Task 明确要求",
            "- ❌ 不要在代码中留下 TODO 或占位符",
            "- ❌ 不要臆造数据库 schema 或 API —— 对照 `docs/data-model.md`",
            "",
            "## 执行流程",
            "1. 阅读 `docs/tasks.json` 找到当前任务",
            "2. 按 Task 的「步骤」字段逐条执行",
            "3. 每个 Task 完成并测试通过后，再开始下一个",
            "4. 遇到问题先查阅 `docs/spec.md` 和 `docs/context.md`",
            "",
            "## 关键文档索引",
            "- 需求规范：`docs/spec.md`",
            "- 技术栈：`docs/tech-stack.md`",
            "- 数据模型：`docs/data-model.md`",
            "- 任务列表：`docs/tasks.json`",
            "- 项目上下文：`docs/context.md`",
        ]

        # 如果有产品 spec 详细信息，补充进来
        if spec.get("product_spec"):
            lines.extend([
                "",
                "## 产品需求摘要",
                spec["product_spec"][:3000],
            ])

        return "\n".join(lines)

    @classmethod
    def _generate_cursor_rules(cls, spec: Dict[str, Any]) -> str:
        """Cursor IDE 专用规则文件"""
        name = spec.get("name", "Untitled")
        tech_stack = spec.get("tech_stack", "")

        return f"""# Cursor Rules for {name}

## 项目背景
{spec.get("description", "参考 AGENTS.md 获取完整上下文")}

## 技术栈
{tech_stack}

## 编码规则
1. 在开始任何代码修改前，先完整阅读 `AGENTS.md`
2. 所有新文件必须使用 TypeScript 并添加严格类型注解
3. UI 组件默认使用 TailwindCSS
4. 遵循项目中已有的代码风格和目录结构
5. 每个函数/组件必须有明确的输入输出类型

## Cursor 特定行为
- 使用 `@docs` 引用文档目录获取项目上下文
- 使用 `@spec` 查看需求规范
- 每次修改后运行相关测试确保没有退化

## 项目和包管理
- 使用项目指定的包管理器（npm/yarn/pnpm）
- 不要在没有明确 Task 要求的情况下添加新依赖

## 测试规则
- 单元测试框架：Vitest（前端）/ Pytest（后端）
- 测试文件位置：与源文件同目录或在 `tests/` 目录下
- 运行测试：请参考 `docs/tech-stack.md` 中的测试命令
"""

    @classmethod
    def _generate_claude_md(cls, spec: Dict[str, Any]) -> str:
        """Claude Code 专用 CLAUDE.md 文件"""
        name = spec.get("name", "Untitled")
        features = spec.get("features", [])

        features_text = "\n".join(f"- {f}" for f in features) if features else "- 参见 docs/spec.md"

        return f"""# CLAUDE.md

## 项目概述
**{name}**: {spec.get("description", "")}

## 核心功能
{features_text}

## 常用命令
- 开发启动: {spec.get("dev_command", "npm run dev")}
- 运行测试: {spec.get("test_command", "npm test")}
- 构建: {spec.get("build_command", "npm run build")}
- Lint: {spec.get("lint_command", "npm run lint")}

## 项目架构
{spec.get("architecture_summary", "参见 docs/context.md 了解完整的项目架构")}

## 开发指南
- 在开始编码前，先读取 `docs/context.md` 了解完整上下文
- 遵循 `docs/spec.md` 中的需求规范
- 数据模型定义在 `docs/data-model.md`
- 保持代码简洁，不引入不必要的抽象
- 提交信息使用 conventional commits 格式
"""

    @classmethod
    def _generate_copilot_instructions(cls, spec: Dict[str, Any]) -> str:
        """GitHub Copilot 指令文件"""
        return f"""# Copilot Instructions

## Project: {spec.get("name", "Untitled")}

## Context
{spec.get("description", "See AGENTS.md for full context.")}

## Instructions
- Always use TypeScript with strict typing
- Follow the project's existing code style
- Use TailwindCSS for styling
- Write tests for all new functionality
- Do not invent APIs or database schemas — refer to docs/data-model.md
- Keep changes minimal and focused
- Each commit should represent a single logical change

## References
- Spec: docs/spec.md
- Tech Stack: docs/tech-stack.md
- Data Model: docs/data-model.md
- Context: docs/context.md
"""

    @classmethod
    def _generate_windsurf_rules(cls, spec: Dict[str, Any]) -> str:
        """Windsurf IDE 规则文件"""
        return f"""# Windsurf Rules

## {spec.get("name", "Untitled")}

### Global Context
{spec.get("description", "")}

### Key Rules
1. Always read AGENTS.md first
2. Follow TypeScript strict mode
3. Use TailwindCSS for all styling
4. Test-driven development: write tests before implementation
5. Do not modify config files without explicit instruction

### Documentation
- Product spec: docs/spec.md
- Architecture: docs/context.md
- Data models: docs/data-model.md
- Tasks: docs/tasks.json
"""

    # ===== 项目文档生成 =====

    @classmethod
    def _generate_spec_md(cls, spec: Dict[str, Any]) -> str:
        """生成项目需求规范"""
        product_spec = spec.get("product_spec", "")
        if product_spec:
            return product_spec

        features = spec.get("features", [])
        stories = []
        for i, f in enumerate(features, 1):
            stories.append(f"### Story {i}\n**As a** user\n**I want to** {f}\n**So that** I can achieve my goal")

        return f"""# Product Specification: {spec.get("name", "Untitled")}

## Problem Statement
{spec.get("description", "No description provided.")}

## User Stories
{chr(10).join(stories) if stories else "*No features specified*"}

## Acceptance Criteria
- All core features functional
- Responsive design for mobile and desktop
- Data validation on client and server side
- Error handling for all API calls
- Loading states for async operations
"""

    @classmethod
    def _generate_context_md(cls, spec: Dict[str, Any]) -> str:
        """生成项目上下文文档"""
        name = spec.get("name", "Untitled")
        tech_stack = spec.get("tech_stack", "")

        parts = [
            f"# {name} - Project Context",
            "",
            "> **AI IDE 指令**：在开始任何工作前先读此文件。它包含项目所有的背景知识。",
            "",
            "## 项目是什么",
            spec.get("description", ""),
            "",
            "## 为什么要做",
            spec.get("why", "见 AGENTS.md 中的产品需求摘要"),
            "",
            "## 技术栈",
            tech_stack or "见 docs/tech-stack.md",
            "",
            "## 项目结构",
            "```",
            spec.get("directory_structure", "见 AGENTS.md"),
            "```",
            "",
            "## 关键决策",
        ]

        decisions = spec.get("decisions", [])
        if decisions:
            for d in decisions:
                parts.append(f"- {d}")
        else:
            parts.append("- 暂无记录的关键决策")

        parts.extend([
            "",
            "## 约束条件",
            "- MVP 阶段不做（参考产品共识中的「非目标」）",
            "- 所有 API 调用需要错误处理",
            "- 所有组件需要 loading 和 empty 状态",
            "",
            "## 已知问题 / 技术负债",
            "- 暂无（项目刚启动）",
            "",
            "## 外部依赖",
            "- 参考 docs/tech-stack.md 中的技术栈推荐",
        ])

        return "\n".join(parts)

    @classmethod
    def _generate_tech_stack_md(cls, spec: Dict[str, Any]) -> str:
        """生成技术栈文档"""
        tech_spec = spec.get("tech_spec", "")

        if tech_spec:
            return tech_spec

        return f"""# Technology Stack for {spec.get("name", "Untitled")}

## 推荐技术栈

| 层级 | 方案 | 版本 |
|------|------|------|
| 前端框架 | Next.js / React | 14+ / 18+ |
| 样式 | TailwindCSS | 3.4+ |
| 语言 | TypeScript | 5+ |
| 后端 | Next.js API Routes 或 FastAPI(Python) | 最新稳定版 |
| 数据库 | Supabase (PostgreSQL) 或 SQLite | 最新 |
| 认证 | Supabase Auth 或 NextAuth.js | 最新 |
| ORM | Prisma 或 Drizzle | 最新 |
| 测试 | Vitest + Testing Library | 最新 |
| 部署 | Vercel / Netlify | - |

## 安装和运行

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 运行测试
npm test

# 构建
npm run build
```

## 关键依赖说明
- **TailwindCSS**: 原子化 CSS，开发效率高
- **TypeScript**: 类型安全，减少运行时错误
- **Supabase**: 开源 Firebase 替代，PostgreSQL + Auth + Storage
"""

    @classmethod
    def _generate_data_model_md(cls, spec: Dict[str, Any]) -> str:
        """生成数据模型文档"""
        data_model = spec.get("data_model", {})

        if not data_model:
            return f"""# Data Model for {spec.get("name", "Untitled")}

*数据模型尚未定义。请基于需求规范定义核心数据结构。*

## 设计原则
1. 每个实体独立成表
2. 使用 UUID 作为主键
3. 添加 `created_at` 和 `updated_at` 时间戳
4. 外键关联使用索引
5. 敏感字段加密或脱敏存储
"""

        lines = [f"# Data Model for {spec.get('name', 'Untitled')}", ""]
        for table_name, columns in data_model.items():
            lines.append(f"## {table_name}")
            lines.append("| Column | Type | Constraints | Description |")
            lines.append("|--------|------|-------------|-------------|")
            for col in columns:
                if isinstance(col, str):
                    lines.append(f"| {col} | TEXT | NOT NULL | |")
                elif isinstance(col, dict):
                    lines.append(f"| {col.get('name', '?')} | {col.get('type', 'TEXT')} | {col.get('constraints', '')} | {col.get('description', '')} |")
            lines.append("")
        return "\n".join(lines)

    # ===== 结构化任务 JSON =====

    @classmethod
    def _generate_tasks_json(cls, spec: Dict[str, Any]) -> str:
        """生成 AI IDE 可解析的结构化任务清单"""
        name = spec.get("name", "Untitled")
        timestamp = datetime.now().isoformat()

        # 尝试从 exec_spec 中提取任务
        tasks = cls._extract_tasks_from_spec(spec)

        task_list = {
            "project": name,
            "generated_at": timestamp,
            "generated_by": "Ssuma IDE Exporter",
            "total_tasks": len(tasks),
            "format_version": "1.0",
            "tasks": tasks,
        }

        return json.dumps(task_list, ensure_ascii=False, indent=2)

    @classmethod
    def _extract_tasks_from_spec(cls, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从 spec 中提取任务列表"""
        exec_spec = spec.get("exec_spec", "")

        # 简单启发式：查找以 "Task" 或 "### Task" 开头的行
        tasks = []
        if exec_spec:
            lines = exec_spec.split("\n")
            current_task = None
            current_files = []

            for line in lines:
                # 匹配 "### Task N: ..." 或 "Task N: ..."
                if line.strip().startswith("### Task") or (
                    line.strip().startswith("Task ") and ":" in line
                ):
                    if current_task:
                        current_task["files"] = current_files
                        tasks.append(current_task)
                    current_task = {
                        "title": line.strip().lstrip("#").strip(),
                        "complexity": "medium",
                        "estimated_minutes": 5,
                        "dependencies": [],
                        "files": [],
                        "steps": [],
                        "acceptance": "",
                    }
                    current_files = []
                elif current_task:
                    if "复杂度" in line or "complexity" in line.lower():
                        if "简单" in line or "simple" in line.lower():
                            current_task["complexity"] = "simple"
                        elif "复杂" in line or "complex" in line.lower():
                            current_task["complexity"] = "complex"
                    elif "预估" in line or "分钟" in line:
                        import re
                        nums = re.findall(r'\d+', line)
                        if nums:
                            current_task["estimated_minutes"] = int(nums[0])
                    elif "依赖" in line or "dependency" in line.lower():
                        if "无" not in line and "none" not in line.lower():
                            deps = [d.strip() for d in line.split(":")[-1].split(",")]
                            current_task["dependencies"] = deps
                    elif line.strip().startswith("- [NEW]") or line.strip().startswith("- [MODIFY]"):
                        current_files.append(line.strip())
                    elif line.strip().startswith("- [ ]"):
                        current_task["steps"].append(line.strip())
                    elif "验收" in line or "acceptance" in line.lower():
                        current_task["acceptance"] = line.split(":", 1)[-1].strip() if ":" in line else line.strip()

            if current_task:
                current_task["files"] = current_files
                tasks.append(current_task)

        # 如果没有提取到任务，创建一个默认骨架
        if not tasks:
            tasks = [
                {
                    "title": "Phase 1: 项目初始化",
                    "complexity": "simple",
                    "estimated_minutes": 15,
                    "dependencies": [],
                    "files": ["package.json", "tsconfig.json", "tailwind.config.ts"],
                    "steps": [
                        "- [ ] 1. 使用 create-next-app 或 vite 初始化项目",
                        "- [ ] 2. 安装并配置 TailwindCSS",
                        "- [ ] 3. 配置 TypeScript 严格模式",
                        "- [ ] 4. 创建基础目录结构",
                        "- [ ] 5. 运行 `npm run dev` 确认项目启动",
                    ],
                    "acceptance": "项目能在本地成功启动，看到默认页面",
                },
                {
                    "title": "Phase 2: 数据模型",
                    "complexity": "moderate",
                    "estimated_minutes": 30,
                    "dependencies": ["Phase 1"],
                    "files": ["src/lib/db.ts", "prisma/schema.prisma"],
                    "steps": [
                        "- [ ] 1. 定义数据库 schema",
                        "- [ ] 2. 运行数据库迁移",
                        "- [ ] 3. 编写 seed 脚本",
                        "- [ ] 4. 测试数据库连接和基本 CRUD",
                    ],
                    "acceptance": "数据库 schema 已定义并可通过测试验证",
                },
            ]

        return tasks

    # ===== 辅助文件 =====

    @classmethod
    def _generate_env_example(cls, spec: Dict[str, Any]) -> str:
        """生成环境变量模板"""
        tech_stack = spec.get("tech_stack", "").lower()
        lines = ["# Environment Variables", ""]

        if any(kw in tech_stack for kw in ["supabase", "postgres", "database"]):
            lines.extend([
                "# Database",
                "DATABASE_URL=postgresql://user:password@localhost:5432/dbname",
                "",
            ])

        if any(kw in tech_stack for kw in ["auth", "nextauth", "clerk"]):
            lines.extend([
                "# Authentication",
                "AUTH_SECRET=your-secret-key",
                "AUTH_URL=http://localhost:3000",
                "",
            ])

        if any(kw in tech_stack for kw in ["openai", "ai", "llm", "claude"]):
            lines.extend([
                "# AI / LLM",
                "OPENAI_API_KEY=sk-...",
                "",
            ])

        if any(kw in tech_stack for kw in ["stripe", "payment"]):
            lines.extend([
                "# Payments",
                "STRIPE_SECRET_KEY=sk_test_...",
                "STRIPE_WEBHOOK_SECRET=whsec_...",
                "",
            ])

        lines.extend([
            "# App",
            "NEXT_PUBLIC_APP_URL=http://localhost:3000",
            "NODE_ENV=development",
        ])

        return "\n".join(lines)

    @classmethod
    def _generate_gitignore(cls, spec: Dict[str, Any]) -> str:
        """生成 .gitignore"""
        return """# Dependencies
node_modules/
.pnp
.pnp.js

# Build
.next/
out/
dist/
build/

# Environment
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Debug
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Testing
coverage/

# Misc
*.pem
"""


def export_project(spec: Dict[str, Any]) -> ExportedProject:
    """便捷函数"""
    return IDEExporter.export(spec)
