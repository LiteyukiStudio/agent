/** 简体中文翻译 */
export default {
  // ─── CLI ───
  cli: {
    help: {
      title: "轻雪本地代理",
      usage: "用法: liteyuki-agent [命令] [选项]",
      commands: "命令:",
      flags: "选项:",
      examples: "示例:",
      cmdNone: "(无)            启动交互式 TUI 模式",
      cmdDaemon: "-d, --daemon    后台守护进程模式（无 TUI）",
      cmdInstall: "install         安装为系统服务（开机自启）",
      cmdUninstall: "uninstall       卸载系统服务",
      cmdStart: "start           启动后台服务",
      cmdStop: "stop            停止后台服务",
      cmdRestart: "restart         重启后台服务（更新后使用）",
      cmdStatus: "status          查看服务状态",
      cmdSudoers: "sudoers         生成免密 sudo 配置（常用命令）",
      cmdUpdate: "update          更新到最新版本",
      cmdInfo: "info            显示设备信息和配置",
      cmdLogout: "logout          清除已保存的凭据",
      cmdVersion: "version, -v     显示版本号",
      cmdHelp: "help, -h        显示此帮助",
      flagYes: "-y, --yes       自动同意所有命令（跳过危险操作确认）",
      exInteractive: "liteyuki-agent              # 交互式登录连接",
      exDaemon: "liteyuki-agent -d           # 后台运行（需先登录）",
      exDaemonYes: "liteyuki-agent -d -y        # 后台 + 自动同意所有操作",
      exInstall: "liteyuki-agent install      # 开机自启",
      exRestart: "liteyuki-agent restart      # 更新后重启",
      exStop: "liteyuki-agent stop         # 停止后台服务",
      exInfo: "liteyuki-agent info         # 查看设备信息",
    },
    unknownOption: "未知选项:",
    unknownCommand: "未知命令:",
    credentialsCleared: "✅ 凭据已清除。运行 `liteyuki-agent` 重新登录。",
  },

  // ─── 服务管理 ───
  service: {
    notInstalled: "服务未安装。请先运行 `liteyuki-agent install`。",
    installed: "服务: 已安装",
    running: "状态:  运行中",
    notRunning: "状态:  未运行",
    stopped: "✅ 服务已停止",
    started: "✅ 服务已启动",
    restarted: "✅ 服务已重启",
    alreadyRunning: "服务可能已在运行。使用 `liteyuki-agent status` 检查。",
    installSuccess: "✅ 服务已安装并启动",
    uninstalled: "✅ 服务已卸载",
    unsupportedPlatform: "不支持的平台:",
    failedStart: "启动服务失败:",
    failedRestart: "重启服务失败:",
    notInstalledHint: "服务未安装。运行 `liteyuki-agent install` 进行设置。",
  },

  // ─── Sudoers ───
  sudoers: {
    notApplicable: "sudoers 不适用于 Windows。",
    alreadyRoot: "当前已是 root 用户，无需配置 sudoers。",
    header: "即将创建以下 sudoers 配置:",
    file: "文件:",
    user: "用户:",
    commands: "免密命令 (NOPASSWD):",
    proceeding: "需要 sudo 权限写入，继续...",
    success: "✅ Sudoers 配置安装成功！",
    noPasswordNeeded: "以下命令已不再需要密码:",
    removeHint: "删除方式:",
    failed: "❌ Sudoers 配置安装失败。",
    ensureSudo: "请确保你有 sudo 权限后重试。",
  },

  // ─── 自更新 ───
  selfUpdate: {
    checking: "正在检查更新...",
    alreadyLatest: "✅ 已是最新版本",
    updating: "正在更新到",
    channel: "安装渠道:",
    success: "✅ 更新成功！请重启 agent。",
    restartHint: "运行: liteyuki-agent restart",
    failed: "❌ 更新失败:",
    unknownChannel: "无法检测安装渠道，请手动更新:",
  },

  // ─── 连接 ───
  connection: {
    connected: "已连接到服务器",
    disconnected: "已断开连接",
    reconnecting: "已断开，将重试...",
    kicked: "不再重连。",
    error: "连接错误:",
    connecting: "正在连接...",
    autoConnecting: "正在以 \"{name}\" 自动连接到 {url}...",
    manualConnect: "正在以 \"{name}\" 连接到 {url}...",
    loginHint: "输入 /login 进行认证，或 /help 查看帮助",
  },

  // ─── 更新 ───
  update: {
    available: "发现新版本: {current} → {latest}",
    run: "更新命令:",
    changelog: "更新日志:",
  },

  // ─── 守护进程 ───
  daemon: {
    noCredentials: "未找到凭据。请先以交互模式运行 `liteyuki-agent` 完成登录。",
    server: "服务器:",
    sigint: "收到 SIGINT 信号，正在关闭...",
    sigterm: "收到 SIGTERM 信号，正在关闭...",
  },

  // ─── 工具确认 ───
  confirm: {
    rejected: [
      "⚠️ 用户拒绝了此操作。该命令被安全策略拦截。",
      "【严格禁止】你不得通过任何方式绕过此限制，包括但不限于：",
      "- 使用 python/node/ruby/perl 等脚本语言间接执行系统命令",
      "- 使用 os.system()、subprocess、exec() 等函数",
      "- 将命令写入脚本文件再执行",
      "- 编码/混淆命令内容",
      "- 拆分命令为多步执行",
      "如果需要执行被拒绝的操作，请直接告知用户原因并请求用户手动执行。",
    ].join("\n"),
    dangerous: "⚠ 危险命令:",
  },

  // ─── 信息 ───
  info: {
    deviceName: "设备名称:",
    deviceId: "设备 ID:",
    osType: "系统类型:",
    platform: "平台:",
    kernel: "内核:",
    server: "服务器:",
    token: "Token:",
    config: "配置文件:",
    notConfigured: "(未配置)",
    notSet: "(未设置)",
  },
} as const;
