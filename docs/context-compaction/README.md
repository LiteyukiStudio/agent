# 上下文压缩设计方案

## 背景

当前 Liteyuki Flow 的聊天会话会持久化完整消息，同时复用同一个 ADK session 继续对话。随着会话增长，用户消息、助手回复、工具调用、工具结果、图片说明、代码片段和日志会不断进入模型上下文。

如果不做上下文管理，长会话最终会遇到上游模型的上下文窗口限制，表现为：

- 模型 API 返回 context length exceeded 或等价错误。
- ADK Runner 抛异常。
- SSE 向前端返回 error。
- 用户继续在同一个会话发消息时仍然可能反复失败。

目标是做到：

- 完整历史继续保存在数据库中，用于 UI、审计和公开分享。
- 发送给模型的上下文可自动压缩，避免长会话不可继续。
- 压缩后仍尽量保留当前任务状态、关键事实、最近原文和工具结果摘要。
- 支持自动触发，也支持用户手动触发。
- 压缩失败时有降级策略，不破坏原会话。

## 行业参考

### Codex 类 Agent

Codex 这类 coding agent 通常支持手动 `/compact` 和自动压缩两种入口。常见策略是：

- token 使用接近模型上下文窗口时自动触发。
- 用户可以手动触发压缩。
- 旧历史被摘要替换。
- 最近一段用户消息和关键上下文保留原文。
- 自动压缩时把摘要插入到最后一条用户消息之前，保证当前请求能接在摘要后继续执行。
- 压缩失败时裁剪更旧的工具调用、reasoning 或消息再重试。

参考：

- OpenAI Codex CLI: https://developers.openai.com/codex/cli
- Codex history compaction analysis: https://deepwiki.com/openai/codex/3.5.1-history-compaction-system

### OpenCode 类 Agent

OpenCode 在 TUI 中提供 `/compact` 命令，也会围绕 token 使用和上下文溢出做 session compaction。常见做法是：

- 监控每轮 LLM 的 token 使用。
- 上下文接近上限时触发压缩。
- 摘要旧历史。
- 裁剪老工具结果和大块输出。
- 保留最近会话片段，提高 follow-up 连续性。

参考：

- OpenCode TUI `/compact`: https://opencode.ai/docs/tui/
- OpenCode compaction analysis: https://instagit.com/anomalyco/opencode/how-does-opencode-implement-session-compaction-and-trigger-memory-optimization/

## 设计原则

### 完整历史不删

`messages` 表保存的是产品历史和审计历史，不应因为上下文压缩而删除或改写。压缩只影响后续送给模型的 ADK session context。

### 压缩不是简单截断

直接丢掉旧消息会让 Agent 丢失目标、决策和约束。压缩应通过 LLM 生成结构化摘要，并保留最近几轮原文。

### 工具结果强裁剪

工具调用结果往往是上下文膨胀的主要来源，尤其是：

- 代码文件全文。
- 日志。
- JSON API 响应。
- 搜索结果。
- Docker、Kubernetes、CI 输出。
- Gitea OpenAPI 端点详情。

旧工具结果应保留来源、结论、关键字段和错误信息，不保留完整正文。

### 凭据和状态不能丢

压缩重建 ADK session 时必须重新注入：

- `__user_id`
- `__chat_session_id`
- UserConfig 中的用户凭据和配置
- MCP 配置
- Push/Misskey/Gitea 等 Agent state
- 未来的 SKILL、设备选择、协作组状态

### 压缩失败不破坏会话

压缩流程必须是事务式的。只有新摘要生成成功、新 ADK session 创建成功后，才更新 `chat_sessions.adk_session_id` 和压缩元数据。

## 配置项

建议新增环境变量：

```env
# [可选] 是否启用上下文自动压缩
CONTEXT_COMPACTION_ENABLED=true

# [可选] 默认模型上下文窗口 token 数，用于无法从模型配置获取时兜底
CONTEXT_WINDOW_TOKENS=128000

# [可选] 达到上下文窗口多少比例时自动压缩
CONTEXT_COMPACT_TRIGGER_RATIO=0.75

# [可选] 压缩后的目标比例
CONTEXT_COMPACT_TARGET_RATIO=0.35

# [可选] 压缩后保留最近多少轮原始对话
CONTEXT_RECENT_TURNS=12

# [可选] 最近原文 token 预算
CONTEXT_RECENT_TOKEN_BUDGET=20000

# [可选] 旧工具结果进入压缩提示时的最大字符数
CONTEXT_TOOL_RESULT_MAX_CHARS=4000

# [可选] 摘要本身最大 token 预算
CONTEXT_SUMMARY_TOKEN_BUDGET=12000
```

默认建议：

| 配置 | 默认值 | 说明 |
|------|--------|------|
| `CONTEXT_COMPACTION_ENABLED` | `true` | 默认启用 |
| `CONTEXT_WINDOW_TOKENS` | `128000` | 未知模型上下文时的保守值 |
| `CONTEXT_COMPACT_TRIGGER_RATIO` | `0.75` | 75% 触发，留出安全 buffer |
| `CONTEXT_COMPACT_TARGET_RATIO` | `0.35` | 压缩后尽量降到 35% |
| `CONTEXT_RECENT_TURNS` | `12` | 保留最近 12 轮 |
| `CONTEXT_RECENT_TOKEN_BUDGET` | `20000` | 最近原文最多约 20k token |
| `CONTEXT_TOOL_RESULT_MAX_CHARS` | `4000` | 老工具结果摘要输入裁剪 |

## 数据模型

### 修改 `chat_sessions`

新增字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `context_summary` | Text, nullable | 当前会话压缩摘要 |
| `summary_until_message_id` | String(36), nullable | 摘要覆盖到哪条消息 |
| `context_compressed_at` | DateTime, nullable | 最近一次压缩时间 |
| `context_version` | Integer, default 0 | 压缩版本号 |
| `last_context_tokens` | Integer, nullable | 最近一次估算上下文 token |

### 新增 `context_compactions`

用于审计和排障。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String(36) PK | UUID |
| `session_id` | String(36) FK | Web 会话 ID |
| `old_adk_session_id` | String(36) | 压缩前 ADK session |
| `new_adk_session_id` | String(36), nullable | 压缩后 ADK session |
| `before_tokens` | Integer | 压缩前估算 token |
| `after_tokens` | Integer, nullable | 压缩后估算 token |
| `summary_message_id` | String(36), nullable | 摘要覆盖到的消息 |
| `trigger_type` | String(20) | `auto` / `manual` / `error_recovery` |
| `status` | String(20) | `running` / `success` / `failed` |
| `error` | Text, nullable | 失败原因 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

## 核心服务

新增 `server/services/context_compaction.py`。

建议对外提供：

```python
async def get_context_status(db: AsyncSession, user: User, session_id: str) -> ContextStatus:
    ...

async def maybe_compact_before_run(
    db: AsyncSession,
    user: User,
    chat_session: ChatSession,
    pending_user_content: str,
    trigger: str = "auto",
) -> CompactionResult | None:
    ...

async def compact_session(
    db: AsyncSession,
    user: User,
    chat_session: ChatSession,
    trigger: str,
    instruction: str = "",
) -> CompactionResult:
    ...
```

## Token 估算

第一阶段可以沿用现有 `_estimate_tokens()` 的字节估算法，并增加结构化估算：

```text
system/root instruction 估算
+ context_summary 估算
+ 最近消息估算
+ 工具调用摘要估算
+ 当前用户消息估算
+ 安全余量
```

后续可接入模型 provider 的 tokenizer 或统一 token counter。

估算策略：

- 普通文本：UTF-8 字节数 / 4。
- 图片：按固定成本估算，或按压缩后大小估算。
- 工具调用：工具名 + 参数 + 裁剪后的结果。
- `parts` 优先于 legacy `tool_calls` 和 `thinking`。
- 对超过 `CONTEXT_TOOL_RESULT_MAX_CHARS` 的工具结果，估算时只取前后片段和摘要提示。

## 自动触发流程

### 正常自动压缩

```text
用户发送消息
  ↓
读取 chat_session 和 messages
  ↓
估算上下文 tokens
  ↓
tokens < trigger_limit：正常进入 ADK Runner
  ↓
tokens >= trigger_limit：触发 compact_session(trigger="auto")
  ↓
生成摘要
  ↓
创建新 ADK session
  ↓
注入摘要和最近消息
  ↓
更新 chat_session.adk_session_id
  ↓
继续处理本轮用户消息
```

### 上游爆上下文后的恢复

如果上游已经返回 context overflow：

```text
runner.run_async 抛 context overflow
  ↓
捕获错误
  ↓
compact_session(trigger="error_recovery")
  ↓
成功后用新 ADK session 重试当前用户消息一次
  ↓
仍失败则返回明确错误
```

注意：重试只能一次，避免循环烧 token。

## 手动触发流程

### API

```http
GET  /api/v1/chat/sessions/{session_id}/context-status
POST /api/v1/chat/sessions/{session_id}/compact
```

请求：

```json
{
  "instruction": "保留部署、Gitea PR 和服务器操作相关的信息"
}
```

响应：

```json
{
  "status": "success",
  "before_tokens": 98000,
  "after_tokens": 31000,
  "context_version": 3,
  "summary_until_message_id": "..."
}
```

### 前端

第一阶段可以放在聊天页菜单：

- `压缩当前上下文`
- `查看上下文状态`

后续接入前端命令工具：

```text
/compact
/compact 保留 Gitea 和本地设备操作细节
/context
```

## 摘要提示词

压缩摘要不是普通聊天总结，而是 Agent handoff。建议模板：

```text
你正在为一个长期运行的 AI 运维 Agent 会话生成压缩上下文。

目标：
- 用尽量少的 token 保留后续继续对话和执行任务所需的信息。
- 不要遗漏用户目标、关键事实、约束、未完成任务、工具调用结论。
- 不要输出完整密钥、Token、密码或 Secret。
- 工具调用结果只保留结论、关键字段和错误信息。
- 对大日志、大 JSON、大文件内容进行摘要。

请按以下结构输出：

# 会话压缩摘要

## 用户目标

## 已完成事项

## 当前正在做的事

## 关键事实和约束

## 已配置的外部服务和状态

## 本地设备 / 仓库 / 文件上下文

## 重要工具调用结论

## 未完成任务

## 风险和注意事项

## 最近用户偏好
```

## 新 ADK session 注入方式

压缩成功后，不尝试直接改写 ADK 内部旧 history，而是创建新的 ADK session。

新 session 的第一段上下文建议作为用户消息或 state 中的专用字段注入：

```text
以下是此前长会话的压缩摘要。你必须基于它延续上下文：

{context_summary}

以下是最近保留的原始对话片段：

{recent_messages}
```

然后再处理当前用户消息。

这样做的好处：

- 不依赖 ADK 内部 history rewrite API。
- 实现简单。
- 失败可回滚。
- 完整历史仍由 `messages` 表保存。

## 最近消息保留策略

压缩后保留最近消息原文，用于避免摘要丢失细节。

建议选择规则：

1. 从最新消息倒序收集。
2. 最多 `CONTEXT_RECENT_TURNS` 轮。
3. 不超过 `CONTEXT_RECENT_TOKEN_BUDGET`。
4. 如果最后一条 assistant 还在 `generating`，不要压缩。
5. 当前用户消息永远不进入旧历史摘要，而是在压缩后作为新请求发送。

## 工具结果裁剪策略

对旧工具结果进入摘要 prompt 前做预处理：

| 类型 | 策略 |
|------|------|
| 普通短结果 | 原样保留 |
| 长文本 | 保留开头、结尾和长度说明 |
| JSON | 尝试提取顶层 key、错误码、状态、关键字段 |
| 日志 | 保留错误行、最后 N 行、命令和退出状态 |
| 文件内容 | 保留路径、文件类型、摘要，不保留全文 |
| 图片 | 保留描述、mime type、大小，不保留 base64 |
| 密钥 | 脱敏 |

## 并发和一致性

压缩需要防止同一会话并发执行。

建议：

- `context_compactions` 中 `status=running` 作为轻量锁。
- 同一 `session_id` 同时只能有一个 running compaction。
- `stream_response` 发现已有 running compaction 时等待短时间或返回“正在压缩上下文”。
- 压缩成功后 `context_version += 1`。
- 更新 `chat_sessions.adk_session_id` 时检查旧值，避免覆盖其他写入。

## 失败兜底

压缩本身也可能因为输入太长失败。建议分级降级：

### Level 1：正常压缩

旧历史摘要 + 最近消息原文。

### Level 2：去掉旧工具结果全文

只保留工具名、参数摘要、状态和关键错误。

### Level 3：分块摘要

按时间把旧历史分块，先生成多个小摘要，再合并成总摘要。

### Level 4：强制降级

只保留：

- 已有 `context_summary`
- 最近 N 轮消息
- 当前用户消息

并向前端返回 warning：

```json
{
  "event": "warning",
  "message": "历史过长，已使用降级压缩策略，仅保留最近上下文。"
}
```

## 与现有代码的集成点

### 后端

新增：

- `server/models/context_compaction.py`
- `server/schemas/context_compaction.py`
- `server/services/context_compaction.py`
- `server/routers/context_compaction.py` 或并入 `server/routers/chat.py`
- Alembic migration

修改：

- `server/models/chat_session.py`
- `server/schemas/chat.py`
- `server/services/chat.py`
- `server/config.py`
- `.env.example`

### 前端

新增：

- 上下文状态展示。
- 会话菜单中的“压缩上下文”。
- 未来接入 `/compact` 命令。

修改：

- `web/src/lib/api.ts`
- `web/src/hooks/useChat.ts`
- `web/src/components/chat/ChatArea.tsx`
- i18n 文案。

## 实施阶段

### Phase 1：手动压缩

- 增加数据库字段和审计表。
- 实现 `POST /compact`。
- 实现结构化摘要。
- 压缩成功后创建新 ADK session。
- 前端菜单手动触发。

### Phase 2：自动压缩

- 每轮 `stream_response` 前估算上下文。
- 超阈值自动压缩。
- 前端提示“已自动压缩上下文”。
- 记录 `context_compactions`。

### Phase 3：错误恢复

- 捕获 context overflow。
- 自动压缩并重试当前消息一次。
- 失败时返回清晰错误和建议。

### Phase 4：命令和可视化

- 接入 `/compact`。
- 接入 `/context`。
- 展示当前估算 tokens、压缩版本、最近压缩时间。

### Phase 5：高级优化

- 模型级 tokenizer。
- 分块摘要。
- 针对工具结果的结构化摘要器。
- 不同 Agent 的摘要模板。
- 对 SKILL、协作组、设备选择做专用状态保留。

