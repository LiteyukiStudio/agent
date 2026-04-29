# 多人协同模式方案

## 概述

在现有「用户 → 会话」架构基础上，新增 **协作组（Group）** 层级。协作模式下，会话和凭据都归属于 Group，组员共享同一套凭据进行操作，任何人都无法看到具体 Token 值，保证安全性。

## 数据模型

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Group      │────▶│  GroupMember      │◀────│    User          │
│              │     │                  │     │                 │
│  id          │     │  group_id        │     │  id             │
│  name        │     │  user_id         │     │  username       │
│  owner_id    │     │  role (admin/    │     │                 │
│  created_at  │     │        member)   │     └─────────────────┘
└──────┬───────┘     └──────────────────┘
       │
       │ 1:N
       ▼
┌──────────────────┐     ┌──────────────────┐
│  GroupConfig      │     │  ChatSession      │
│                  │     │                  │
│  group_id       │     │  group_id (可选)  │
│  namespace      │     │  user_id         │
│  key            │     │  is_collaborative│
│  value          │     │                  │
│  is_secret      │     └──────────────────┘
└──────────────────┘
```

### 新增表

#### `groups` — 协作组

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| name | String(200) | 组名 |
| owner_id | String(36) FK → users.id | 创建者 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

#### `group_members` — 组成员

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| group_id | String(36) FK → groups.id | 组 ID |
| user_id | String(36) FK → users.id | 用户 ID |
| role | String(20) | `owner` / `admin` / `member` |
| created_at | DateTime | 加入时间 |

**唯一约束**: `(group_id, user_id)`

#### `group_configs` — 组级凭据

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| group_id | String(36) FK → groups.id | 组 ID |
| namespace | String(100) | 如 `gitea`、`misskey` |
| key | String(100) | 如 `base_url`、`token` |
| value | String(2000) | 配置值 |
| is_secret | Boolean | 是否敏感 |
| created_at | DateTime | |
| updated_at | DateTime | |

**唯一约束**: `(group_id, namespace, key)`

### 已有表修改

#### `chat_sessions` — 新增字段

| 字段 | 类型 | 说明 |
|------|------|------|
| group_id | String(36) FK → groups.id, nullable | 归属组（NULL = 个人会话） |
| is_collaborative | Boolean, default False | 是否协作模式 |

## 凭据注入逻辑

`stream_response` 中注入 state 时判断会话类型：

```python
if chat_session.group_id:
    # 协作模式：用 GroupConfig（组共享凭据）
    configs = await get_group_configs(db, chat_session.group_id)
else:
    # 个人模式：用 UserConfig（现有逻辑）
    configs = await get_all_raw_configs(db, user.id)
```

### credential_provider 优先级

```
协作会话：
  GroupConfig[namespace_key]  ← 组共享凭据（唯一来源）
  （不读 UserConfig，不读环境变量）

个人会话（现有逻辑不变）：
  tool_context.state[namespace_key]  ← UserConfig 注入
  环境变量（仅 user_only=False 的 key）
  默认值
```

## 权限设计

### 组角色权限

| 操作 | owner | admin | member |
|------|-------|-------|--------|
| 查看协作会话消息 | ✅ | ✅ | ✅ |
| 在协作会话中发消息 | ✅ | ✅ | ✅ |
| 创建协作会话 | ✅ | ✅ | ✅ |
| 管理组凭据（增删改） | ✅ | ✅ | ❌ |
| 邀请/移除成员 | ✅ | ✅ | ❌ |
| 修改成员角色 | ✅ | ✅（不能改 owner） | ❌ |
| 删除组 | ✅ | ❌ | ❌ |
| 查看凭据原文 | ❌ | ❌ | ❌ |

**关键安全点**：即使是 owner 也无法看到凭据原文，`is_secret=True` 的值**永远脱敏返回**。

### 协作会话中的工具限制

- 协作模式下**禁用** `setup_gitea`、`setup_misskey` 等对话配置工具
- 凭据只能通过 Group 管理 API（Web 界面）配置
- 防止组员通过对话中的 setup 工具覆盖组凭据

## API 设计

### Group 管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/groups` | 创建组 |
| GET | `/api/v1/groups` | 列出我加入的组 |
| GET | `/api/v1/groups/{id}` | 组详情 |
| PATCH | `/api/v1/groups/{id}` | 更新组信息 |
| DELETE | `/api/v1/groups/{id}` | 删除组（仅 owner） |

### 成员管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/groups/{id}/members` | 成员列表 |
| POST | `/api/v1/groups/{id}/members` | 添加成员 |
| PATCH | `/api/v1/groups/{id}/members/{uid}` | 修改角色 |
| DELETE | `/api/v1/groups/{id}/members/{uid}` | 移除成员 |

### 组凭据管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/groups/{id}/configs` | 列出凭据（脱敏） |
| PUT | `/api/v1/groups/{id}/configs` | 设置凭据 |
| DELETE | `/api/v1/groups/{id}/configs/{ns}/{key}` | 删除凭据 |

### 协作会话

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/groups/{id}/sessions` | 创建协作会话 |
| GET | `/api/v1/groups/{id}/sessions` | 列出组的协作会话 |

## 前端 UI

### 侧边栏改造

```
── 个人会话 ──
  会话 A
  会话 B
── 协作组：SRE Team ──
  协作会话 C
  协作会话 D
── 协作组：Dev Team ──
  协作会话 E
```

### 新增页面

- **Group 管理页**（`/groups`）：创建组、列出组
- **Group 详情页**（`/groups/:id`）：成员管理 + 凭据配置
- **协作会话**：复用现有 ChatArea，标识显示组名和模式

### 协作会话标识

ChatArea 顶栏显示：
- 组名标签（如 `🏢 SRE Team`）
- 协作模式 badge
- 三点菜单中无"设为公开"（协作会话不支持公开分享）

## 后端文件清单

| 文件 | 说明 |
|------|------|
| `server/models/group.py` | Group + GroupMember 模型 |
| `server/models/group_config.py` | GroupConfig 模型 |
| `server/schemas/group.py` | 请求/响应模型 |
| `server/routers/group.py` | Group 相关 API |
| `server/services/group.py` | Group 业务逻辑 |
| `server/services/chat.py` | 修改：凭据注入适配 Group |
| `server/models/chat_session.py` | 修改：新增 group_id、is_collaborative |
| `credential_provider.py` | 修改：协作模式下只读 GroupConfig |

## 实施阶段

### Phase 1：核心功能
- Group CRUD + 成员管理
- GroupConfig 凭据存储
- ChatSession 关联 Group
- stream_response 凭据注入切换

### Phase 2：前端 UI
- 侧边栏分组显示
- Group 管理页面
- 协作会话标识

### Phase 3：增强（可选）
- WebSocket 实时消息同步（多人同时看到新消息）
- 组内消息通知
- 操作审计日志（谁在什么时候用 Agent 做了什么）
