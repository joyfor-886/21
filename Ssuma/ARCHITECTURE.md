# Ssuma 升华改造 — 架构文档与变更记录

## 项目概述

**Ssuma** 是一个 AI 驱动的智能项目对话与生成平台，采用水墨风格 UI，核心工作流为 **8 技艺 + 3 通道**。

### 8 技艺阶段
| 序号 | 名称 | 拼音 | 职责 |
|------|------|------|------|
| 1 | 启枢 | qishu | 意图识别与项目启动 |
| 2 | 探隐 | tanyin | 需求深层挖掘 |
| 3 | 裁衡 | caiheng | 产品价值评审 |
| 4 | 甄微 | zhenwei | 技术选型与架构评审 |
| 5 | 策书 | ceshu | 方案规划 |
| 6 | 凝墨 | ningmo | 最终方案成案 |
| 7 | 破妄 | powang | 方案质疑与验证 |
| 8 | 渐衍 | jianyan | 迭代演进 |

### 3 条通道
| 通道 | 阶段数 | 适用场景 |
|------|--------|---------|
| 快速 | 3 | 简单需求 |
| 标准 | 5 | 常规项目 |
| 深度 | 8 | 复杂系统 |

---

## 技术栈

- **前端**: Next.js 16 + React 19 + Three.js + TypeScript
- **后端**: FastAPI + SQLite + Python 3.13
- **LLM**: 10+ 供应商（OpenAI/Anthropic/Ollama/DeepSeek 等）
- **协议**: MCP (Model Context Protocol) + WebSocket

---

## 改造历程（Phase 1-8）

### Phase 1: 基础加固

**目标**: 消除技术债，建立类型安全基础

| 改造项 | 文件 | 说明 |
|--------|------|------|
| FastAPI 依赖注入 | `api/dependencies.py`, `main.py` | `get_db()`, `get_flow_service()`, `get_llm_factory()` |
| 路由改用 DI | `api/flow.py`, `api/chat.py`, `api/projects.py`, `api/tanyin.py` | 全部改用 `Depends()` 注入 |
| TypeScript 类型强化 | `lib/types.ts` | 新增 `ArtifactSummary`, `FlowChatResponse`, `AutoPilotResult` |
| 前端类型修复 | `FlowContext.tsx`, `api.ts`, `useChatStream.ts` | 消除 `any`，改用具体类型 |

### Phase 2: 核心重构

**目标**: 统一流式处理，结构化输出，中间件框架

| 改造项 | 文件 | 说明 |
|--------|------|------|
| 流式统一 | `services/flow/service.py` | `process_message` 收集 `process_message_stream` 的 chunk |
| Pydantic 结构化 | `domain/results.py` | 4 个核心类转为 `BaseModel`，带字段验证 |
| 中间件链框架 | `services/flow/middlewares.py` | `FlowContext` + `FlowMiddleware` + 7 个中间件 |

### Phase 3: 架构升级

**目标**: 三层记忆 + 进化引擎 + 声明式路由

| 改造项 | 文件 | 说明 |
|--------|------|------|
| 项目记忆卡 | `core/project_memory.py` | `ProjectMemoryCard` + `ProjectMemoryStore`（SQLite 持久化） |
| 进化引擎重写 | `services/evolution_engine.py` | 从"提议-审核"改为"反射-微调"，只做 LOW 风险调整 |
| 声明式路由图 | `services/flow/graph.py` | `FlowGraph` 替代 140 行 if-elif 链 |
| 路由兼容层 | `services/flow/router.py` | 委托到 `FlowGraph`，重新导出保持兼容 |
| 前端 hook 拆分 | `hooks/useConsciousness.ts`, `page.tsx` | 339行→160行，逻辑与渲染分离 |

### Phase 4: 智能增强

**目标**: 双层评估 + 反思循环

| 改造项 | 文件 | 说明 |
|--------|------|------|
| 双层评估 | `services/phase_gates.py` | 关键词快速路径 40% + LLM 深度路径 60% |
| 反思循环 | `services/reflexion.py` | 输出→反思→纠正→再输出，凝墨阶段自动触发 |

### Phase 5: 中间件链集成

**目标**: 将中间件框架真正接入处理流程

| 改造项 | 文件 | 说明 |
|--------|------|------|
| 中间件升级 | `services/flow/middlewares.py` | 拆分 Pre/Post 两阶段，新增 MemoryContext/Reflexion/PostProcess |
| 流程重构 | `services/flow/service.py` | `process_message_stream` 改为 Pre→生成→Post 三阶段 |

**中间件执行链**:
```
Pre-generation: MemoryContext → Identity → Intent → Channel → Routing
                                                    ↓
                                          [流式 LLM 生成]
                                                    ↓
Post-generation (逆序): PostProcess → Reminder → MCPToolCall → Reflexion → HITL → Evaluation
```

### Phase 6: MCP Tools 集成

**目标**: 支持外部工具扩展智能体能力

| 改造项 | 文件 | 说明 |
|--------|------|------|
| MCP 客户端 | `core/mcp_client.py` | `MCPConfig` + `MCPClientManager` + 工具发现/调用 |
| MCP API | `api/mcp.py` | status/servers/tools/call/refresh/reconnect |
| 中间件集成 | `middlewares.py` | `RoutingMiddleware` 注入工具上下文 + `MCPToolCallMiddleware` 执行 |
| 配置 | `config.yaml` | 新增 `mcp_servers` 配置段 |

### Phase 7: Human-in-the-Loop

**目标**: 关键阶段人工确认

| 改造项 | 文件 | 说明 |
|--------|------|------|
| HITL 核心 | `core/hitl.py` | `HumanInterrupt` + `HITLStore` + `HITLDecider` |
| HITL API | `api/hitl.py` | pending/interrupt/respond/feedback/config |
| HITL 中间件 | `middlewares.py` | `HITLMiddleware` 在裁衡/甄微/凝墨阶段触发 |
| 前端类型 | `types.ts`, `api.ts`, `FlowContext.tsx`, `useChatStream.ts` | HITLInterrupt 类型 + API + 状态管理 |

**默认触发条件**:
- 裁衡(caiheng): 完成度 ≥ 50% → 产品价值评审需确认
- 甄微(zhenwei): 完成度 ≥ 50% → 技术选型需确认
- 凝墨(ningmo): 完成度 ≥ 50% → 最终方案需确认
- MCP 工具调用: 任意 → 高风险操作需确认

### Phase 8: 完善与收尾

| 改造项 | 文件 | 说明 |
|--------|------|------|
| WebSocket 适配 | `main.py` | 改用 `FlowService.process_message_stream`，支持流式 chunk + HITL |
| 测试覆盖 | `tests/test_new_modules.py` | 110 个新测试，覆盖 FlowGraph/Memory/Reflexion/MCP/HITL/Middlewares |
| HITL 确认卡片 | `components/HITLCard.tsx` | 水墨风格确认界面，支持 accept/ignore/response/edit |
| MCP 状态面板 | `components/MCPPanel.tsx` | 服务器状态 + 工具列表 + 刷新 |
| MCP API 函数 | `lib/api.ts` | `fetchMCPStatus()`, `fetchMCPTools()` |
| 自定义颜色 | `globals.css` | `--color-ink`, `--color-ink-light` |

---

## 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │Conscious- │  │ HITLCard │  │ MCPPanel │  │FlowContext│ │
│  │ness Page  │  │ 确认卡片  │  │ 工具面板  │  │ 状态管理   │ │
│  └─────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│        └──────────┬───┴──────────┬───┴──────────┬─┘       │
│                   │  HTTP/WebSocket API         │          │
└───────────────────┼─────────────────────────────┼──────────┘
                    │                             │
┌───────────────────┼─────────────────────────────┼──────────┐
│                   ▼         Backend (FastAPI)    ▼          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              API Layer (FastAPI Routers)              │  │
│  │  flow │ chat │ projects │ tanyin │ mcp │ hitl │ voice │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │  Depends() DI                     │
│  ┌──────────────────────▼───────────────────────────────┐  │
│  │              FlowService (核心引擎)                    │  │
│  │  ┌─────────────────────────────────────────────────┐ │  │
│  │  │         Middleware Chain (中间件链)               │ │  │
│  │  │  Pre: Memory→Identity→Intent→Channel→Routing    │ │  │
│  │  │  Gen: [LLM Stream]                              │ │  │
│  │  │  Post: Eval→HITL→Reflex→MCP→Remind→PostProc    │ │  │
│  │  └─────────────────────────────────────────────────┘ │  │
│  └──────────┬──────────┬──────────┬─────────────────────┘  │
│             │          │          │                          │
│  ┌──────────▼──┐ ┌─────▼────┐ ┌──▼──────────┐             │
│  │  FlowGraph  │ │  MCP     │ │  HITL       │             │
│  │  声明式路由  │ │  Client  │ │  Decider    │             │
│  └─────────────┘ │  Manager │ │  + Store    │             │
│                  └─────┬────┘ └─────────────┘             │
│  ┌──────────┐  ┌───────▼──────┐                            │
│  │ Project  │  │   LLM        │                            │
│  │ Memory   │  │   Factory    │                            │
│  │ Card     │  │  (10+ 供应商) │                            │
│  └──────────┘  └──────────────┘                            │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │Evolution │  │Reflexion │  │PhaseGates│                 │
│  │Engine    │  │Loop      │  │双层评估   │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 测试统计

| 指标 | 改造前 | 改造后 |
|------|--------|--------|
| 后端测试数 | 17 | **237** |
| TypeScript 编译 | 有类型错误 | **零错误** |
| 测试覆盖模块 | 基础模块 | FlowGraph/Memory/Reflexion/MCP/HITL/Middlewares |

---

## 关键设计决策

1. **中间件链而非硬编码**: 参考 Agno Capability 设计，将 process_message_stream 的步骤拆分为可插拔中间件
2. **声明式路由图**: 参考 LangGraph StateGraph，用 `DEFAULT_PROGRESSION` 映射替代 if-elif 链
3. **三层记忆架构**: 工作记忆(ContextManager) → 项目记忆(ProjectMemoryCard) → 进化记忆(SelfEvolutionEngine)
4. **反射-微调进化**: 只做 LOW 风险微调(±0.05)，HIGH 风险仅记录建议
5. **双层评估策略**: 关键词快速路径 40% + LLM 深度路径 60%，只在边界情况调用 LLM
6. **非阻塞 HITL**: 暂停时不阻塞服务器，持久化中断状态等待前端响应
7. **MCP 工具注入**: 通过 system_prompt 注入工具描述，LLM 用 `tool_call` 格式调用
