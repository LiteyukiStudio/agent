# LiteYuki SRE Agent

基于 [Google ADK](https://github.com/google/adk-python) 的多智能体 SRE 运维助手，支持 Gitea 代码托管管理、社区运营、容器镜像站等基础设施的智能化运维。提供完整的 Web 聊天界面，支持多用户、OAuth 登录、用量计费。

## 项目结构

```
adk-demo/
├── root_agent/                 # 根调度 Agent
│   ├── agent.py                # root_agent 定义，编排 sub_agents
│   ├── _cli.py                 # uv run 快捷命令入口
│   └── agents/
│       └── gitea_agent/        # Gitea 子 Agent（44 个工具）
│           ├── agent.py        # gitea_agent 定义
│           ├── client.py       # GiteaClient — httpx 封装
│           └── tools/          # 按 API 分类的工具模块
├── server/                     # FastAPI 后端
│   ├── main.py                 # 应用入口 + 启动初始化
│   ├── config.py               # 环境变量配置（Settings）
│   ├── database.py             # SQLAlchemy async 引擎
│   ├── deps.py                 # FastAPI 依赖注入（认证、DB session）
│   ├── models/                 # ORM 模型（9 个表）
│   ├── schemas/                # Pydantic 请求/响应模型
│   ├── routers/                # API 路由（34 个端点）
│   └── services/               # 业务逻辑层
├── model_config.py             # 统一 LLM 模型配置
├── web/                        # React 前端
│   ├── src/
│   │   ├── components/         # UI 组件
│   │   ├── hooks/              # 状态管理（useAuth, useChat）
│   │   ├── pages/              # 页面（Login, Chat, Settings, Admin）
│   │   ├── locales/            # i18n 翻译（zh/en/ja）
│   │   └── lib/                # 工具函数 + API client
│   └── package.json
├── Dockerfile                  # 后端镜像
├── web/Dockerfile              # 前端镜像（多阶段 Node → Nginx）
├── docker-compose.yml          # 编排文件
├── .env.example                # 环境变量模板
└── pyproject.toml              # Python 项目配置 + Ruff lint
```

## 技术栈

| 层 | 技术 |
|------|------|
| Agent 框架 | Google ADK |
| 后端 | FastAPI + SQLAlchemy 2.0 async + Pydantic v2 |
| 数据库 | SQLite（开发）/ PostgreSQL（生产） |
| 前端 | React 19 + Vite 8 + TypeScript 6 + TailwindCSS 4 + shadcn/ui |
| 认证 | JWT + OAuth 2.0 OIDC + API Token |
| 部署 | Docker Compose |

## 环境要求

| 工具 | 版本 |
|------|------|
| Python | >= 3.13 |
| uv | >= 0.6 |
| Node.js | >= 20 |
| pnpm | >= 10 |

## 快速开始

### 1. 克隆并安装

```bash
git clone <repo-url>
cd adk-demo
uv sync                    # Python 依赖
cd web && pnpm install     # 前端依赖
```

### 2. 配置环境变量

复制模板并填写：

```bash
cp .env.example .env
```

最小必填项：

```env
SECRET_KEY=一个随机字符串      # JWT 签名
AGENT_TOKEN=你的_llm_api_key  # LLM API 密钥
```

> 完整配置项说明见 `.env.example`。

### 3. 启动服务

```bash
# 后端（自动建表 + 创建初始超级用户 admin/admin）
uv run server

# 前端（另一个终端）
cd web && pnpm dev
```

打开 http://localhost:5173 即可使用。

### 4. Docker 部署

```bash
cp .env.example .env       # 编辑配置
docker compose up -d       # 启动
```

前端访问 `http://localhost`，后端 API `http://localhost:8000`。

## 核心功能

### 认证系统

- **密码登录** — 首次启动自动创建超级用户（`INITIAL_USERNAME` / `INITIAL_PASSWORD`）
- **OAuth 2.0 + OIDC** — 管理后台添加 Provider，自动发现 OIDC 端点，支持 whitelist/blacklist 访问控制
- **JWT** — 网页端认证，24 小时有效期
- **API Token** — 外部 API 调用，`lys_` 前缀，sha256 存储，支持 scope 和有效期

### 用户权限

三级角色：`superuser` > `admin` > `user`

| 角色 | 权限 |
|------|------|
| superuser | 所有操作 + 分配 admin |
| admin | 管理用户/OAuth/配额，不能修改其他 admin/superuser |
| user | 聊天 + 个人设置 + API Token |

### 用量计费

- 配额方案（QuotaPlan）：按日/周/月 token 用量限制 + 请求速率限制
- 自动创建默认 free 方案（100k/日, 500k/周, 1.5M/月）
- admin/superuser 不受配额限制

### 聊天

- SSE 流式输出（逐 token 推送）
- 工具调用可视化（调用中 → 完成状态展示）
- Markdown 渲染（GFM 表格支持）
- 自动会话标题（首条消息摘要，用户手动修改后不再覆盖）
- 消息持久化到数据库

### 用户配置隔离

- 每个用户独立的 Agent 凭据（如 Gitea Token）
- 通过 UserConfig 模型存储，工具运行时通过 ADK session state 注入
- 敏感值脱敏返回前端

## API 概览

所有接口 `/api/v1` 前缀，共 34 个端点。

| 模块 | 前缀 | 端点数 | 说明 |
|------|------|--------|------|
| auth | `/api/v1/auth` | 8 | 登录、OAuth、获取用户、API Token |
| chat | `/api/v1/chat` | 6 | 会话 CRUD + SSE 消息流 |
| usage | `/api/v1/usage` + `/api/v1/admin/usage` | 8 | 个人用量 + 管理端统计 + 配额方案 |
| admin | `/api/v1/admin` | 9 | 用户管理 + OAuth Provider + 访问名单 |
| user_config | `/api/v1/user` | 3 | 用户配置 CRUD |

## 模型配置

支持 Gemini、DeepSeek、OpenAI、Ollama 等任意 LLM，通过环境变量配置。

### 优先级

每个参数独立 fallback：

```
{AGENT_NAME}_MODEL  →  AGENT_MODEL  →  gemini-2.5-flash
{AGENT_NAME}_TOKEN  →  AGENT_TOKEN
{AGENT_NAME}_API    →  AGENT_API
```

### 示例

```env
# 全局用 DeepSeek
AGENT_MODEL=deepseek/deepseek-v4-flash
AGENT_TOKEN=sk-xxx
AGENT_API=https://api.deepseek.com

# root_agent 单独用 Gemini
ROOT_AGENT_MODEL=gemini-2.5-flash

# gitea_agent 用不同的 Token
GITEA_AGENT_TOKEN=sk-yyy
```

### 支持的模型

| 提供商 | MODEL 值 | 说明 |
|--------|----------|------|
| Gemini | `gemini-2.5-flash` | 原生支持，无需 LiteLLM |
| DeepSeek | `deepseek/deepseek-v4-flash` | 性价比首选 |
| DeepSeek | `deepseek/deepseek-v4-pro` | 强推理场景 |
| OpenAI | `openai/gpt-4o` | 需 OpenAI API Key |
| Ollama | `ollama/qwen3` | 本地部署，API 填 `http://localhost:11434` |

## 开发命令

### Python 后端

| 命令 | 说明 |
|------|------|
| `uv run server` | 启动后端（FastAPI + uvicorn, reload 模式） |
| `uv run dev` | 启动 Agent 交互模式（adk run） |
| `uv run web` | 启动 Agent Web UI（adk web） |
| `uv run lint` | 运行 Ruff 代码检查 |
| `uv run fmt` | 运行 Ruff 代码格式化 |
| `uv run fix` | 自动修复 lint 问题 + 格式化 |
| `uv run check` | CI 用：lint + format 检查（不修改文件） |

### 前端

```bash
cd web
pnpm install       # 安装依赖
pnpm dev           # 开发服务器（http://localhost:5173）
pnpm build         # 生产构建
pnpm lint          # ESLint 检查
pnpm lint --fix    # 自动修复
```

## Gitea 凭证配置

支持三种方式（优先级从高到低）：

1. **用户配置** — 登录后在 Web 界面设置个人 Gitea Token，存储到 UserConfig，与其他用户隔离
2. **环境变量** — 在 `.env` 中设置 `GITEA_BASE_URL` 和 `GITEA_TOKEN`（全局默认）
3. **交互式配置** — 通过 `setup_gitea` 工具在对话中配置

## 扩展新 Agent

1. 在 `root_agent/agents/` 下创建新目录，例如 `community_agent/`
2. 编写 `agent.py`、`tools/` 等
3. 在 `root_agent/agent.py` 的 `sub_agents` 中添加导入
4. 通过环境变量配置专属模型（可选）：`COMMUNITY_AGENT_MODEL=...`

## 开发规范

编码约定、项目结构、命名规则等请阅读 **[CONTRIBUTING.md](./CONTRIBUTING.md)**。

## License

MIT
