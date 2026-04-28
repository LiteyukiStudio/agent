# 开发规范

本文档是项目的编码约定，面向开发者和 AI 编码助手。只列常用规则，细节由 Ruff / ESLint 自动检查。

## 通用

- 缩进：Python 4 空格，TypeScript 2 空格
- 文件末尾保留一个空行
- 字符串统一用**单引号**（Python / TypeScript 均适用）
- 提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/)：`feat:` / `fix:` / `refactor:` / `docs:` / `chore:`
- 不提交 `.env`、`.credentials.json`、`node_modules`、`__pycache__` 等敏感或生成文件
- **注释语言**：Python 代码的注释、模块 docstring、行内注释、段落标题统一用**中文**。工具函数的 docstring（`tools/*.py`）保持当前语言以确保 LLM 工具识别准确。TypeScript 注释保持英文。

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

- 每个 Agent 一个独立 Python 包（目录），包含 `agent.py` 和 `__init__.py`
- Agent 名使用 `snake_case`，与目录名一致，如 `gitea_agent/` → `name="gitea_agent"`
- 工具函数必须有 **docstring + Args 注释**，这是 LLM 识别工具的唯一依据
- `tool_context: ToolContext` 参数不需要在 docstring 里写，ADK 自动注入
- Agent 的 `instruction` 用中文写，这是面向最终用户的
- 模型统一通过 `get_model("agent_name")` 获取，不硬编码模型名

```python
# 工具函数示例
def list_repos(owner: str, page: int = 1, limit: int = 20) -> dict:
    """列出指定用户或组织拥有的仓库

    Args:
        owner: 仓库所有者的用户名或组织名，例如 liteyuki
        page: 页码，从 1 开始
        limit: 每页数量，默认 20，最大 50
    """
```

### 项目结构

```
{agent_name}/
├── __init__.py          # 空文件或 re-export
├── agent.py             # Agent 定义（model, instruction, tools, sub_agents）
├── client.py            # 外部 API 客户端封装（如有）
└── tools/
    ├── __init__.py      # 汇总 all_tools 列表
    ├── feature_a.py     # 按功能域拆分，每个文件底部 export all_tools: list
    └── feature_b.py
```

### 检查命令

```bash
uv run lint    # 检查
uv run fix     # 自动修复 + 格式化
uv run check   # CI 用，不修改文件
```

## TypeScript (web/)

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
│   ├── chat/            # 业务组件（ChatArea, MessageBubble, ...）
│   └── ui/              # shadcn/ui 基础组件（不手动修改）
├── hooks/               # 自定义 hooks（useChat, useAuth, ...）
├── types/               # 共享类型定义
├── lib/                 # 工具函数（utils.ts）
├── App.tsx              # 根组件
├── main.tsx             # 入口
└── index.css            # 全局样式 + Tailwind
```

### 样式

- 用 TailwindCSS class，不写自定义 CSS（除 `index.css` 的 CSS 变量）
- shadcn/ui 组件目录 `components/ui/` 由 CLI 生成，**不要手动修改**
- 颜色使用 CSS 变量（`bg-background`、`text-foreground`），不硬编码色值

### 图标

- 统一使用 **lucide-react** 图标库：`import { IconName } from 'lucide-react'`
- 菜单项、按钮等交互元素**必须搭配图标**，提升可识别性
- 图标尺寸：跟随文本用 `size-4`（16px），独立按钮用 `size-5`（20px）
- 不要混用其他图标库（heroicons、phosphor 等）

### i18n

- 所有面向用户的文案走 i18n：`const { t } = useTranslation('namespace')`
- 翻译文件：`src/locales/{zh,en,ja}/{module}.json`，按模块拆分一层
- 不在组件里硬编码中文/英文字符串

### 检查命令

```bash
cd web
pnpm lint      # ESLint 检查
pnpm lint --fix # 自动修复
```
