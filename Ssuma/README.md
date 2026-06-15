# 枢墨 Ssuma

> 东方美学 AI 项目规划与对话生成平台

## 简介

枢墨（Ssuma）是一个以东方水墨美学为设计语言的 AI 驱动项目规划平台。它将传统项目管理方法论与大型语言模型（LLM）相结合，通过「七艺」工作流（启枢→裁衡→甄微→策书→凝墨→破妄→渐衍）引导用户完成从需求澄清到代码生成的完整项目生命周期。

## 核心特性

- **七艺工作流**：启枢 · 追问澄清、裁衡 · 价值审视、甄微 · 技术评审、策书 · 任务规划、凝墨 · 方案整合、破妄 · 覆盖验证、渐衍 · 分阶段生成
- **三通道模式**：快速（3步）、标准（5步）、深度（8步）
- **多模型支持**：OpenAI、Claude、DeepSeek、Gemini、Moonshot、Ollama、LM Studio 等 10+ 供应商
- **水墨风格 UI**：Three.js 粒子场景 + Canvas 墨海动画，支持玄墨/宣纸双主题
- **语音交互**：MediaRecorder 录音 + 多后端 STT（Groq/OpenAI/faster-whisper）+ edge-tts 机械音色合成
- **Human-in-the-Loop**：裁衡、甄微、凝墨阶段支持人工确认中断
- **MCP 工具集成**：支持 Model Context Protocol 工具调用
- **项目记忆系统**：工作记忆 → 项目记忆 → 进化记忆三层架构
- **反思循环（Reflexion）**：输出→反思→纠正→再输出的自精炼机制
- **Auto-Pilot**：一键自动流水线，从需求到方案全自动生成

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Next.js 16 + React 19 + TypeScript + Tailwind CSS v4 |
| 3D 场景 | Three.js + @react-three/fiber |
| 后端 | FastAPI + Python 3.11+ |
| 数据库 | SQLite（项目状态、对话历史）|
| 工作流 | LangGraph StateGraph + 条件边 |
| 容器化 | Docker + Docker Compose |

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 20+
- SQLite 3

### 1. 克隆仓库

```bash
git clone <repository-url>
cd Ssuma
```

### 2. 配置后端

```bash
cd backend

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置 LLM（编辑 config.yaml）
cp config.example.yaml config.yaml
# 在 config.yaml 中填写你的 API Key
```

### 3. 配置前端

```bash
cd ../frontend
npm install
```

### 4. 启动服务

```bash
# 终端 1：启动后端
cd backend
python main.py

# 终端 2：启动前端
cd frontend
npm run dev
```

访问 http://localhost:3000 进入意识空间。

### Docker 部署

```bash
docker-compose up --build
```

## 项目结构

```
Ssuma/
├── backend/                    # FastAPI 后端
│   ├── api/                    # REST API 路由
│   │   ├── chat.py             # 对话 API
│   │   ├── flow.py             # 工作流 API（八技艺状态机）
│   │   ├── llm_config.py       # LLM 配置 API（模型检测、测速）
│   │   ├── voice.py            # 语音 API（STT/TTS）
│   │   ├── mcp.py              # MCP 工具 API
│   │   ├── hitl.py             # Human-in-the-Loop API
│   │   ├── tanyin.py           # 探隐（问卷）API
│   │   ├── projects.py         # 项目管理 API
│   │   ├── generation.py       # 产物生成 API
│   │   ├── evolution.py        # 进化引擎 API
│   │   ├── feedback.py         # 反馈 API
│   │   ├── orchestrator.py     # 编排器 API
│   │   ├── wiki.py             # 文档 API
│   │   └── models.py           # Pydantic 请求/响应模型
│   ├── core/                   # 核心模块
│   │   ├── llm_factory.py      # LLM 工厂（多供应商统一接口）
│   │   ├── llm_adapter.py      # 模型适配与档次检测
│   │   ├── config.py           # YAML 配置加载
│   │   ├── state_repository.py # 项目状态持久化
│   │   ├── mcp_client.py       # MCP 协议客户端
│   │   ├── hitl.py             # HITL 中断存储
│   │   ├── circuit_breaker.py  # 熔断器
│   │   ├── middleware.py       # 请求中间件（限流、API Key）
│   │   ├── project_memory.py   # 项目记忆卡片
│   │   ├── skill_registry.py   # 技能注册表
│   │   ├── cache.py            # 缓存层
│   │   ├── errors.py           # 异常体系
│   │   ├── quality_gate.py     # 质量门
│   │   ├── garbage_detector.py # 死代码检测
│   │   ├── pattern_extractor.py# 模式提取器
│   │   └── learning_db.py      # 学习数据库
│   ├── db/
│   │   └── sqlite.py           # SQLite 数据库操作
│   ├── domain/
│   │   ├── enums.py            # 领域枚举（阶段、意图、通道）
│   │   ├── state.py            # 工作流状态定义
│   │   └── results.py          # 结果类型
│   ├── services/               # 业务服务层
│   │   ├── flow/               # 工作流引擎
│   │   │   ├── service.py      # Flow 主服务
│   │   │   ├── router.py       # 阶段路由逻辑
│   │   │   ├── graph.py        # LangGraph 状态图
│   │   │   └── middlewares.py  # 中间件链（Pre/Post generation）
│   │   ├── intent_analyzer.py  # 意图分析器
│   │   ├── context_manager.py  # 上下文管理器
│   │   ├── evolution_engine.py # 进化引擎（记忆升级）
│   │   ├── reflexion.py        # 反思循环
│   │   ├── phase_gates.py      # 阶段门控
│   │   ├── orchestrator.py     # 服务编排器
│   │   ├── project_service.py  # 项目管理
│   │   ├── tanyin_service.py   # 探隐服务
│   │   ├── scaffold_generator.py # 脚手架生成
│   │   ├── artifact_extractor.py # 产物提取
│   │   ├── artifact_store.py   # 产物存储
│   │   ├── ide_exporter.py     # IDE 导出
│   │   ├── document_parser.py  # 文档解析
│   │   ├── document_comparator.py # 文档比对
│   │   ├── fact_checker.py     # 事实核查
│   │   ├── response_validator.py # 响应校验
│   │   ├── tech_stack_advisor.py # 技术栈建议
│   │   ├── autopilot_service.py # 自动驾驶服务
│   │   └── feedback_service.py # 反馈服务
│   ├── skills/                 # 八技艺技能实现
│   │   ├── qishu.py            # 启枢（对话引导）
│   │   ├── tanyin_service.py   # 探隐（需求澄清问卷）
│   │   ├── caiheng.py          # 裁衡（CEO视角审视）
│   │   ├── zhenwei.py          # 甄微（技术架构评审）
│   │   ├── ceshu.py            # 策书（执行计划生成）
│   │   ├── ningmo.py           # 凝墨（方案生成）
│   │   ├── powang.py           # 破妄（需求覆盖检查）
│   │   ├── jianyan.py          # 渐衍（分阶段生成）
│   │   ├── autoplan.py         # 自动规划
│   │   ├── design_review.py    # 设计评审
│   │   ├── mindmap_generator.py # 思维导图生成
│   │   └── metacognition.py    # 元认知
│   ├── tests/                  # 测试套件
│   │   ├── test_api.py
│   │   ├── test_skills.py
│   │   ├── test_state_repository.py
│   │   ├── test_circuit_breaker.py
│   │   ├── test_orchestrator.py
│   │   ├── test_context_manager.py
│   │   ├── test_document_parser.py
│   │   ├── test_fact_checker.py
│   │   ├── test_quality_gate.py
│   │   ├── test_garbage_detector.py
│   │   ├── test_pattern_extractor.py
│   │   ├── test_learning_db.py
│   │   ├── test_scaffold_generator.py
│   │   ├── test_response_validator.py
│   │   ├── test_api_generation.py
│   │   ├── test_context_generator.py
│   │   └── test_tanyin_service.py
│   ├── main.py                 # FastAPI 入口
│   ├── requirements.txt        # Python 依赖
│   └── Dockerfile              # 后端容器镜像
├── frontend/                   # Next.js 前端
│   ├── src/app/
│   │   ├── consciousness/      # 主应用（意识空间）
│   │   │   ├── components/
│   │   │   │   ├── ConsciousnessScene.tsx    # Three.js 场景容器
│   │   │   │   ├── HITLCard.tsx              # HITL 确认卡片
│   │   │   │   ├── MCPPanel.tsx              # MCP 状态面板
│   │   │   │   ├── layers/
│   │   │   │   │   ├── L0FarMist.tsx         # 远景雾层
│   │   │   │   │   ├── L1Calligraphy3D.tsx   # 3D 书法层
│   │   │   │   │   ├── L2InkSphere.tsx       # 墨球粒子层
│   │   │   │   │   ├── L3TextFlow.tsx        # 文字流动层
│   │   │   │   │   ├── L4InkSea.tsx          # 墨海波浪层（Canvas）
│   │   │   │   │   └── PostProcessing.tsx    # 后处理效果
│   │   │   │   ├── modals/
│   │   │   │   │   └── TanyinModal.tsx       # 探隐问卷弹窗
│   │   │   │   ├── panels/
│   │   │   │   │   ├── HistoryPanel.tsx      # 历史记录面板
│   │   │   │   │   ├── ArtifactPanel.tsx     # 产物面板
│   │   │   │   │   └── StudyPanel.tsx        # 文房（设置）面板
│   │   │   │   └── ui/
│   │   │   │       ├── BrandPanel.tsx        # 右侧品牌面板
│   │   │   │       ├── InkConversation.tsx   # 对话流组件
│   │   │   │       ├── InputLine.tsx         # 输入框
│   │   │   │       ├── PhaseScroll.tsx       # 阶段进度条
│   │   │   │       ├── VoiceMode.tsx         # 语音模式 UI
│   │   │   │       ├── GradeOverlay.tsx      # 评级动画
│   │   │   │       ├── SsumaLogo.tsx         # Logo 组件
│   │   │   │       ├── QuickActions.tsx      # 快捷操作
│   │   │   │       └── LoadingIndicator.tsx  # 加载指示器
│   │   │   ├── context/
│   │   │   │   └── FlowContext.tsx           # 工作流状态上下文
│   │   │   ├── hooks/
│   │   │   │   ├── useConsciousness.ts       # 主业务逻辑 Hook
│   │   │   │   ├── useChatStream.ts          # 流式对话 Hook
│   │   │   │   ├── useVoiceMode.ts           # 语音模式 Hook
│   │   │   │   ├── useTTS.ts                 # TTS 语音合成 Hook
│   │   │   │   ├── useTanyin.ts              # 探隐问卷 Hook
│   │   │   │   └── useTheme.ts               # 主题切换 Hook
│   │   │   ├── types/
│   │   │   │   └── consciousness.ts          # TypeScript 类型定义
│   │   │   ├── styles/
│   │   │   │   └── consciousness.css         # 主样式表
│   │   │   ├── shaders/                      # GLSL 着色器（预留）
│   │   │   ├── page.tsx                      # 主页面
│   │   │   └── layout.tsx                    # 布局文件
│   │   ├── api/v1/                           # Next.js API 路由代理
│   │   │   ├── [...path]/                    # 通用后端代理
│   │   │   └── voice/
│   │   │       ├── stt/route.ts              # 语音转文字代理
│   │   │       └── tts/route.ts              # 文字转语音代理
│   │   ├── globals.css                       # 全局样式
│   │   ├── layout.tsx                        # 根布局
│   │   └── page.tsx                          # 根页面（重定向）
│   ├── src/lib/
│   │   ├── api.ts                            # API 客户端封装
│   │   ├── constants.ts                      # 前端常量
│   │   ├── types.ts                          # 共享类型
│   │   └── icons.tsx                         # 图标组件
│   ├── src/components/                       # 共享组件（预留）
│   ├── public/                               # 静态资源
│   │   ├── ssuma-logo.svg
│   │   ├── ssuma-logo-light.svg
│   │   └── stream-test.html
│   ├── next.config.ts                        # Next.js 配置
│   ├── package.json
│   ├── tsconfig.json
│   ├── Dockerfile                            # 前端容器镜像
│   └── postcss.config.mjs
├── docker-compose.yml                        # Docker 编排
├── config.yaml                               # 运行时配置
├── user_settings.json                        # 用户设置
├── LICENSE                                   # MIT 许可证
├── ARCHITECTURE.md                           # 架构文档
└── README.md                                 # 本文件
```

## 配置说明

### LLM 配置（backend/config.yaml）

```yaml
llm:
  default_provider: "deepseek"
  providers:
    deepseek:
      type: "openai_compatible"
      model: "deepseek-chat"
      base_url: "https://api.deepseek.com/v1"
      api_key: "your-api-key"
    
    claude:
      type: "anthropic"
      model: "claude-sonnet-4-20250514"
      api_key: "your-api-key"
    
    ollama:
      type: "openai_compatible"
      model: "qwen2.5"
      base_url: "http://127.0.0.1:11434/v1"
      api_key: ""
    
    lm_studio:
      type: "lm_studio"
      model: "your-local-model"
      base_url: "http://127.0.0.1:1234/v1"
      api_key: ""
```

### 本地模型注意事项

- **Ollama**：确保 Ollama 服务已运行，`/api/tags` 可访问
- **LM Studio**：启动 LM Studio 服务器模式，确认模型已加载
- 配置无效时系统会记录警告日志，不会自动遍历所有模型

## 开发指南

### 运行测试

```bash
cd backend
pytest tests/ -v
```

### 添加新技艺

1. 在 `backend/skills/` 创建新技能文件
2. 继承 `BaseSkill` 并实现 `execute` 方法
3. 在 `backend/skills/__init__.py` 注册

### 前端组件开发

```bash
cd frontend
npm run dev        # 开发模式
npm run build      # 生产构建
npm run lint       # 代码检查
```

## API 概览

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/flow/chat` | POST | 主对话流（支持 SSE 流式） |
| `/api/v1/flow/options` | GET | 获取当前阶段的交互选项 |
| `/api/v1/flow/status` | GET | 获取工作流状态 |
| `/api/v1/chat` | POST | 通用对话（非工作流） |
| `/api/v1/llm/list-providers` | GET | 列出已配置的 LLM 供应商 |
| `/api/v1/llm/fetch-models` | POST | 从服务器获取模型列表 |
| `/api/v1/llm/test-connection` | POST | 测试 LLM 连接 |
| `/api/v1/llm/config` | GET/POST | 读取/保存 LLM 配置 |
| `/api/v1/llm/health` | GET | LLM 健康检查 |
| `/api/v1/voice/stt` | POST | 语音转文字 |
| `/api/v1/voice/tts` | GET | 文字转语音 |
| `/api/v1/mcp/status` | GET | MCP 服务器状态 |
| `/api/v1/mcp/tools` | GET | 列出可用 MCP 工具 |
| `/api/v1/hitl/interrupts` | GET/POST | HITL 中断查询/响应 |
| `/api/v1/projects` | GET/POST | 项目列表/创建 |
| `/api/v1/tanyin` | POST | 提交探隐问卷 |
| `/api/v1/feedback` | POST | 提交反馈 |
| `/api/v1/evolution/report` | GET | 获取进化报告 |
| `/api/v1/health` | GET | 服务健康检查 |

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `NEXT_PUBLIC_API_BASE` | 后端 API 地址 | `http://localhost:8000` |
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `ANTHROPIC_API_KEY` | Anthropic API Key | - |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | - |
| `SILICONFLOW_API_KEY` | SiliconFlow API Key（语音回退） | - |

## 快捷键

| 按键 | 功能 |
|------|------|
| `空格`（按住） | 按住说话，松开发送语音 |
| `V` | 切换语音模式 |
| `Enter` | 发送消息 |
| `Shift + Enter` | 换行 |

## 常见问题

**Q: 配置本地模型后系统卡顿？**
A: 已修复。系统只会验证你配置的模型，不会遍历加载所有本地模型。

**Q: 侧边栏/品牌面板看不到？**
A: 检查是否误触 `V` 键进入了语音模式（语音模式会隐藏侧边栏）。刷新页面或再次按 `V` 切换回来。

**Q: 语音识别报错 503？**
A: 确保已配置至少一个 STT 后端。系统会自动从已配置的 LLM Provider 获取 API Key 进行语音识别，无需额外配置。也可通过 `GROQ_API_KEY` 或 `OPENAI_API_KEY` 环境变量单独配置，或安装 `faster-whisper` 使用本地离线识别。

**Q: 如何切换主题？**
A: 点击右上角的「墨/纸」按钮切换玄墨（深色）和宣纸（浅色）主题。

## 许可证

MIT License
