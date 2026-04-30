# Liteyuki Local Agent

连接 [Liteyuki Flow](https://flow.liteyuki.org) 云端 Agent，在本地电脑上执行命令和文件操作。

## 安装

### 方式一：npm / pnpm（需要 Node.js）

```bash
npm install -g liteyuki-local-agent
# 或
pnpm add -g liteyuki-local-agent
```

### 方式二：二进制文件（推荐，零依赖）

从 [Releases](https://github.com/LiteyukiStudio/agent/releases) 下载对应平台的可执行文件：

| 平台 | 文件 |
|------|------|
| macOS (Apple Silicon) | `liteyuki-agent-darwin-arm64` |
| macOS (Intel) | `liteyuki-agent-darwin-x64` |
| Linux (x64) | `liteyuki-agent-linux-x64` |
| Linux (ARM64) | `liteyuki-agent-linux-arm64` |
| Windows (x64) | `liteyuki-agent-win-x64.exe` |

下载后赋予执行权限即可使用：

```bash
chmod +x liteyuki-agent-darwin-arm64
./liteyuki-agent-darwin-arm64
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
liteyuki-agent uninstall  # 卸载服务
```

### 服务管理

```bash
liteyuki-agent start      # 启动后台服务
liteyuki-agent stop       # 停止后台服务
liteyuki-agent restart    # 重启服务（更新后使用）
liteyuki-agent status     # 查看服务状态
```

### 更新

```bash
# npm 用户
npm install -g liteyuki-local-agent@latest
liteyuki-agent restart

# pnpm 用户
pnpm add -g liteyuki-local-agent@latest
liteyuki-agent restart
```

启动时会自动检测新版本并显示 changelog。

## CLI 命令参考

```
Usage: liteyuki-agent [command] [flags]

Commands:
  (none)          交互式 TUI 模式
  -d, --daemon    后台 daemon 模式（无 TUI）
  install         安装为系统服务（开机自启）
  uninstall       卸载系统服务
  start           启动后台服务
  stop            停止后台服务
  restart         重启后台服务（更新后使用）
  status          查看服务运行状态
  info            显示设备信息和配置
  logout          清除已保存的凭据
  version, -v     显示版本号
  help, -h        显示帮助

Flags:
  -y, --yes       自动同意所有命令（跳过危险操作确认）
```

### TUI 交互命令

| 命令 | 说明 |
|------|------|
| `/login [url]` | 浏览器授权登录 |
| `/login [url] --device` | 设备码登录（无浏览器环境） |
| `/connect <url> <token>` | 直接用 token 连接 |
| `/disconnect` | 断开连接 |
| `/status` | 查看连接状态 |
| `/logout` | 清除凭据 |
| `/help` | 帮助 |
| `/quit` | 退出 |

## 安全机制

### 危险命令审批

AI 触发以下类型的命令时，需要用户在 **Web 前端** 确认后才会执行：

- 系统级操作：`rm -rf`、`sudo`、`shutdown`、`reboot`、`kill -9` 等
- 文件系统变更：`chmod 777`、`chown`、`mkfs`、`dd` 等
- 脚本执行：`python -c`、`node -e`、`curl | sh` 等
- 防 AI 绕过：`os.system()`、`subprocess.run()`、`shutil.rmtree()` 等

审批选项：
- **拒绝** — 阻止执行，AI 收到禁止绕过的严格提示
- **允许** — 本次执行
- **始终允许** — 该会话内相同命令不再询问

使用 `-y` 标志可跳过所有确认（仅建议在受信环境使用）。

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

- 本地 Agent 主动连接云端（无需公网 IP、无需开端口）
- 云端 AI 通过 WebSocket 下发操作指令
- 每 10 秒双向心跳保活，确保连接不被中间代理断开
- 危险命令通过 Web 前端审批（不再依赖终端交互）
- 支持同一账号连接多设备，AI 可指定目标设备执行
- 每个设备报告版本号，Web 端可查看并提示更新

## License

MIT
