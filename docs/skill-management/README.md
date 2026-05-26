# SKILL 管理方案

## 背景

Liteyuki Flow 需要支持用户上传自己的 SKILL，也需要支持管理员上传面向所有用户或部分用户开放的公共 SKILL 包。

SKILL 的定位是对 Agent 能力的可管理扩展。第一阶段建议只支持文档型 SKILL，即通过 `SKILL.md` 向 Agent 注入使用说明、流程、约束和参考资料，不直接执行用户上传代码。后续可以扩展到 MCP 型 SKILL 或沙箱代码型 SKILL。

核心目标：

- 用户可以上传、启用、停用自己的私有 SKILL。
- 管理员可以上传、发布、停用公共 SKILL。
- 会话可以手动加载或卸载 SKILL。
- 新会话可以按用户默认设置自动加载 SKILL。
- 多租户之间文件、权限、运行时上下文严格隔离。
- SKILL 有版本管理，老会话使用的版本可保持稳定。

## SKILL 类型

### 系统内置 SKILL

随代码发布，部署时自带。管理员不可删除，只能启用或停用。

### 公共 SKILL

由管理员上传和发布。可以对所有用户可见，也可以按用户、角色、配额方案或后续协作组授权。

### 用户私有 SKILL

由普通用户上传，仅上传者自己可见，仅上传者自己的会话可以加载。

## SKILL 包格式

上传包建议使用 zip 格式，根目录包含：

```text
my-skill/
  skill.json
  SKILL.md
  assets/
  scripts/
  references/
```

必需文件：

- `skill.json`：机器可读 manifest。
- `SKILL.md`：给 Agent 读取的能力说明。

可选目录：

- `assets/`：图片、模板、静态资源。
- `references/`：长文档、示例、规范等参考资料。
- `scripts/`：辅助脚本或示例脚本。第一阶段仅作为参考文件，不执行。

示例 `skill.json`：

```json
{
  "name": "k8s-troubleshooter",
  "display_name": "Kubernetes 故障排查",
  "version": "0.1.0",
  "description": "帮助分析 Kubernetes 资源、日志和常见故障",
  "entry": "SKILL.md",
  "capabilities": ["read_context", "tool_guidance"],
  "required_tools": ["local_read_file", "local_run_command"],
  "permissions": {
    "local_agent": "ask",
    "network": "deny",
    "secrets": "deny"
  }
}
```

字段说明：

| 字段 | 说明 |
|------|------|
| `name` | 稳定唯一名，只允许小写字母、数字、短横线、下划线 |
| `display_name` | 前端展示名 |
| `version` | SKILL 包版本 |
| `description` | 简短描述 |
| `entry` | 入口文档，第一阶段固定为 `SKILL.md` |
| `capabilities` | 能力声明，例如 `read_context`、`tool_guidance` |
| `required_tools` | 建议或依赖的工具名 |
| `permissions` | 权限声明，供审核、展示和运行时约束使用 |

## 文件存储

数据库只保存元数据，不直接保存上传文件内容。上传包和解包后的只读文件放在 Skill Storage 中。

开发和单机部署可以使用本地目录：

```text
data/
  skills/
    users/
      {user_id}/
        {skill_id}/
          versions/
            {version_id}/
              package.zip
              unpacked/
                skill.json
                SKILL.md
                assets/
                references/
                scripts/
    public/
      {skill_id}/
        versions/
          {version_id}/
            package.zip
            unpacked/
```

生产部署可以替换为对象存储，例如 S3、MinIO 或 R2：

```text
skills/private/{user_id}/{skill_id}/{version_id}/package.zip
skills/public/{skill_id}/{version_id}/package.zip
```

所有文件访问必须经过 `SkillStorageService`，业务代码不直接拼接路径。

## 数据模型

### `skills`

保存 SKILL 的逻辑实体。

| 字段 | 说明 |
|------|------|
| `id` | SKILL ID |
| `owner_user_id` | 私有 SKILL 所属用户，公共和系统 SKILL 为 `NULL` |
| `name` | manifest 中的稳定名 |
| `display_name` | 展示名 |
| `description` | 描述 |
| `visibility` | `private` / `public` / `system` |
| `status` | `active` / `disabled` / `deleted` |
| `latest_version_id` | 当前默认版本 |
| `created_by` | 上传者 |
| `created_at` / `updated_at` | 时间 |

建议唯一约束：

- 私有 SKILL：`(owner_user_id, name)`
- 公共或系统 SKILL：`(visibility, name)`

### `skill_versions`

保存 SKILL 的具体版本。

| 字段 | 说明 |
|------|------|
| `id` | 版本 ID |
| `skill_id` | 所属 SKILL |
| `version` | manifest 版本 |
| `manifest_json` | manifest 快照 |
| `package_hash` | 上传包 hash |
| `storage_key` | 原始包存储位置 |
| `unpacked_path` | 解包后的只读路径或对象存储前缀 |
| `review_status` | `pending` / `approved` / `rejected` |
| `validation_status` | `valid` / `invalid` |
| `validation_errors` | 校验错误 |
| `created_at` | 时间 |

### `user_skill_settings`

保存用户对 SKILL 的启用设置。

| 字段 | 说明 |
|------|------|
| `user_id` | 用户 |
| `skill_id` | SKILL |
| `enabled` | 是否对用户启用 |
| `auto_load` | 新会话是否自动加载 |
| `pinned_version_id` | 可选，锁定版本 |
| `created_at` / `updated_at` | 时间 |

### `session_skills`

保存某个会话实际加载的 SKILL。

| 字段 | 说明 |
|------|------|
| `session_id` | 会话 |
| `skill_id` | SKILL |
| `version_id` | 实际加载版本 |
| `loaded_by` | `auto` / `manual` |
| `enabled` | 当前会话是否启用 |
| `loaded_at` | 加载时间 |

后续协作组模式可以新增 `group_skills`：

| 字段 | 说明 |
|------|------|
| `group_id` | 协作组 |
| `skill_id` | SKILL |
| `enabled` | 是否启用 |
| `pinned_version_id` | 组内锁定版本 |

## 多租户隔离

### 可见性隔离

普通用户只能看到：

- 自己的私有 SKILL。
- 已发布且授权给自己的公共 SKILL。
- 系统内置且启用的 SKILL。

管理员可以管理公共 SKILL 和系统 SKILL。是否允许管理员查看用户私有 SKILL 原文需要单独设计审计权限，默认不建议开放。

### 文件隔离

私有 SKILL 的存储路径必须包含 `user_id`。所有读取通过服务层完成：

```python
await skill_storage.get_skill_file(
    user_id=user.id,
    skill_id=skill_id,
    version_id=version_id,
    path="SKILL.md",
)
```

服务层必须检查：

- 当前用户是否拥有该 SKILL，或是否有公共 SKILL 的访问权限。
- `path` 不允许绝对路径。
- `path` 不允许包含 `..` 目录穿越。
- 不跟随符号链接。

### 运行时隔离

Agent 运行时只加载当前会话启用的 SKILL。不要把完整 SKILL 仓库、其他用户私有 SKILL 或本地绝对路径暴露给模型。

推荐在 `stream_response` 前构造当前会话的 SKILL 上下文：

```python
active_skills = await skill_service.get_active_session_skills(db, user.id, session_id)
skill_context = await skill_service.render_skill_context(active_skills)
```

然后把 `skill_context` 注入到 Agent 会话状态或 instruction 中。

如果 SKILL 需要引用资源，提供受控工具：

- `skill_list_files(skill_id)`
- `skill_read_file(skill_id, path)`

这些工具内部仍然必须做用户、会话、路径权限检查。

## 上传和校验流程

### 用户上传私有 SKILL

1. 用户上传 zip 包。
2. 后端保存原始包。
3. 解压到隔离目录。
4. 校验 `skill.json` 和 `SKILL.md`。
5. 校验文件大小、文件数量和路径安全。
6. 写入 `skills` 和 `skill_versions`。
7. 默认创建为 `private + active`。
8. 默认不自动加载，除非用户上传时勾选。

### 管理员上传公共 SKILL

1. 管理员上传 zip 包。
2. 后端保存、解包、校验。
3. 写入版本记录。
4. 进入 `pending` 或直接 `approved`。
5. 管理员发布为公共 SKILL。
6. 可配置授权范围：
   - 所有人可用。
   - 仅管理员可用。
   - 指定用户可用。
   - 指定配额方案可用。
   - 后续指定协作组可用。

### 校验规则

必须校验：

- 压缩包总大小限制。
- 单文件大小限制。
- 文件数量限制。
- 必须存在 `skill.json`。
- 必须存在 `SKILL.md`。
- `name` 格式合法。
- `version` 格式合法。
- 禁止绝对路径。
- 禁止 `..` 目录穿越。
- 禁止或忽略符号链接。
- `SKILL.md` 长度限制，例如 100KB。
- 第一阶段不执行 `scripts/` 中任何内容。

## 启用、停用和加载

SKILL 有两级状态。

### 用户级启用

表示用户认可该 SKILL，可以在自己的会话中使用。

用户可以设置：

- 是否启用。
- 是否新会话自动加载。
- 是否锁定版本。

### 会话级加载

表示当前会话实际注入了某个 SKILL。

新会话创建时，自动加载 `user_skill_settings.auto_load = true` 的 SKILL。老会话保持自己的 `session_skills` 记录，不因为用户后续修改默认设置而自动变化。

公共 SKILL 发布新版本后：

- 新会话默认使用最新版。
- 老会话继续使用原 `version_id`。
- 用户可以手动升级会话中的 SKILL 版本。
- 用户也可以在用户级设置中 pin 固定版本。

## 前端功能

用户设置页增加 SKILL 管理：

- 我的 SKILL。
- 公共 SKILL。
- 上传私有 SKILL。
- 启用 / 停用。
- 新会话自动加载。
- 删除私有 SKILL。
- 查看版本。
- 锁定版本或使用最新版。

聊天页增加会话 SKILL 选择器：

- 当前会话已加载 SKILL。
- 加载 SKILL。
- 卸载 SKILL。
- 升级 SKILL 版本。

管理后台增加公共 SKILL 管理：

- 上传公共 SKILL。
- 发布 / 下线。
- 查看校验状态。
- 查看版本。
- 设置授权范围。

## API 设计

### 用户 SKILL

```http
GET    /api/v1/skills
POST   /api/v1/skills/upload
GET    /api/v1/skills/{skill_id}
PATCH  /api/v1/skills/{skill_id}/settings
DELETE /api/v1/skills/{skill_id}
```

### 会话 SKILL

```http
GET    /api/v1/chat/sessions/{session_id}/skills
POST   /api/v1/chat/sessions/{session_id}/skills
DELETE /api/v1/chat/sessions/{session_id}/skills/{skill_id}
PATCH  /api/v1/chat/sessions/{session_id}/skills/{skill_id}
```

### 管理员公共 SKILL

```http
GET    /api/v1/admin/skills
POST   /api/v1/admin/skills/upload
PATCH  /api/v1/admin/skills/{skill_id}
POST   /api/v1/admin/skills/{skill_id}/versions/{version_id}/publish
DELETE /api/v1/admin/skills/{skill_id}
```

## Agent 工具

可以给 root agent 增加受控工具：

- `list_available_skills`
- `list_loaded_skills`
- `load_skill`
- `unload_skill`

这些工具只能操作当前用户和当前会话有权限访问的 SKILL，不能绕过后端权限检查。

## 分阶段实施

### Phase 1：文档型 SKILL

- 支持 zip 上传。
- 支持 `skill.json + SKILL.md`。
- 支持用户私有 SKILL。
- 支持管理员公共 SKILL。
- 支持用户级启用和停用。
- 支持会话级加载和卸载。
- 支持新会话自动加载。
- 支持版本记录。
- 不执行用户上传代码。

### Phase 2：MCP 型 SKILL

- manifest 支持声明 MCP server。
- 用户为 MCP server 配置凭据。
- 按用户隔离加载 MCP 工具。
- 在会话中启用或停用 MCP 型 SKILL。

### Phase 3：沙箱代码型 SKILL

只有在明确需要时再做。

要求：

- 不在主进程 import 用户代码。
- 独立 worker 或容器沙箱执行。
- CPU、内存、执行时间限制。
- 网络访问策略。
- 文件系统只读挂载。
- 调用审计。
- 高风险能力必须用户审批。

