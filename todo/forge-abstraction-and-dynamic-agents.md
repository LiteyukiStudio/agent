# 代码托管平台统一抽象 + Agent 动态加载

## 一、Forge 统一抽象（GitHub / Gitea / Forgejo）

### 背景

Gitea API 本身就是照着 GitHub REST API 设计的，80%+ 的端点路径和参数结构一致。
差异主要在：认证头格式、分页参数名、GitHub 独有功能（Actions 等）。

### 方案：抽象基类 + 平台适配

```
forge_base/                      # 通用代码托管平台基类（新增共享包）
├── __init__.py
├── client.py                    # ForgeClient 基类
│                                  - 统一 get/post/put/patch/delete
│                                  - 抽象方法：_build_auth_header(), _paginate()
├── credentials.py               # 通用 CredentialSchema（base_url + token）
├── tools/
│   ├── __init__.py
│   ├── repository.py            # list_repos, get_repo, create_repo, delete_repo, ...
│   ├── issue.py                 # list_issues, create_issue, edit_issue, ...
│   ├── pull_request.py          # list_prs, create_pr, merge_pr, ...
│   ├── user.py                  # get_me, get_user, search_users, ...
│   └── organization.py          # list_orgs, get_org, list_org_repos, ...
│
gitea_agent/
├── client.py                    # class GiteaClient(ForgeClient)
│                                  - auth: "token {token}"
│                                  - pagination: page + limit
│                                  - base_path: /api/v1
├── agent.py                     # Gitea 特有 instruction
├── tools/                       # 只放 Gitea 独有的工具，通用的从 forge_base 导入
│   └── setup.py
│
github_agent/
├── client.py                    # class GitHubClient(ForgeClient)
│                                  - auth: "Bearer {token}"
│                                  - pagination: page + per_page, Link header
│                                  - base_path: (none, 直接 api.github.com)
├── agent.py                     # GitHub 特有 instruction
├── tools/
│   ├── setup.py
│   └── actions.py               # GitHub 独有：Workflows, Runs, Artifacts
```

### 通用工具函数模式

```python
# forge_base/tools/repository.py
def list_repos(owner: str, tool_context: ToolContext, page: int = 1, limit: int = 20) -> dict:
    """List repositories owned by a user or organization."""
    with get_forge_client(tool_context) as c:  # 自动根据 namespace 选择 Client 类型
        return c.get(f"/repos/search", params={"owner": owner, "page": page, "limit": limit})
```

### 关键差异处理

| 差异点 | 处理方式 |
|--------|---------|
| 认证头 | ForgeClient 抽象方法 `_build_auth_header()` |
| 分页 | ForgeClient 抽象方法 `_paginate(params)` |
| API 前缀 | 子类设 `api_base_path` |
| 独有功能 | 各自 agent 的 tools/ 下单独实现 |
| 默认实例 | Gitea: git.liteyuki.org, GitHub: api.github.com |

## 二、Agent 动态加载（插件化）

### 背景

目前 Agent 注册是硬编码在 `root_agent/agent.py` 的 `sub_agents` 列表中。
新增或移除 Agent 需要改代码 + 重启。目标是支持 pip install 安装、配置文件启用。

### 方案：Python Entry Points + YAML 配置

#### 1. Agent 包结构标准

```toml
# pyproject.toml（第三方 Agent 包示例）
[project]
name = "liteyuki-sre-github-agent"
version = "0.1.0"
dependencies = ["liteyuki-sre-core>=0.1"]  # 依赖核心包

[project.entry-points."liteyuki_sre.agents"]
github_agent = "github_agent:agent_manifest"
```

```python
# github_agent/__init__.py
from .agent import github_agent

agent_manifest = {
    "agent": github_agent,                     # ADK Agent 实例
    "credential_namespaces": ["github"],        # 需要持久化的凭据命名空间
    "description": "GitHub 代码托管管理",
}
```

#### 2. 配置文件

```yaml
# agents.yaml（项目根目录）
agents:
  # 内置 Agent（始终可用）
  gitea_agent:
    enabled: true

  misskey_agent:
    enabled: true

  # 外部安装的 Agent
  github_agent:
    enabled: true
    # package: liteyuki-sre-github-agent  # 自动从 entry_points 发现

  # 禁用的 Agent
  harbor_agent:
    enabled: false
```

#### 3. 动态加载器

```python
# agent_loader.py
import yaml
from importlib.metadata import entry_points
from pathlib import Path

def load_agents(config_path: str = "agents.yaml") -> tuple[list[Agent], set[str]]:
    """加载所有启用的 Agent，返回 (agents, credential_namespaces)。"""
    config = yaml.safe_load(Path(config_path).read_text()) if Path(config_path).exists() else {}
    agent_configs = config.get("agents", {})

    agents = []
    all_namespaces = set()

    # 1. 从 entry_points 发现已安装的 Agent
    for ep in entry_points(group="liteyuki_sre.agents"):
        agent_cfg = agent_configs.get(ep.name, {})
        if not agent_cfg.get("enabled", True):  # 默认启用
            continue

        manifest = ep.load()
        agents.append(manifest["agent"])
        all_namespaces.update(manifest.get("credential_namespaces", []))

    return agents, all_namespaces

# root_agent/agent.py
from agent_loader import load_agents

sub_agents, credential_namespaces = load_agents()

root_agent = Agent(
    ...
    sub_agents=sub_agents,
)

# chat.py 中 PERSIST_CREDENTIAL_NAMESPACES 也从 credential_namespaces 获取
```

#### 4. 核心包拆分

```
liteyuki-sre-core/               # 核心框架（pip install liteyuki-sre-core）
├── credential_provider.py        # 凭据隔离
├── model_config.py               # 模型配置
├── agent_loader.py               # 动态加载器
├── forge_base/                   # 代码托管通用基类
└── server/                       # FastAPI 后端

liteyuki-sre-gitea-agent/        # 内置 Agent（可选独立发布）
liteyuki-sre-misskey-agent/
liteyuki-sre-github-agent/       # 社区贡献的 Agent
```

### Agent SDK 约定

每个 Agent 包必须导出 `agent_manifest` 字典：

```python
agent_manifest = {
    # 必须
    "agent": Agent,                           # ADK Agent 实例
    "credential_namespaces": list[str],       # 凭据命名空间列表

    # 可选
    "description": str,                       # 人类可读描述
    "version": str,                           # Agent 版本
    "setup_tools": list[str],                 # 协作模式下需要禁用的配置工具名
}
```

### 安全考虑

| 风险 | 对策 |
|------|------|
| 恶意 Agent 包 | 包签名校验 / 只允许可信源（私有 PyPI） |
| 凭据泄露 | Agent 只能通过 credential_provider 读凭据 |
| 权限越界 | Agent 工具只能操作自己声明的 namespace |
| 版本冲突 | 核心包声明最低兼容版本 |

## 实施建议

### 优先级

1. **Forge 统一抽象**（先做）—— 重构现有 GiteaClient，再加 GitHub 适配
2. **Agent 动态加载**（后做）—— 需要把项目拆成多个包，改动较大

### 分步实施

- Phase 1: 抽取 `forge_base` 共享包，重构 `gitea_agent` 继承
- Phase 2: 实现 `github_agent`，验证抽象层可用性
- Phase 3: 引入 `agents.yaml` + entry_points 动态加载
- Phase 4: 拆分为独立 pip 包，发布到 PyPI
