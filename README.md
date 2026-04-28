# LiteYuki SRE Agent

基于 [Google ADK](https://github.com/google/adk-python) 的多智能体 SRE 运维助手，支持 Gitea 代码托管管理、社区运营、容器镜像站等基础设施的智能化运维。

## 项目结构

```
adk-demo/
├── root_agent/              # 根调度 Agent
│   ├── agent.py             # root_agent 定义，编排 sub_agents
│   ├── _cli.py              # uv run 快捷命令入口
│   └── .env                 # 环境变量（API Key、模型配置）
├── gitea_agent/             # Gitea 子 Agent（44 个工具）
│   ├── agent.py             # gitea_agent 定义
│   ├── client.py            # GiteaClient — httpx 封装
│   └── tools/               # 按 API 分类的工具模块
│       ├── repository.py    # 仓库 + PR
│       ├── issue.py         # Issue + 评论
│       ├── user.py          # 用户信息
│       └── ...              # organization, notification, admin 等
├── model_config.py          # 统一模型配置
├── pyproject.toml           # Python 项目配置 + Ruff lint
└── web/                     # 前端（React 聊天界面）
    ├── src/
    │   ├── components/      # UI 组件
    │   ├── hooks/           # 状态管理
    │   └── types/           # TypeScript 类型
    └── package.json
```

## 环境要求

| 工具 | 版本 |
|------|------|
| Python | >= 3.13 |
| uv | >= 0.6 |
| Node.js | >= 20 |
| pnpm | >= 10 |

## 快速开始

### 1. 克隆项目

```bash
git clone <repo-url>
cd adk-demo
```

### 2. 安装 Python 依赖

```bash
uv sync
```

### 3. 配置环境变量

编辑 `root_agent/.env`：

```env
# Google Gemini（使用 Gemini 模型时需要）
GOOGLE_GENAI_USE_VERTEXAI=0
GOOGLE_API_KEY=你的_google_api_key

# 模型配置 — 全局默认
AGENT_MODEL=deepseek/deepseek-v4-flash
AGENT_TOKEN=你的_deepseek_api_key
AGENT_API=https://api.deepseek.com
```

### 4. 启动 Agent

```bash
# 终端交互模式
uv run dev

# Web UI 模式（ADK 自带）
uv run web
```

### 5. 配置 Gitea 连接

启动后在对话中告诉 Agent 你的 Gitea 地址和 Token，Agent 会自动保存配置：

```
> 帮我配置 Gitea，地址是 https://git.example.com，token 是 xxx
```

或通过环境变量预配置（在 `root_agent/.env` 中添加）：

```env
GITEA_BASE_URL=https://git.example.com
GITEA_TOKEN=你的_gitea_token
```

## 前端开发

```bash
cd web

# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev

# 生产构建
pnpm build
```

| 技术 | 版本 |
|------|------|
| Vite | 8 |
| React | 19 |
| TypeScript | 6 |
| TailwindCSS | 4 |
| shadcn/ui | latest |
| ESLint | @antfu/eslint-config |

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

## Python 开发命令

所有命令通过 `uv run` 调用：

| 命令 | 说明 |
|------|------|
| `uv run dev` | 启动 Agent 交互模式（adk run） |
| `uv run web` | 启动 Agent Web UI（adk web） |
| `uv run lint` | 运行 Ruff 代码检查 |
| `uv run fmt` | 运行 Ruff 代码格式化 |
| `uv run fix` | 自动修复 lint 问题 + 格式化 |
| `uv run check` | CI 用：lint + format 检查（不修改文件） |

## Gitea 凭证配置

支持三种方式（优先级从高到低）：

1. **交互式配置** — 通过 `setup_gitea` 工具在对话中配置，持久化到 `.credentials.json`
2. **环境变量** — 在 `.env` 中设置 `GITEA_BASE_URL` 和 `GITEA_TOKEN`
3. **文件配置** — 自动读取 `.credentials.json`（已加入 `.gitignore`）

## 扩展新 Agent

1. 创建新目录，例如 `community_agent/`
2. 在其中编写 `agent.py`、`tools/` 等
3. 在 `root_agent/agent.py` 的 `sub_agents` 中添加导入
4. 在 `model_config.py` 中通过环境变量配置专属模型（可选）

## License

MIT
