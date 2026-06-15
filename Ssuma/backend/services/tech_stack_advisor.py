"""技术栈顾问 —— 基于项目需求智能推荐技术栈

支持的维度：
- 项目类型（Web 全栈 / 前端 SPA / 后端 API / CLI 工具 / 移动端 / 浏览器扩展）
- 复杂度（简单 / 中等 / 复杂 / 平台级）
- 用户偏好（语言、框架、部署平台）
- 团队规模（个人 / 小团队 / 大团队）

每种推荐包含：
- 首选方案 + 备选方案
- 版本要求
- 选择理由
- 适用场景和限制
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import re
import logging

logger = logging.getLogger('Ssuma.TechStackAdvisor')


@dataclass
class TechStackRecommendation:
    """单个技术栈推荐"""
    name: str
    tier: str  # "recommended" | "alternative" | "not_recommended"
    description: str
    layers: Dict[str, str] = field(default_factory=dict)  # layer_name -> technology
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    best_for: str = ""
    not_for: str = ""


class TechStackAdvisor:
    """智能技术栈推荐引擎"""

    # ===== 预定义技术栈模板 =====

    STACKS = {
        "nextjs_fullstack": {
            "name": "Next.js 全栈",
            "description": "React 全栈框架，支持 SSR/SSG/ISR，API Routes 作为后端",
            "layers": {
                "前端框架": "Next.js 14+ (App Router)",
                "语言": "TypeScript 5+",
                "样式": "TailwindCSS 3.4+",
                "UI 组件": "shadcn/ui (Radix UI)",
                "后端": "Next.js API Routes / Server Actions",
                "数据库": "Supabase (PostgreSQL) 或 Prisma + PostgreSQL",
                "认证": "Supabase Auth 或 NextAuth.js v5",
                "ORM": "Prisma 或 Drizzle ORM",
                "状态管理": "React Context + TanStack Query",
                "表单": "React Hook Form + Zod",
                "测试": "Vitest + Testing Library + Playwright (E2E)",
                "部署": "Vercel / Netlify",
            },
            "pros": [
                "前后端统一，一个仓库管理",
                "Server Components 减少客户端 JS 体积",
                "Vercel 生态无缝部署",
                "丰富的模板和社区支持",
            ],
            "cons": [
                "Server Actions 有时不够灵活",
                "对复杂后端业务逻辑支持有限",
                "Vercel 费用随规模增长较快",
            ],
            "best_for": "全栈 SaaS、内容网站、电商、个人博客、MVP 快速验证",
            "not_for": "需要独立后端的大规模系统、实时处理密集型应用",
        },
        "vite_react_spa": {
            "name": "Vite + React SPA",
            "description": "轻量级前端方案，Vite 构建 + React 组件，需要独立后端",
            "layers": {
                "前端框架": "React 18+ + React Router 6+",
                "构建工具": "Vite 5+",
                "语言": "TypeScript 5+",
                "样式": "TailwindCSS 3.4+",
                "UI 组件": "shadcn/ui 或 Ant Design",
                "状态管理": "Zustand + TanStack Query",
                "表单": "React Hook Form + Zod",
                "测试": "Vitest + Testing Library",
                "部署": "Vercel / Netlify / Cloudflare Pages",
            },
            "pros": [
                "构建极快（Vite HMR）",
                "前端独立，后端可自由选择",
                "部署到 CDN，成本低",
            ],
            "cons": [
                "需要单独的后端服务",
                "SEO 需要额外配置",
                "无 SSR，首屏加载依赖客户端",
            ],
            "best_for": "需要独立后端的管理后台、内部工具、B 端产品",
            "not_for": "SEO 敏感的公开网站、需要 SSR 的应用",
        },
        "vue_nuxt": {
            "name": "Vue + Nuxt 全栈",
            "description": "Vue 生态的全栈方案，Nuxt 提供 SSR/SSG 和 Server API",
            "layers": {
                "前端框架": "Nuxt 3+ (Vue 3 Composition API)",
                "语言": "TypeScript 5+",
                "样式": "TailwindCSS 3.4+",
                "UI 组件": "Nuxt UI 或 PrimeVue",
                "后端": "Nitro Server (Nuxt 内置)",
                "数据库": "Supabase 或 Prisma + PostgreSQL",
                "认证": "Nuxt Auth (sidebase/nuxt-auth)",
                "ORM": "Prisma",
                "状态管理": "Pinia",
                "测试": "Vitest + Nuxt Test Utils",
                "部署": "Vercel / Netlify / Cloudflare Pages",
            },
            "pros": [
                "Vue 生态完整，社区活跃",
                "Nuxt 开箱即用，约定优于配置",
                "Nitro Server 性能优异",
                "适合 Vue 技术栈团队",
            ],
            "cons": [
                "React 生态更丰富（组件库、教程）",
                "Nuxt 3 部分模块尚不稳定",
            ],
            "best_for": "Vue 技术栈团队的全栈应用、内容网站、电商",
            "not_for": "需要 React 特定生态的项目",
        },
        "fastapi_backend": {
            "name": "Python FastAPI 后端",
            "description": "高性能 Python 后端，类型安全的 API 开发",
            "layers": {
                "后端框架": "FastAPI 0.110+",
                "语言": "Python 3.11+",
                "数据库": "PostgreSQL + SQLAlchemy 2.0",
                "ORM": "SQLAlchemy 2.0 (async) 或 SQLModel",
                "认证": "JWT + python-jose",
                "缓存": "Redis",
                "任务队列": "Celery + Redis 或 ARQ",
                "测试": "Pytest + httpx",
                "部署": "Docker + Railway / Render / Fly.io",
                "API 文档": "自动生成 OpenAPI/Swagger",
            },
            "pros": [
                "Python 生态丰富（AI/ML/数据分析）",
                "自动生成 OpenAPI 文档",
                "异步支持，性能优异",
                "类型提示提升代码质量",
            ],
            "cons": [
                "Python 性能瓶颈（CPU 密集任务）",
                "GIL 限制并发",
                "包管理混乱（pip/poetry/pipenv）",
            ],
            "best_for": "AI/ML 相关 API、数据分析后端、快速 API 开发",
            "not_for": "高并发实时应用、对延迟极度敏感的系统",
        },
        "express_typescript": {
            "name": "Express + TypeScript 后端",
            "description": "Node.js 后端经典方案，生态最丰富",
            "layers": {
                "后端框架": "Express 4+ 或 Fastify",
                "语言": "TypeScript 5+",
                "数据库": "PostgreSQL + Prisma",
                "认证": "JWT + bcrypt 或 Passport.js",
                "验证": "Zod",
                "缓存": "Redis (ioredis)",
                "测试": "Vitest + Supertest",
                "部署": "Docker + Railway / Render",
            },
            "pros": [
                "npm 生态最大",
                "前后端语言统一（TypeScript）",
                "中间件模式灵活",
                "社区资源最多",
            ],
            "cons": [
                "Express 缺乏内置功能（需自行组合）",
                "回调地狱（虽然 async/await 已缓解）",
                "对大型项目架构约束弱",
            ],
            "best_for": "需要 npm 生态、前后端统一语言的项目",
            "not_for": "需要严格架构约束的大型后端",
        },
        "go_gin": {
            "name": "Go + Gin 后端",
            "description": "高性能 Go 后端，适合高并发场景",
            "layers": {
                "后端框架": "Gin 1.9+ 或 Echo",
                "语言": "Go 1.21+",
                "数据库": "PostgreSQL + sqlc 或 GORM",
                "认证": "JWT (golang-jwt)",
                "缓存": "Redis (go-redis)",
                "测试": "Go testing + testify",
                "部署": "Docker + 单二进制部署",
            },
            "pros": [
                "性能极高，内存占用低",
                "并发模型优秀 (goroutines)",
                "编译为单二进制，部署简单",
                "类型安全，编译时检查",
            ],
            "cons": [
                "错误处理冗长",
                "泛型支持较新，生态尚未完全适配",
                "开发效率不如脚本语言",
            ],
            "best_for": "高性能 API、微服务、CLI 工具、基础设施",
            "not_for": "快速原型开发、AI/ML 集成",
        },
        "cli_python": {
            "name": "Python CLI 工具",
            "description": "适合命令行工具、脚本、自动化",
            "layers": {
                "语言": "Python 3.11+",
                "CLI 框架": "Typer + Rich",
                "打包": "pipx 或 PyInstaller",
                "测试": "Pytest",
                "配置": "Pydantic Settings",
            },
            "pros": ["快速开发", "丰富的数据处理库", "跨平台"],
            "cons": ["启动速度较慢", "需要 Python 运行时"],
            "best_for": "数据处理、自动化脚本、开发者工具",
            "not_for": "需要极快启动速度的 CLI 工具",
        },
        "cli_rust": {
            "name": "Rust CLI 工具",
            "description": "极致性能的 CLI 工具",
            "layers": {
                "语言": "Rust (stable)",
                "CLI 框架": "clap + anyhow + thiserror",
                "异步": "tokio",
                "测试": "Rust built-in test",
                "打包": "cargo build --release (单二进制)",
            },
            "pros": ["极致性能", "单二进制，无依赖", "内存安全"],
            "cons": ["学习曲线陡峭", "编译时间长", "开发速度较慢"],
            "best_for": "性能敏感的 CLI 工具、系统工具、网络工具",
            "not_for": "快速原型、需求频繁变动的项目",
        },
    }

    # ===== 项目类型到推荐栈的映射 =====

    TYPE_TO_STACKS = {
        "web_fullstack": ["nextjs_fullstack", "vue_nuxt"],
        "web_frontend": ["vite_react_spa", "vue_nuxt"],
        "backend_api": ["fastapi_backend", "express_typescript", "go_gin"],
        "cli": ["cli_python", "cli_rust"],
        "mobile": ["react_native", "flutter"],
        "extension": ["vite_react_spa"],
    }

    # ===== 公共 API =====

    @classmethod
    def recommend(
        cls,
        description: str,
        complexity: str = "moderate",
        preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """基于项目描述推荐技术栈

        Args:
            description: 项目需求描述
            complexity: 复杂度 (simple/moderate/complex/platform)
            preferences: 用户偏好 {"language": "python", "platform": "web", ...}

        Returns:
            {
                "recommended": TechStackRecommendation,
                "alternative": TechStackRecommendation,
                "not_recommended": [TechStackRecommendation, ...],
                "reasoning": str,
            }
        """
        preferences = preferences or {}

        # 1. 推断项目类型
        project_type = cls._infer_project_type(description, preferences)

        # 2. 获取候选栈
        candidate_keys = cls.TYPE_TO_STACKS.get(project_type, ["nextjs_fullstack"])
        candidates = [cls.STACKS[k] for k in candidate_keys if k in cls.STACKS]

        if not candidates:
            candidates = [cls.STACKS["nextjs_fullstack"]]

        # 3. 根据用户偏好排序
        preferred = cls._apply_preferences(candidates, preferences)

        # 4. 构建返回结果
        recommended = cls._to_recommendation(preferred[0], "recommended") if preferred else None
        alternative = cls._to_recommendation(preferred[1], "alternative") if len(preferred) > 1 else None
        not_recommended = [
            cls._to_recommendation(s, "not_recommended")
            for s in cls.STACKS.values()
            if s["name"] not in [p["name"] for p in preferred[:2]]
            and cls._is_relevant(s, project_type)
        ][:3]

        reasoning = cls._generate_reasoning(recommended, alternative, description, complexity)

        return {
            "recommended": recommended.__dict__ if recommended else None,
            "alternative": alternative.__dict__ if alternative else None,
            "not_recommended": [nr.__dict__ for nr in not_recommended],
            "reasoning": reasoning,
            "project_type": project_type,
        }

    @classmethod
    def get_stack_details(cls, stack_key: str) -> Optional[Dict[str, Any]]:
        """获取特定技术栈的详细信息"""
        stack = cls.STACKS.get(stack_key)
        if not stack:
            return None
        rec = cls._to_recommendation(stack, "recommended")
        return rec.__dict__

    @classmethod
    def list_all_stacks(cls) -> List[str]:
        """列出所有支持的栈"""
        return list(cls.STACKS.keys())

    # ===== 内部方法 =====

    @classmethod
    def _infer_project_type(cls, description: str, preferences: Dict[str, Any]) -> str:
        """从描述中推断项目类型"""
        desc_lower = description.lower()

        # 用户明确指定
        if preferences.get("project_type"):
            return preferences["project_type"]

        # 关键词匹配
        type_keywords = {
            "web_fullstack": ["全栈", "fullstack", "full stack", "网站", "web app", "web应用", "saas", "电商", "博客", "blog"],
            "web_frontend": ["前端", "frontend", "spa", "单页", "管理后台", "dashboard", "admin"],
            "backend_api": ["api", "后端", "backend", "微服务", "microservice", "接口", "服务端", "server"],
            "cli": ["cli", "命令行", "command line", "工具", "脚本", "script", "自动化"],
            "mobile": ["app", "移动", "mobile", "ios", "android", "手机", "小程序", "miniapp"],
            "extension": ["插件", "extension", "扩展", "vscode", "浏览器", "browser", "chrome"],
        }

        scores = {k: 0 for k in type_keywords}
        for ptype, keywords in type_keywords.items():
            for kw in keywords:
                if kw in desc_lower:
                    scores[ptype] += 1

        best_type = max(scores, key=scores.get)
        if scores[best_type] > 0:
            return best_type

        # 默认：web 全栈
        return "web_fullstack"

    @classmethod
    def _apply_preferences(
        cls,
        candidates: List[Dict],
        preferences: Dict[str, Any],
    ) -> List[Dict]:
        """根据用户偏好排序候选栈"""
        if not preferences:
            return candidates

        scored = []

        for stack in candidates:
            score = 0

            lang = preferences.get("language", "").lower()
            if lang:
                stack_layers = {k.lower(): v.lower() for k, v in stack.get("layers", {}).items()}
                all_tech = " ".join(stack_layers.values()) + " " + stack.get("name", "").lower()
                if lang in all_tech:
                    score += 10

            platform = preferences.get("platform", "").lower()
            if platform and platform in stack.get("description", "").lower():
                score += 5

            scored.append((score, stack))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored]

    @classmethod
    def _to_recommendation(cls, stack: Dict, tier: str) -> TechStackRecommendation:
        """将内置栈字典转为 TechStackRecommendation"""
        return TechStackRecommendation(
            name=stack["name"],
            tier=tier,
            description=stack["description"],
            layers=stack["layers"],
            pros=stack.get("pros", []),
            cons=stack.get("cons", []),
            best_for=stack.get("best_for", ""),
            not_for=stack.get("not_for", ""),
        )

    @classmethod
    def _is_relevant(cls, stack: Dict, project_type: str) -> bool:
        """判断栈是否与项目类型相关（用于不推荐列表）"""
        relevant_types = {
            "nextjs_fullstack": ["web_fullstack", "web_frontend"],
            "vite_react_spa": ["web_fullstack", "web_frontend", "extension"],
            "vue_nuxt": ["web_fullstack", "web_frontend"],
            "fastapi_backend": ["backend_api", "web_fullstack"],
            "express_typescript": ["backend_api", "web_fullstack"],
            "go_gin": ["backend_api"],
            "cli_python": ["cli"],
            "cli_rust": ["cli"],
        }
        return project_type in relevant_types.get(stack["name"].lower().replace(" ", "_"), [])

    @classmethod
    def _generate_reasoning(
        cls,
        recommended: Optional[TechStackRecommendation],
        alternative: Optional[TechStackRecommendation],
        description: str,
        complexity: str,
    ) -> str:
        """生成推荐理由"""
        parts = []

        if recommended:
            parts.append(f"**首选推荐：{recommended.name}**")
            parts.append(f"理由：{recommended.description}")
            parts.append(f"最适合：{recommended.best_for}")
            parts.append(f"优势：{'、'.join(recommended.pros[:3])}")

        if alternative:
            parts.append(f"\n**备选方案：{alternative.name}**")
            parts.append(f"当你需要 {alternative.best_for} 时考虑此方案")

        # 复杂度相关建议
        complexity_advice = {
            "simple": "简单项目建议选择最熟悉的技术栈，避免过度设计。部署策略从简。",
            "moderate": "中等复杂度建议选择一个生态完善的主流框架，减少造轮子的时间。",
            "complex": "复杂项目需要关注架构的可扩展性和测试策略。考虑微服务或模块化单体。",
            "platform": "平台级项目需要关注性能、可观测性、灾备。建议选择成熟的企业级技术栈。",
        }
        parts.append(f"\n{complexity_advice.get(complexity, '')}")

        return "\n".join(parts)


def recommend_tech_stack(
    description: str,
    complexity: str = "moderate",
    preferences: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """便捷函数"""
    return TechStackAdvisor.recommend(description, complexity, preferences)
