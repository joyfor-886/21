# PlanCraft Core Design: Context + Scaffold (A + B)

## Overview
PlanCraft is an AI-powered project planning assistant that solves the "Vibe Code Execution Gap". It helps users who have ideas but lack technical/prompt engineering skills to successfully implement projects using AI IDEs (like Cursor, GitHub Copilot, Trae).

Core philosophy: **Instead of teaching users how to prompt, PlanCraft generates the perfect context and scaffolding so AI IDEs work like professional engineers.**

## Architecture

### High-Level Flow
1. **User Input**: Natural language description of the project idea.
2. **Intent Analysis**: PlanCraft analyzes the request to extract:
   - Core features & user stories
   - Target audience & use cases
   - Technical constraints (if any)
3. **Context Generation (A)**: Produces a set of structured Markdown files:
   - `spec.md`: Product requirements, user stories, acceptance criteria.
   - `tech_stack.md`: Recommended technology stack with reasoning.
   - `data_model.md`: Database schema, API endpoints, data flow.
   - `context.md`: A single file combining all critical info for AI IDE injection.
4. **Scaffold Generation (B)**: Based on the chosen tech stack, generates a standardized project skeleton with:
   - Correct directory structure.
   - Base configurations (linting, formatting, CI/CD).
   - Empty route/component files matching the spec.
5. **Beta Orchestrator (C)**: (Experimental) Step-by-step task execution prompts for AI IDEs with automatic error analysis.

### Component Design

#### 1. Context Generator
- **Input**: Structured project spec (from intent analysis).
- **Output**: Directory of Markdown files.
- **Format Standards**:
  - Uses clear headings, tables for data models, and code blocks for examples.
  - Includes explicit instructions for AI IDEs (e.g., "READ THIS FILE FIRST").
  - Modular: Users can inject `@spec.md` for high-level context or `@data_model.md` for implementation details.

#### 2. Scaffold Generator
- **Input**: Tech stack selection + Data model.
- **Output**: ZIP archive or Git repository containing project files.
- **Mechanism**:
  - Uses template system (like `create-next-app` but customizable).
  - Injects generated `context.md` into `docs/` folder.
  - Adds `AGENTS.md` / `CLAUDE.md` / `.cursorrules` pre-filled with project context for AI IDEs that support rule files.

#### 3. Beta Orchestrator (C)
- **Purpose**: Guide users through step-by-step implementation with AI IDEs.
- **Features**:
  - Task queue with dependencies.
  - Pre-written prompts for each task (including file paths and context references).
  - Error handler: User pastes error -> PlanCraft analyzes -> Generates fix prompt.
- **Status**: Beta, hidden behind feature flag initially.

## Data Flow

```
User -> [Idea Input] -> PlanCraft AI -> [Intent Analysis] -> [Spec Generation]
                                           |
                                           v
                              [Context Generator] ---> Markdown Files (A)
                                           |
                                           v
                              [Scaffold Generator] ---> ZIP/Repo (B)
                                           |
                                           v (Beta)
                              [Orchestrator] ---> Step-by-step Prompts (C)
```

## Error Handling
1. **Invalid Input**: If user description is too vague, PlanCraft asks clarifying questions before generating.
2. **Generation Failure**: If AI fails to produce a valid spec, fallback to template-based generation with placeholders.
3. **Scaffold Errors**: Provide troubleshooting guide for common IDE setup issues.
4. **Beta Orchestrator**: If IDE returns errors, PlanCraft analyzes stack trace/logs and outputs targeted fix prompts.

## Testing Strategy
1. **Unit Tests**: Context generator output validation (schema checks).
2. **Integration Tests**: End-to-end flow from idea -> scaffold -> AI IDE import.
3. **User Testing**: Measure success rate of non-technical users completing projects using PlanCraft vs baseline.

## Future Extensions
- **Direct IDE Integration**: MCP server or plugin to send contexts/prompts directly to AI IDEs without copy-paste.
- **Live Sync**: Track IDE changes and update PlanCraft state automatically.
- **Collaborative Mode**: Multiple users working on same project spec.
