/** English translations (default fallback) */
export default {
  // ─── CLI ───
  cli: {
    help: {
      title: "Liteyuki Local Agent",
      usage: "Usage: liteyuki-agent [command] [flags]",
      commands: "Commands:",
      flags: "Flags:",
      examples: "Examples:",
      cmdNone: "(none)          Start interactive TUI mode",
      cmdDaemon: "-d, --daemon    Run in headless daemon mode",
      cmdInstall: "install         Install as system service (auto-start on boot)",
      cmdUninstall: "uninstall       Remove system service",
      cmdStart: "start           Start the background service",
      cmdStop: "stop            Stop the background service",
      cmdRestart: "restart         Restart the background service (useful after update)",
      cmdStatus: "status          Show service status",
      cmdSudoers: "sudoers         Generate passwordless sudo config (for common commands)",
      cmdInfo: "info            Show device info and config",
      cmdLogout: "logout          Clear saved credentials",
      cmdVersion: "version, -v     Show version number",
      cmdHelp: "help, -h        Show this help",
      flagYes: "-y, --yes       Auto-approve all commands (skip confirmation)",
      exInteractive: "liteyuki-agent              # Interactive login & connect",
      exDaemon: "liteyuki-agent -d           # Background mode (after login)",
      exDaemonYes: "liteyuki-agent -d -y        # Background + auto-approve",
      exInstall: "liteyuki-agent install      # Auto-start on boot",
      exRestart: "liteyuki-agent restart      # Restart after update",
      exStop: "liteyuki-agent stop         # Stop background service",
      exInfo: "liteyuki-agent info         # Check device ID and config",
    },
    unknownOption: "Unknown option:",
    unknownCommand: "Unknown command:",
    credentialsCleared: "✅ Credentials cleared. Run `liteyuki-agent` to login again.",
  },

  // ─── Service management ───
  service: {
    notInstalled: "Service not installed. Run `liteyuki-agent install` first.",
    installed: "Service: installed",
    running: "Status:  running",
    notRunning: "Status:  not running",
    stopped: "✅ Service stopped",
    started: "✅ Service started",
    restarted: "✅ Service restarted",
    alreadyRunning: "Service may already be running. Use `liteyuki-agent status` to check.",
    installSuccess: "✅ Service installed and started",
    uninstalled: "✅ Service uninstalled",
    unsupportedPlatform: "Unsupported platform:",
    failedStart: "Failed to start service:",
    failedRestart: "Failed to restart service:",
    notInstalledHint: "Service not installed. Run `liteyuki-agent install` to set up.",
  },

  // ─── Sudoers ───
  sudoers: {
    notApplicable: "sudoers is not applicable on Windows.",
    alreadyRoot: "Already running as root, no sudoers needed.",
    header: "This will create the following sudoers config:",
    file: "File:",
    user: "User:",
    commands: "Commands (NOPASSWD):",
    proceeding: "Requires sudo to write. Proceeding...",
    success: "✅ Sudoers config installed successfully!",
    noPasswordNeeded: "The following commands no longer require password:",
    removeHint: "To remove:",
    failed: "❌ Failed to install sudoers config.",
    ensureSudo: "Make sure you have sudo access and try again.",
  },

  // ─── Connection ───
  connection: {
    connected: "Connected to server",
    disconnected: "Disconnected",
    reconnecting: "Disconnected, will retry...",
    kicked: "Not reconnecting.",
    error: "Connection error:",
    connecting: "Connecting...",
    autoConnecting: "Auto-connecting as \"{name}\" to {url}...",
    manualConnect: "Connecting as \"{name}\" to {url}...",
    loginHint: "Type \"/login\" to authenticate, or \"/help\" for commands",
  },

  // ─── Update ───
  update: {
    available: "New version available: {current} → {latest}",
    run: "Run:",
    changelog: "Changelog:",
  },

  // ─── Daemon ───
  daemon: {
    noCredentials: "No credentials found. Run `liteyuki-agent` interactively first to login.",
    server: "Server:",
    sigint: "Received SIGINT, shutting down...",
    sigterm: "Received SIGTERM, shutting down...",
  },

  // ─── Tool confirmation ───
  confirm: {
    rejected: [
      "⚠️ User rejected this operation. Blocked by security policy.",
      "【STRICTLY FORBIDDEN】You must NOT bypass this restriction in any way, including:",
      "- Using python/node/ruby/perl to indirectly execute system commands",
      "- Using os.system(), subprocess, exec() or similar functions",
      "- Writing commands to a script file then executing it",
      "- Encoding/obfuscating command content",
      "- Splitting the command into multiple steps",
      "If you need to perform the rejected operation, tell the user directly and ask them to run it manually.",
    ].join("\n"),
    dangerous: "⚠ Dangerous command:",
  },

  // ─── Info ───
  info: {
    deviceName: "Device Name:",
    deviceId: "Device ID:",
    osType: "OS Type:",
    platform: "Platform:",
    kernel: "Kernel:",
    server: "Server:",
    token: "Token:",
    config: "Config:",
    notConfigured: "(not configured)",
    notSet: "(not set)",
  },
} as const;
