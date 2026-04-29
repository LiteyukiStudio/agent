# Liteyuki Local Agent

连接 [Liteyuki Flow](https://flow.liteyuki.org) 云端 Agent，在本地电脑上执行命令和文件操作。

## 安装

```bash
npm install -g liteyuki-local-agent
```

## 使用

### 首次登录

```bash
liteyuki-agent
```

启动后输入：

```
/login
```

浏览器会自动打开授权页面，确认后自动连接。

如需连接自建实例：

```
/login https://your-server.com
```

无浏览器环境（如 SSH 服务器）：

```
/login --device
```

### 后台运行

登录成功后，后续可直接后台运行：

```bash
liteyuki-agent -d
```

### 开机自启

```bash
liteyuki-agent install    # 安装为系统服务（macOS launchd / Linux systemd）
liteyuki-agent uninstall  # 卸载
```

### 全部命令

| 命令 | 说明 |
|------|------|
| `/login [url]` | 浏览器授权登录 |
| `/login [url] --device` | 设备码登录（无浏览器） |
| `/connect <url> <token>` | 直接用 token 连接 |
| `/disconnect` | 断开连接 |
| `/status` | 查看连接状态 |
| `/logout` | 清除凭据 |
| `/help` | 帮助 |
| `/quit` | 退出 |

## 工作原理

```
本地电脑                              云端
┌──────────────┐    WebSocket    ┌─────────────────┐
│ liteyuki-agent│ ──────────────▶│ flow.liteyuki.org│
│              │◀────────────── │                 │
│ 执行命令     │    指令/结果    │ AI Agent        │
│ 读写文件     │                │                 │
└──────────────┘                └─────────────────┘
```

- 本地 Agent 主动连接云端（无需公网 IP）
- 云端 AI 通过 WebSocket 下发操作指令
- 危险命令需要用户确认
- 支持同一账号多设备连接

## License

MIT
