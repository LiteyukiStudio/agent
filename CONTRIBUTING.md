# 开发规范

本文档是项目的编码约定，面向开发者和 AI 编码助手。只列常用规则，细节由 Ruff / ESLint 自动检查。

## 通用

- 缩进：Python 4 空格，TypeScript 2 空格
- 文件末尾保留一个空行
- 字符串统一用**单引号**（Python / TypeScript 均适用）
- 提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/)：`feat:` / `fix:` / `refactor:` / `docs:` / `chore:`
- 不提交 `.env`、`.credentials.json`、`node_modules`、`__pycache__` 等敏感或生成文件
- **注释语言**：Python 代码的注释、模块 docstring、行内注释、段落标题统一用**中文**。工具函数的 docstring（`tools/*.py`）保持当前语言以确保 LLM 工具识别准确。TypeScript 注释保持英文。
- **配置项变更**：新增或修改环境变量时，必须同步更新 `.env.example`，并用注释标注：是否必填、作用说明、默认值。格式示例：
  ```env
  # [必填] JWT 签名密钥，用于用户认证令牌签发
  SECRET_KEY=请替换为随机字符串
  # [可选] PostgreSQL 连接地址，默认使用 SQLite
  # DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
  ```

## Python

### 风格

- 类型注解必须写，函数参数和返回值都要有
- 使用 Python 3.13+ 内置类型，**禁止从 `typing` 导入已内置的泛型**：
  - `dict` 不用 `typing.Dict`
  - `list` 不用 `typing.List`
  - `tuple` 不用 `typing.Tuple`
  - `set` 不用 `typing.Set`
  - `type` 不用 `typing.Type`
  - `X | Y` 不用 `typing.Union[X, Y]`
  - `X | None` 不用 `typing.Optional[X]`
- 使用 `from __future__ import annotations` 开启延迟求值（文件顶部）
- 优先 `pathlib.Path` 而非 `os.path`
- 禁止遗留 `print()`（tools 目录除外，调试用）
- import 顺序：stdlib → 第三方 → 本项目（isort 自动处理）
- **导入风格**：包内用相对导入，跨包用绝对导入
  - 包内：`from .tools import all_tools`、`from ..client import GiteaClient`
  - 跨包：`from server.config import settings`、`from model_config import get_model`
  - 同一个包内保持一致，不混用

### ADK Agent 规范

- 每个 Agent 一个独立 Python 包（目录），放在 `root_agent/agents/` 下
- Agent 名使用 `snake_case`，与目录名一致，如 `gitea_agent/` → `name="gitea_agent"`
- 工具函数必须有 **docstring + Args 注释**，这是 LLM 识别工具的唯一依据
- `tool_context: ToolContext` 参数不需要在 docstring 里写，ADK 自动注入
- Agent 的 `instruction` 用中文写，这是面向最终用户的
- 模型统一通过 `get_model("agent_name")` 获取，不硬编码模型名

### 凭据隔离（credential_provider）

**所有需要外部凭据的工具必须通过 `credential_provider` 读取，禁止直接 `os.getenv` 或读文件。**

这是多用户安全隔离的核心。每个用户的凭据（如 Gitea Token）互不可见。

#### 1. 声明凭据 schema（在 client.py 中）

```python
from credential_provider import CredentialKey, CredentialSchema

GITEA_CREDENTIALS = CredentialSchema(
    namespace="gitea",  # 与 UserConfig 的 namespace 一致
    keys={
        "base_url": CredentialKey(env_var="GITEA_BASE_URL", required=True),
        "token": CredentialKey(env_var="GITEA_TOKEN", secret=True),
    },
)
```

#### 2. 在工具函数中使用（通过 tool_context）

```python
from google.adk.tools import ToolContext
from credential_provider import credentials

def my_tool(owner: str, tool_context: ToolContext, page: int = 1) -> dict:
    """工具示例。tool_context 放在必需参数之后、可选参数之前。"""
    creds = credentials("my_service", ["base_url", "token"], tool_context)
    # 或者用 schema:
    creds = MY_CREDENTIALS.resolve(tool_context)
```

#### 3. 凭据解析优先级

```
tool_context.state["{namespace}_{key}"]   ← 用户专属（UserConfig 注入）
         ↓ 空则
os.environ["{NAMESPACE}_{KEY}"]           ← 全局默认（.env）
         ↓ 空则
CredentialKey.default                      ← 声明的默认值
```

#### 4. 工具函数签名规则

`tool_context: ToolContext` 必须放在 **所有必需参数之后、可选参数之前**：

```python
# ✅ 正确
def func(owner: str, repo: str, tool_context: ToolContext, page: int = 1) -> dict:

# ❌ 错误：tool_context 在可选参数之后（Python 语法错误）
def func(owner: str, page: int = 1, tool_context: ToolContext) -> dict:
```

```python
# 工具函数示例
def list_repos(owner: str, tool_context: ToolContext, page: int = 1, limit: int = 20) -> dict:
    """列出指定用户或组织拥有的仓库

    Args:
        owner: 仓库所有者的用户名或组织名，例如 liteyuki
        page: 页码，从 1 开始
        limit: 每页数量，默认 20，最大 50
    """
```

### Agent 目录结构

```
root_agent/agents/{agent_name}/
├── __init__.py          # 空文件或 re-export
├── agent.py             # Agent 定义（model, instruction, tools, sub_agents）
├── client.py            # 外部 API 客户端封装（如有）
└── tools/
    ├── __init__.py      # 汇总 all_tools 列表
    ├── feature_a.py     # 按功能域拆分，每个文件底部 export all_tools: list
    └── feature_b.py
```

### 后端架构（server/）

后端采用 **Router → Service → Model** 三层架构：

```
server/
├── main.py              # FastAPI 应用 + 启动初始化
├── config.py            # Settings（从 .env 读取）
├── database.py          # SQLAlchemy async 引擎 + session factory
├── deps.py              # 依赖注入（get_db, get_current_user, require_admin）
├── models/              # SQLAlchemy ORM 模型（数据库表定义）
├── schemas/             # Pydantic 请求/响应模型（数据校验）
├── routers/             # API 路由（薄层，只做参数校验和调用 service）
└── services/            # 业务逻辑（所有核心逻辑在这里）
```

**规则：**

- Router 不写业务逻辑，只做参数解析、权限检查（通过 Depends）、调用 Service
- Service 函数接收 `db: AsyncSession` 作为第一个参数
- Model 使用 `from __future__ import annotations`，主键统一 `uuid4` 字符串
- 新增路由必须写 response_model 和 status_code
- 所有接口 `/api/v1` 前缀

### 数据库迁移

本项目使用 SQLAlchemy `create_all()` 在启动时自动建表。**已存在的表不会被自动修改**。

- **新增表**：直接加 Model，重启后端即可自动创建
- **修改已有表结构**（加字段、改类型等）：需要**删除 `data.db` 并重启**
  ```bash
  rm data.db && uv run server
  ```
  这会丢失所有开发数据（用户、会话等），重启后自动重建表 + 初始超级用户
- **生产环境**：后续引入 Alembic 做正式迁移，开发阶段直接重建即可
- **注意**：改完 Model 后如果不删库重建，会出现 500 错误（表结构不匹配）

### 检查命令

```bash
uv run lint    # 检查
uv run fix     # 自动修复 + 格式化
uv run check   # CI 用，不修改文件
```

## TypeScript (web/)

### 包管理

- **强制使用 pnpm**，禁止使用 npm / yarn
- 安装依赖：`pnpm install`，添加包：`pnpm add <pkg>`
- 项目已配置 `packageManager` 字段，确保团队版本一致

### 风格

- 使用 `interface` 而非 `type`（除非需要联合类型或映射类型）
- 组件文件使用 `PascalCase.tsx`，工具函数使用 `camelCase.ts`
- React 组件用命名导出 `export function Component()`，不用 `export default`
- Props 类型与组件同文件定义，命名为 `{ComponentName}Props`
- 路径引用一律用 `@/` 别名，不写相对路径

### 项目结构

```
web/src/
├── components/
│   ├── chat/            # 聊天业务组件（ChatArea, MessageBubble, Sidebar, ...）
│   ├── layout/          # 布局组件
│   └── ui/              # shadcn/ui 基础组件（不手动修改）
├── hooks/               # 自定义 hooks（useChat, useAuth）
├── pages/               # 页面级组件
│   ├── LoginPage.tsx    # 登录（密码 + OAuth）
│   ├── ChatPage.tsx     # 聊天主页
│   ├── SettingsPage.tsx # 个人设置（Token + 用量）
│   └── admin/           # 管理后台
│       ├── AdminLayout.tsx
│       ├── UsersPage.tsx
│       ├── OAuthPage.tsx
│       └── QuotaPage.tsx
├── types/               # 共享类型定义
├── lib/                 # 工具函数（api.ts, utils.ts, i18n.ts）
├── locales/             # i18n 翻译文件（zh/en/ja）
├── App.tsx              # 路由 + Toaster
├── main.tsx             # 入口（AuthProvider + TooltipProvider）
└── index.css            # 全局样式 + Tailwind CSS 变量
```

### 路由

```
/login          → LoginPage（公开）
/               → ChatPage（需登录）
/settings       → SettingsPage（需登录）
/admin/users    → UsersPage（需 admin）
/admin/oauth    → OAuthPage（需 admin）
/admin/quota    → QuotaPage（需 admin）
```

认证守卫由 `ProtectedRoute` 组件实现，未登录自动重定向 `/login`。

### 样式

- 用 TailwindCSS class，不写自定义 CSS（除 `index.css` 的 CSS 变量）
- shadcn/ui 组件目录 `components/ui/` 由 CLI 生成，**不要手动修改**
- 颜色使用 CSS 变量（`bg-background`、`text-foreground`），不硬编码色值

### 图标

- 统一使用 **lucide-react** 图标库：`import { IconName } from 'lucide-react'`
- 菜单项、按钮等交互元素**必须搭配图标**，提升可识别性
- 图标尺寸：跟随文本用 `size-4`（16px），独立按钮用 `size-5`（20px）
- 不要混用其他图标库（heroicons、phosphor 等）

### Toast 通知

- 使用 **sonner** 库，全局 `<Toaster>` 在 `App.tsx` 中挂载
- 操作失败用 `toast.error(message)`，成功用 `toast.success(message)`
- **禁止用 `useState` 管理错误提示**，统一走 toast
- 导入方式：`import { toast } from 'sonner'`

### i18n

- 所有面向用户的文案走 i18n：`const { t } = useTranslation('namespace')`
- 翻译文件：`src/locales/{zh,en,ja}/{module}.json`，按模块拆分一层
- 不在组件里硬编码中文/英文字符串

### API 调用

- 使用 `src/lib/api.ts` 中的封装函数：`apiGet`, `apiPost`, `apiPatch`, `apiDelete`, `streamSSE`
- 401 响应自动清除 token，由 `ProtectedRoute` 驱动重定向，**不在 API 层硬跳转**
- SSE 流式响应使用 `streamSSE()` async generator

### 检查命令

```bash
cd web
pnpm lint      # ESLint 检查
pnpm lint --fix # 自动修复
```
