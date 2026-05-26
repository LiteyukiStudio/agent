# 会话命令工具与设备选择方案

## 背景

当前会话中，用户的所有已连接设备都会暴露给 Agent。对于很多实际场景，一个会话只需要控制一个设备，例如某台服务器、某台开发机或某个本地工作站。

如果每次都让 Agent 在所有设备中自行选择，会带来几个问题：

- 上下文暴露面过大，Agent 可以看到不相关设备。
- 误操作风险更高。
- 用户很难表达“这个会话只操作这台设备”。
- 前端缺少统一命令入口，后续新增命令和补全不够灵活。

建议增加两个能力：

1. 前端命令工具：支持 `/` 命令、命令补全、参数提示，命令定义由后端提供。
2. 会话设备选择：用户可以为当前会话指定目标设备；若用户未指定，Agent 再按现有逻辑调用工具选择设备。

## 目标

- 用户可以在前端为当前会话选择一个或多个允许操作的设备。
- 如果用户选择了设备，Agent 默认只能看到和操作被选择的设备。
- 如果用户没有选择设备，保持现有体验，由 Agent 调用 `local_list_devices` 自行判断。
- 前端支持后端驱动的命令列表、补全和参数提示。
- 后续新增命令不需要改前端核心逻辑。
- 命令执行仍然走后端权限校验，前端只负责交互和提交。

## 非目标

第一阶段不做：

- 不实现复杂 shell 语法。
- 不做前端本地命令执行。
- 不绕过现有聊天流式响应。
- 不允许前端直接调用本地 Agent。
- 不做跨用户共享设备。

## 会话设备选择

### 设备选择模式

建议每个会话增加 `device_scope`：

| 模式 | 说明 |
|------|------|
| `auto` | 默认模式，不指定设备，Agent 可调用工具自行选择 |
| `single` | 当前会话绑定一个设备 |
| `multiple` | 当前会话允许多个设备 |
| `none` | 当前会话禁用本地设备工具 |

第一阶段可以只实现：

- `auto`
- `single`
- `none`

`multiple` 可以保留数据结构，后续再开放 UI。

### 数据模型

可以在 `chat_sessions` 增加：

| 字段 | 说明 |
|------|------|
| `device_scope_mode` | `auto` / `single` / `multiple` / `none` |
| `selected_device_id` | 单设备模式下的设备 ID，可为空 |

如果要支持多设备，新增表：

### `session_devices`

| 字段 | 说明 |
|------|------|
| `id` | 记录 ID |
| `session_id` | 会话 ID |
| `device_id` | 设备 ID |
| `created_at` | 选择时间 |

第一阶段即使只做单设备，也可以直接建 `session_devices`，避免后续迁移。

### 权限规则

用户只能选择自己的设备。

服务层必须校验：

- `session_id` 属于当前用户。
- `device_id` 属于当前用户。
- 设备未被删除。
- 如果设备离线，允许选择但前端要标记离线；实际执行时仍会失败并提示。

管理员审查会话时可以看到会话绑定的设备名，但不应该获得该设备操作权限。

### Agent 运行时行为

在调用 `stream_response` 前，后端读取会话设备设置，并注入到 Agent state 或 local 工具上下文中。

推荐规则：

#### `auto`

保持现有行为：

- Agent 可以调用 `local_list_devices`。
- 如果有多个设备，Agent 根据用户描述选择。
- 必要时询问用户。

#### `single`

后端把当前会话绑定的 `device_id` 注入 local 工具上下文。

行为：

- `local_list_devices` 只返回该设备，或返回“当前会话已锁定设备”信息。
- `local_run_command`、`local_read_file`、`local_write_file` 默认使用该设备。
- Agent 不需要再选择设备。
- 如果 Agent 显式传入其他设备 ID，后端拒绝。

#### `none`

后端禁用本地设备工具。

行为：

- `local_list_devices` 返回当前会话禁用了设备。
- 其他 `local_` 工具调用直接拒绝。
- Agent 应提示用户在会话中选择设备后再继续。

### 前端 UI

聊天页面顶部增加设备选择器。

状态示例：

- `自动选择设备`
- `MacBook Pro 在线`
- `Server-01 离线`
- `本会话禁用设备`

交互：

- 点击后显示用户设备列表。
- 支持选择“自动”。
- 支持选择“禁用设备”。
- 第一阶段支持选择单个设备。
- 设备显示在线状态、系统类型、版本号、最后在线时间。

切换设备时建议弹确认：

- 如果当前会话已有本地操作记录，提示切换设备可能影响上下文。
- 切换只影响后续消息，不修改历史消息。

### API 设计

```http
GET   /api/v1/chat/sessions/{session_id}/device-scope
PUT   /api/v1/chat/sessions/{session_id}/device-scope
GET   /api/v1/local-agent/devices
```

请求示例：

```json
{
  "mode": "single",
  "device_ids": ["device-uuid"]
}
```

响应示例：

```json
{
  "mode": "single",
  "devices": [
    {
      "id": "device-uuid",
      "name": "MacBook Pro",
      "os_type": "macos",
      "version": "0.2.0",
      "online": true,
      "last_seen_at": "2026-05-26T12:00:00Z"
    }
  ]
}
```

## 前端命令工具

### 设计原则

前端只实现通用命令框架，具体命令信息由后端返回。

前端负责：

- 识别 `/`。
- 展示命令列表。
- 展示参数提示。
- 支持补全。
- 把命令提交给后端。

后端负责：

- 返回用户当前可用命令。
- 定义命令参数 schema。
- 执行命令或转换成会话操作。
- 做权限校验。

### 命令定义

后端提供命令 registry。

示例：

```json
{
  "name": "device",
  "aliases": ["dev"],
  "description": "选择当前会话使用的本地设备",
  "category": "session",
  "args": [
    {
      "name": "mode",
      "type": "enum",
      "required": true,
      "values": ["auto", "single", "none"]
    },
    {
      "name": "device",
      "type": "device",
      "required": false,
      "depends_on": {"mode": "single"}
    }
  ]
}
```

### 命令 API

```http
GET  /api/v1/commands
GET  /api/v1/commands/complete?q=/dev&session_id=xxx
POST /api/v1/chat/sessions/{session_id}/commands
```

`GET /api/v1/commands` 返回当前用户可用命令。命令列表可以根据：

- 用户权限。
- 当前会话。
- 是否有设备。
- 是否启用了 SKILL。
- 是否管理员。

`GET /api/v1/commands/complete` 返回补全建议。

`POST /commands` 执行命令。

请求示例：

```json
{
  "raw": "/device single MacBook",
  "command": "device",
  "args": {
    "mode": "single",
    "device_id": "device-uuid"
  }
}
```

响应示例：

```json
{
  "ok": true,
  "message": "当前会话已绑定设备：MacBook Pro",
  "effects": [
    {
      "type": "session_device_scope_updated",
      "mode": "single",
      "device_ids": ["device-uuid"]
    }
  ]
}
```

### 第一批命令建议

| 命令 | 说明 |
|------|------|
| `/help` | 查看可用命令 |
| `/device` | 查看或选择当前会话设备 |
| `/device auto` | 当前会话由 AI 自动选择设备 |
| `/device none` | 当前会话禁用本地设备 |
| `/device use <device>` | 当前会话绑定某个设备 |
| `/skills` | 查看当前会话可用和已加载的 SKILL |
| `/skill load <name>` | 加载 SKILL |
| `/skill unload <name>` | 卸载 SKILL |
| `/clear` | 清空输入框或新建干净会话，具体语义需确认 |

其中 SKILL 命令可以和 SKILL 管理功能共用后端服务。

### 补全类型

参数 `type` 可以支持：

| 类型 | 说明 |
|------|------|
| `string` | 普通文本 |
| `enum` | 枚举值 |
| `device` | 当前用户设备 |
| `skill` | 当前用户可用 SKILL |
| `session` | 当前用户会话 |
| `boolean` | 布尔值 |

补全请求应带 `session_id`，因为可用项可能和当前会话有关。

## 与 Agent 的边界

用户在前端选择设备后，AI 不再负责选择设备。

具体规则：

- 用户选择了 `single`：local 工具默认目标设备为该设备。
- 用户选择了 `none`：local 工具不可用。
- 用户选择了 `auto`：AI 按现有逻辑调用工具判断。

这不是单纯的前端状态，而是后端会话状态。所有 local 工具执行前必须读取后端状态并校验。

## 安全考虑

- 前端传入的 `device_id` 不可信，后端必须校验归属。
- Agent 显式传入的 `device` 也不可信，local 工具服务层必须校验是否在当前会话允许范围内。
- 设备选择只影响当前会话，不影响其他会话。
- 切换设备不修改历史消息。
- 管理员查看会话不获得设备控制权。
- `none` 模式下必须硬禁用 local 工具，而不是只在 prompt 中提示。

## 实施阶段

### Phase 1：设备选择

- `chat_sessions` 增加设备范围字段，或新增 `session_devices`。
- 增加设备范围 API。
- 聊天页顶部增加设备选择器。
- local 工具按会话设备范围过滤和拒绝。
- 支持 `auto`、`single`、`none`。

### Phase 2：命令框架

- 后端增加命令 registry。
- 前端输入框支持 `/` 命令列表。
- 支持命令补全。
- 支持 `/device` 命令。
- 命令执行通过后端 API。

### Phase 3：扩展命令

- 接入 SKILL 命令。
- 接入会话管理命令。
- 支持更多参数类型和动态补全。
- 支持命令执行后的 UI effects。

### Phase 4：多设备范围

- 开放 `multiple` 模式。
- 支持会话绑定多个设备。
- `local_list_devices` 只返回允许范围内的设备。
- local 工具拒绝范围外设备。

