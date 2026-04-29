# LiteYuki SRE Agent — 前端

LiteYuki SRE Agent 的 Web 聊天界面，提供多用户登录、AI 对话、管理后台等功能。

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 19 | UI 框架 |
| Vite | 8 | 构建工具 |
| TypeScript | 6 | 类型系统 |
| TailwindCSS | 4 | 样式 |
| shadcn/ui | latest | 组件库（base-ui 底层） |
| lucide-react | latest | 图标 |
| sonner | latest | Toast 通知 |
| react-i18next | latest | 国际化（中/英/日） |
| react-markdown + remark-gfm | latest | Markdown 渲染 |
| react-router | 7 | 路由 |

## 开发

```bash
# 安装依赖（强制 pnpm）
pnpm install

# 启动开发服务器（http://localhost:5173）
pnpm dev

# 生产构建
pnpm build

# 代码检查
pnpm lint
pnpm lint --fix
```

开发模式下，Vite 自动将 `/api` 请求代理到后端 `http://localhost:8000`。

## 页面

| 路由 | 页面 | 权限 |
|------|------|------|
| `/login` | 登录（密码 + OAuth） | 公开 |
| `/` | AI 聊天 | 登录用户 |
| `/settings` | 个人设置（API Token + 用量统计） | 登录用户 |
| `/admin/users` | 用户管理 | admin |
| `/admin/oauth` | OAuth Provider 管理 | admin |
| `/admin/quota` | 配额方案管理 | admin |

## 关键模块

### 认证（useAuth）

- JWT 存储在 localStorage
- `AuthProvider` 在应用启动时自动验证 token
- `ProtectedRoute` 组件守卫需要登录的路由

### 聊天（useChat）

- SSE 流式接收 Agent 响应（逐 token 更新）
- 支持工具调用可视化
- 消息从 API 加载 + 实时追加
- 会话管理（创建/删除/重命名）

### API 层（lib/api.ts）

- `apiGet` / `apiPost` / `apiPatch` / `apiDelete` — 标准 REST 调用
- `streamSSE` — SSE 流式 async generator
- 401 自动清 token，由路由守卫驱动跳转（不硬刷新）

## Docker 部署

```bash
# 从项目根目录构建
docker build -f web/Dockerfile -t liteyuki-sre-frontend .
```

生产环境通过 Nginx 托管静态文件 + 反向代理后端 API。配置文件：`web/nginx.conf`。
