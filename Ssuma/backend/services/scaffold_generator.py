"""项目脚手架生成器 —— 支持多技术栈的项目初始化文件生成。

支持的栈：
- Next.js 14+ (React 全栈)
- Vite + React (前端 SPA)
- Vue + Nuxt 3
- FastAPI (Python 后端)
- Express + TypeScript (Node.js 后端)
"""

from typing import Dict, Any, List
import logging
from .context_generator import ContextGenerator
from .ide_exporter import IDEExporter

logger = logging.getLogger('Ssuma.ScaffoldGenerator')


class ScaffoldGenerator:
    """多技术栈项目脚手架生成器"""

    GENERATORS = {
        "nextjs": "_generate_nextjs",
        "nextjs_fullstack": "_generate_nextjs",
        "vite_react": "_generate_vite_react",
        "vite_react_spa": "_generate_vite_react",
        "vue_nuxt": "_generate_vue_nuxt",
        "fastapi_backend": "_generate_fastapi",
        "express_typescript": "_generate_express",
    }

    @classmethod
    def generate(cls, config: Dict[str, Any]) -> Dict[str, str]:
        """根据配置生成项目文件

        config:
            - name: 项目名称
            - tech_stack: 技术栈标识（nextjs, vite_react, vue_nuxt, fastapi, express）
            - stack_details: 技术栈详细配置（可选，来自 TechStackAdvisor）
            - description: 项目描述
            - features: 功能列表
            - data_model: 数据模型
        """
        stack = config.get("tech_stack", "nextjs")
        stack = stack.lower().replace("-", "_").replace(" ", "_")

        generator_name = cls.GENERATORS.get(stack, "_generate_nextjs")
        generator = getattr(cls, generator_name, cls._generate_nextjs)

        logger.info(f"Generating scaffold for stack '{stack}' using {generator_name}")
        files = generator(config)

        # 添加通用文件
        context_files = ContextGenerator.generate(config)
        for name, content in context_files.items():
            files[f"docs/{name}"] = content

        # 使用 IDE Exporter 生成 AI IDE 配置文件
        try:
            ide_project = IDEExporter.export(config)
            for path, content in ide_project.files.items():
                # 不覆盖已生成的 docs 文件
                if path.startswith("docs/") and f"docs/{path[5:]}" in files:
                    continue
                files[path] = content
        except Exception as e:
            logger.warning(f"IDE exporter failed, using fallback: {e}")
            cls._add_fallback_ide_files(files, config)

        return files

    # ===== Next.js 全栈 =====

    @classmethod
    def _generate_nextjs(cls, config: Dict[str, Any]) -> Dict[str, str]:
        name = config.get("name", "my-app").lower().replace(" ", "-")
        files = {}

        files["package.json"] = cls._json({
            "name": name,
            "version": "0.1.0",
            "private": True,
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "start": "next start",
                "lint": "next lint",
                "test": "vitest",
                "test:e2e": "playwright test",
            },
            "dependencies": {
                "next": "^14.2.0",
                "react": "^18.3.0",
                "react-dom": "^18.3.0",
                "@supabase/supabase-js": "^2.43.0",
                "@supabase/ssr": "^0.4.0",
                "zod": "^3.23.0",
                "tailwind-merge": "^2.3.0",
            },
            "devDependencies": {
                "@types/node": "^20",
                "@types/react": "^18.3.0",
                "@types/react-dom": "^18.3.0",
                "typescript": "^5.4.0",
                "tailwindcss": "^3.4.0",
                "postcss": "^8.4.0",
                "autoprefixer": "^10.4.0",
                "vitest": "^1.6.0",
                "@vitejs/plugin-react": "^4.3.0",
                "@testing-library/react": "^15.0.0",
                "@testing-library/jest-dom": "^6.4.0",
                "@playwright/test": "^1.44.0",
                "prettier": "^3.3.0",
            },
        })

        files["next.config.ts"] = """import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {},
};

export default nextConfig;
"""
        files["tsconfig.json"] = cls._json({
            "compilerOptions": {
                "target": "ES2017",
                "lib": ["dom", "dom.iterable", "esnext"],
                "allowJs": True,
                "skipLibCheck": True,
                "strict": True,
                "noEmit": True,
                "esModuleInterop": True,
                "module": "esnext",
                "moduleResolution": "bundler",
                "resolveJsonModule": True,
                "isolatedModules": True,
                "jsx": "preserve",
                "incremental": True,
                "plugins": [{"name": "next"}],
                "paths": {"@/*": ["./src/*"]},
            },
            "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
            "exclude": ["node_modules"],
        })

        files["tailwind.config.ts"] = """import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
export default config;
"""

        files["postcss.config.mjs"] = """/** @type {import('postcss-load-config').Config} */
const config = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
export default config;
"""

        files["src/app/layout.tsx"] = f"""import type {{ Metadata }} from "next";
import "./globals.css";

export const metadata: Metadata = {{
  title: "{name}",
  description: "{config.get('description', '')}",
}};

export default function RootLayout({{
  children,
}}: {{
  children: React.ReactNode;
}}) {{
  return (
    <html lang="zh-CN">
      <body className="antialiased min-h-screen bg-white text-gray-900">
        {{children}}
      </body>
    </html>
  );
}}
"""

        files["src/app/page.tsx"] = f"""export default function Home() {{
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold">{name}</h1>
      <p className="mt-4 text-gray-600">{config.get('description', '')}</p>
    </main>
  );
}}
"""

        files["src/app/globals.css"] = """@tailwind base;
@tailwind components;
@tailwind utilities;
"""

        files["vitest.config.ts"] = """import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
"""

        files["vitest.setup.ts"] = """import "@testing-library/jest-dom/vitest";
"""

        return files

    # ===== Vite + React SPA =====

    @classmethod
    def _generate_vite_react(cls, config: Dict[str, Any]) -> Dict[str, str]:
        name = config.get("name", "my-app").lower().replace(" ", "-")
        files = {}

        files["package.json"] = cls._json({
            "name": name,
            "version": "0.1.0",
            "private": True,
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "tsc -b && vite build",
                "preview": "vite preview",
                "test": "vitest",
                "lint": "eslint .",
            },
            "dependencies": {
                "react": "^18.3.0",
                "react-dom": "^18.3.0",
                "react-router-dom": "^6.23.0",
                "zustand": "^4.5.0",
                "@tanstack/react-query": "^5.40.0",
                "zod": "^3.23.0",
            },
            "devDependencies": {
                "@types/react": "^18.3.0",
                "@types/react-dom": "^18.3.0",
                "@vitejs/plugin-react": "^4.3.0",
                "typescript": "^5.4.0",
                "vite": "^5.2.0",
                "tailwindcss": "^3.4.0",
                "postcss": "^8.4.0",
                "autoprefixer": "^10.4.0",
                "vitest": "^1.6.0",
                "@testing-library/react": "^15.0.0",
                "@testing-library/jest-dom": "^6.4.0",
                "jsdom": "^24.1.0",
            },
        })

        files["vite.config.ts"] = """import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
"""

        files["tsconfig.json"] = cls._json({
            "compilerOptions": {
                "target": "ES2020",
                "useDefineForClassFields": True,
                "lib": ["ES2020", "DOM", "DOM.Iterable"],
                "module": "ESNext",
                "skipLibCheck": True,
                "moduleResolution": "bundler",
                "allowImportingTsExtensions": True,
                "isolatedModules": True,
                "moduleDetection": "force",
                "noEmit": True,
                "jsx": "react-jsx",
                "strict": True,
                "noUnusedLocals": True,
                "noUnusedParameters": True,
                "noFallthroughCasesInSwitch": True,
                "paths": {"@/*": ["./src/*"]},
            },
            "include": ["src"],
        })

        files["tailwind.config.ts"] = """import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: { extend: {} },
  plugins: [],
};
export default config;
"""

        files["postcss.config.js"] = """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
"""

        files["index.html"] = f"""<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{name}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""

        files["src/main.tsx"] = """import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import "./index.css";

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
"""

        files["src/App.tsx"] = f"""import {{ Routes, Route }} from "react-router-dom";

export default function App() {{
  return (
    <div className="min-h-screen bg-white text-gray-900">
      <Routes>
        <Route path="/" element={{<Home />}} />
      </Routes>
    </div>
  );
}}

function Home() {{
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold">{name}</h1>
      <p className="mt-4 text-gray-600">{config.get('description', '')}</p>
    </main>
  );
}}
"""

        files["src/index.css"] = """@tailwind base;
@tailwind components;
@tailwind utilities;
"""

        return files

    # ===== Vue + Nuxt 3 =====

    @classmethod
    def _generate_vue_nuxt(cls, config: Dict[str, Any]) -> Dict[str, str]:
        name = config.get("name", "my-app").lower().replace(" ", "-")
        files = {}

        files["package.json"] = cls._json({
            "name": name,
            "version": "0.1.0",
            "private": True,
            "type": "module",
            "scripts": {
                "dev": "nuxt dev",
                "build": "nuxt build",
                "generate": "nuxt generate",
                "preview": "nuxt preview",
                "test": "vitest",
            },
            "devDependencies": {
                "@nuxt/devtools": "^1.3.0",
                "@nuxtjs/tailwindcss": "^6.12.0",
                "nuxt": "^3.12.0",
                "vue": "^3.4.0",
                "typescript": "^5.4.0",
                "vitest": "^1.6.0",
                "@vue/test-utils": "^2.4.0",
            },
        })

        files["nuxt.config.ts"] = f"""export default defineNuxtConfig({{
  devtools: {{ enabled: true }},
  modules: ["@nuxtjs/tailwindcss"],
  app: {{
    head: {{
      title: "{name}",
      meta: [
        {{ name: "description", content: "{config.get('description', '')}" }}
      ],
    }},
  }},
}});
"""

        files["tsconfig.json"] = cls._json({
            "extends": "./.nuxt/tsconfig.json",
        })

        files["app.vue"] = """<template>
  <div>
    <NuxtPage />
  </div>
</template>
"""

        files["pages/index.vue"] = f"""<template>
  <main class="flex min-h-screen flex-col items-center justify-center p-8">
    <h1 class="text-4xl font-bold">{name}</h1>
    <p class="mt-4 text-gray-600">{config.get('description', '')}</p>
  </main>
</template>
"""

        return files

    # ===== FastAPI 后端 =====

    @classmethod
    def _generate_fastapi(cls, config: Dict[str, Any]) -> Dict[str, str]:
        name = config.get("name", "my-api").lower().replace(" ", "-").replace("_", "-")
        files = {}

        files["requirements.txt"] = """fastapi==0.111.0
uvicorn[standard]==0.30.0
sqlalchemy[asyncio]==2.0.30
alembic==1.13.0
pydantic==2.7.0
pydantic-settings==2.3.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
httpx==0.27.0
pytest==8.2.0
pytest-asyncio==0.23.0
"""

        files["pyproject.toml"] = f"""[project]
name = "{name}"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
"""

        files["app/main.py"] = f"""from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import api_router

app = FastAPI(title=settings.PROJECT_NAME, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {{"status": "ok"}}
"""

        files["app/__init__.py"] = ""
        files["app/core/__init__.py"] = ""
        files["app/core/config.py"] = f"""from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "{name}"
    BACKEND_CORS_ORIGINS: list = ["http://localhost:3000"]
    DATABASE_URL: str = "sqlite:///./{name}.db"

    class Config:
        env_file = ".env"

settings = Settings()
"""

        files["app/api/__init__.py"] = """from fastapi import APIRouter
from app.api import items

api_router = APIRouter()
api_router.include_router(items.router, prefix="/items", tags=["items"])
"""

        files["app/api/items.py"] = """from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_items():
    return {"items": []}
"""

        files["app/models/__init__.py"] = ""
        files["app/models/base.py"] = """from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
"""

        files["tests/__init__.py"] = ""
        files["tests/test_main.py"] = """from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
"""

        return files

    # ===== Express + TypeScript =====

    @classmethod
    def _generate_express(cls, config: Dict[str, Any]) -> Dict[str, str]:
        name = config.get("name", "my-api").lower().replace(" ", "-")
        files = {}

        files["package.json"] = cls._json({
            "name": name,
            "version": "0.1.0",
            "private": True,
            "scripts": {
                "dev": "tsx watch src/index.ts",
                "build": "tsc",
                "start": "node dist/index.js",
                "test": "vitest",
            },
            "dependencies": {
                "express": "^4.19.0",
                "cors": "^2.8.5",
                "zod": "^3.23.0",
                "dotenv": "^16.4.0",
            },
            "devDependencies": {
                "@types/express": "^4.17.21",
                "@types/cors": "^2.8.17",
                "@types/node": "^20",
                "typescript": "^5.4.0",
                "tsx": "^4.11.0",
                "vitest": "^1.6.0",
                "supertest": "^7.0.0",
                "@types/supertest": "^6.0.0",
            },
        })

        files["tsconfig.json"] = cls._json({
            "compilerOptions": {
                "target": "ES2020",
                "module": "commonjs",
                "lib": ["ES2020"],
                "outDir": "./dist",
                "rootDir": "./src",
                "strict": True,
                "esModuleInterop": True,
                "skipLibCheck": True,
                "forceConsistentCasingInFileNames": True,
                "resolveJsonModule": True,
                "declaration": True,
                "declarationMap": True,
                "sourceMap": True,
            },
            "include": ["src"],
            "exclude": ["node_modules", "dist"],
        })

        files["src/index.ts"] = f"""import express from "express";
import cors from "cors";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

app.get("/health", (_req, res) => {{
  res.json({{ status: "ok" }});
}});

app.listen(PORT, () => {{
  console.log(`Server running on http://localhost:${{PORT}}`);
}});

export default app;
"""

        files["tests/index.test.ts"] = """import { describe, it, expect } from "vitest";
import request from "supertest";
import app from "../src/index";

describe("Health Check", () => {
  it("should return ok", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });
});
"""

        return files

    # ===== 辅助方法 =====

    @classmethod
    def _json(cls, obj: Any) -> str:
        """格式化为 JSON 字符串，2 空格缩进"""
        import json
        return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"

    @classmethod
    def _add_fallback_ide_files(cls, files: Dict[str, str], config: Dict[str, Any]):
        """如果 IDE Exporter 不可用，使用降级方案"""
        name = config.get("name", "my-app").lower().replace(" ", "-")

        files[".cursorrules"] = f"""# AI IDE Rules for {name}
1. Always read `docs/context.md` first.
2. Follow the tech stack in `docs/tech_stack.md`.
3. Use TypeScript for all new files.
4. Use TailwindCSS for styling.
5. Do not hallucinate APIs or database schemas.
"""
        files["AGENTS.md"] = files.get("docs/context.md", f"# {name}\n\n{config.get('description', '')}")
