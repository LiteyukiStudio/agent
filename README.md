# Liteyuki Flow

<div align="center">

**智能运维助手 — 让 AI 管理你的基础设施**

[官方实例](https://flow.liteyuki.org) · [接入文档](docs/integration.md) · [Local Agent](local_agent/README.md) · [贡献指南](CONTRIBUTING.md)

</div>

---

## ✨ 简介

Liteyuki Flow 是一个基于多智能体架构的 AI 运维平台，能够通过自然语言对话完成代码仓库管理、服务器操作、消息推送等任务。

支持多用户、多设备、多通道，提供完整的 Web 聊天界面。

## 🚀 体验

> **⚠️ 当前处于内测阶段**

1. 前往 [轻雪通行证](https://pass.liteyuki.org/login/liteyuki-user?orgChoiceMode=None) 注册账户
2. 发送邮件到 **contact@liteyuki.org** 申请内测资格
3. 获批后访问 **https://flow.liteyuki.org** 开始使用

## 🎯 核心能力

| 能力 | 说明 |
|------|------|
| 🤖 多智能体协作 | 根据任务自动调度 Gitea、搜索、推送等专业 Agent |
| 💻 远程设备控制 | 通过 [Local Agent](local_agent/README.md) 在你的电脑上执行命令、读写文件 |
| 📢 多通道推送 | 飞书、企业微信、QQ（OneBot）、邮件、Gotify 通知推送 |
| 🔍 实时搜索 | 联网搜索最新信息，辅助决策 |
| 🔐 多用户隔离 | 每个用户独立凭据，互不可见 |
| 🌐 OAuth 登录 | 支持任意 OIDC 提供商（Gitea、GitHub、Google 等） |

## 📱 功能特性

- **流式对话** — SSE 实时输出，工具调用可视化
- **消息持久化** — 刷新不丢失，生成中断可恢复
- **会话管理** — 自动标题、公开分享、批量操作
- **用量计费** — 可配置配额方案，按日/周/月限制
- **设备管理** — 多设备在线，危险操作 Web 端审批
- **管理后台** — 用户管理、OAuth 配置、配额方案、会话审查
- **国际化** — 中文 / English / 日本語

## 🖥️ Local Agent

在你的电脑上安装 Local Agent，让 AI 能远程操作你的设备：

```bash
# npm
npm install -g liteyuki-local-agent

# 或 pnpm
pnpm add -g liteyuki-local-agent

# 启动并登录
liteyuki-agent
```

详细文档见 [Local Agent README](local_agent/README.md)。

## 🏗️ 自部署

### Docker Compose（推荐）

```bash
git clone https://github.com/LiteyukiStudio/agent.git
cd agent
cp .env.example .env   # 编辑配置
docker compose up -d
```

访问 `http://localhost` 即可使用。

### 最小配置

```env
SECRET_KEY=一个随机字符串
AGENT_TOKEN=你的_llm_api_key
```

> 完整配置项说明见 `.env.example`

## 🔌 第三方接入

支持通过 WebSocket 协议接入自定义 Agent 或应用，详见 [接入文档](docs/integration.md)。

## 🤝 参与开发

欢迎贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解开发环境搭建、代码规范和架构说明。

## 📄 License

MIT
