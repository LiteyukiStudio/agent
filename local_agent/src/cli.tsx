#!/usr/bin/env node
/**
 * Liteyuki Local Agent - CLI 入口
 *
 * 用法:
 *   liteyuki-agent              交互式模式（Ink TUI）
 *   liteyuki-agent -d           后台模式（headless，适合 systemd/launchd）
 *   liteyuki-agent install      安装为系统服务（macOS launchd / Linux systemd）
 *   liteyuki-agent uninstall    卸载系统服务
 *   liteyuki-agent status       查看服务运行状态
 *   liteyuki-agent version      显示版本号
 *   liteyuki-agent info         显示设备信息
 *   liteyuki-agent logout       清除凭据
 *   liteyuki-agent help         显示帮助
 */
import { platform, homedir, arch, release } from "node:os";
import { existsSync, mkdirSync, writeFileSync, unlinkSync } from "node:fs";
import { join } from "node:path";
import { execSync } from "node:child_process";

import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const pkg = require("../package.json") as { version: string; name: string };

const args = process.argv.slice(2);
const command = args[0];

switch (command) {
  case "-d":
  case "--daemon": {
    const { runDaemon } = await import("./daemon.js");
    runDaemon();
    break;
  }

  case "install":
    installService();
    break;

  case "uninstall":
    uninstallService();
    break;

  case "status":
    showStatus();
    break;

  case "version":
  case "-v":
  case "--version":
    console.log(`${pkg.name} v${pkg.version}`);
    break;

  case "info": {
    const { getDeviceId } = await import("./config.js");
    const { getDeviceName, getOsType } = await import("./auth.js");
    console.log(`Liteyuki Local Agent v${pkg.version}`);
    console.log(`──────────────────────────────`);
    console.log(`Device Name: ${getDeviceName()}`);
    console.log(`Device ID:   ${getDeviceId()}`);
    console.log(`OS Type:     ${getOsType()}`);
    console.log(`Platform:    ${platform()} ${arch()}`);
    console.log(`Kernel:      ${release()}`);
    const { getConfig, getConfigPath } = await import("./config.js");
    const cfg = getConfig();
    console.log(`Server:      ${cfg.baseUrl || "(not configured)"}`);
    console.log(`Token:       ${cfg.token ? cfg.token.slice(0, 8) + "..." : "(not set)"}`);
    console.log(`Config:      ${getConfigPath()}`);
    break;
  }

  case "logout": {
    const { clearConnection } = await import("./config.js");
    clearConnection();
    console.log("✅ Credentials cleared. Run `liteyuki-agent` to login again.");
    break;
  }

  case "help":
  case "-h":
  case "--help":
    printHelp();
    break;

  case undefined:
  default:
    if (command && !["", undefined].includes(command) && command.startsWith("-")) {
      console.error(`Unknown option: ${command}`);
      printHelp();
      process.exit(1);
    }
    // 交互式 TUI 模式
    if (command && command !== "") {
      console.error(`Unknown command: ${command}`);
      printHelp();
      process.exit(1);
    }
    const React = await import("react");
    const { render } = await import("ink");
    const { App } = await import("./app.js");
    render(React.createElement(App));
    break;
}

function printHelp(): void {
  console.log(`
Liteyuki Local Agent v${pkg.version}

Usage: liteyuki-agent [command]

Commands:
  (none)          Start interactive TUI mode
  -d, --daemon    Run in headless daemon mode
  install         Install as system service (auto-start)
  uninstall       Remove system service
  status          Show service status
  info            Show device info and config
  logout          Clear saved credentials
  version, -v     Show version number
  help, -h        Show this help

Examples:
  liteyuki-agent              # Interactive login & connect
  liteyuki-agent -d           # Background mode (after login)
  liteyuki-agent install      # Auto-start on boot
  liteyuki-agent info         # Check device ID and config
`);
}

// ---------------------------------------------------------------------------
// 系统服务安装 / 卸载 / 状态
// ---------------------------------------------------------------------------

function getAgentBin(): string {
  return process.argv[1] || "liteyuki-agent";
}

function showStatus(): void {
  const os = platform();
  if (os === "darwin") {
    const plistPath = getLaunchdPlistPath();
    if (!existsSync(plistPath)) {
      console.log("Service not installed. Run `liteyuki-agent install` to set up.");
      return;
    }
    console.log("Service: installed (macOS launchd)");
    console.log(`Plist:   ${plistPath}`);
    try {
      const output = execSync(`launchctl list | grep ${LAUNCHD_LABEL}`, { encoding: "utf-8" });
      console.log(`Status:  running`);
      console.log(`         ${output.trim()}`);
    } catch {
      console.log(`Status:  not running`);
    }
  } else if (os === "linux") {
    const servicePath = getSystemdServicePath();
    if (!existsSync(servicePath)) {
      console.log("Service not installed. Run `liteyuki-agent install` to set up.");
      return;
    }
    console.log("Service: installed (systemd user)");
    console.log(`Unit:    ${servicePath}`);
    try {
      const output = execSync("systemctl --user is-active liteyuki-local-agent", { encoding: "utf-8" }).trim();
      console.log(`Status:  ${output}`);
    } catch {
      console.log(`Status:  inactive`);
    }
  } else {
    console.log(`Service management not supported on ${os}`);
  }
}

function installService(): void {
  const os = platform();
  if (os === "darwin") {
    installLaunchd();
  } else if (os === "linux") {
    installSystemd();
  } else {
    console.error(`Unsupported platform: ${os}. Only macOS and Linux are supported.`);
    process.exit(1);
  }
}

function uninstallService(): void {
  const os = platform();
  if (os === "darwin") {
    uninstallLaunchd();
  } else if (os === "linux") {
    uninstallSystemd();
  } else {
    console.error(`Unsupported platform: ${os}`);
    process.exit(1);
  }
}

// --- macOS launchd ---

const LAUNCHD_LABEL = "org.liteyuki.local-agent";

function getLaunchdPlistPath(): string {
  return join(homedir(), "Library", "LaunchAgents", `${LAUNCHD_LABEL}.plist`);
}

function installLaunchd(): void {
  const bin = getAgentBin();
  const logDir = join(homedir(), "Library", "Logs", "liteyuki-local-agent");
  mkdirSync(logDir, { recursive: true });

  const plist = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LAUNCHD_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${process.execPath}</string>
        <string>${bin}</string>
        <string>-d</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${join(logDir, "stdout.log")}</string>
    <key>StandardErrorPath</key>
    <string>${join(logDir, "stderr.log")}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>`;

  const plistPath = getLaunchdPlistPath();
  writeFileSync(plistPath, plist);

  try {
    execSync(`launchctl load ${plistPath}`);
    console.log("✅ Service installed and started (macOS launchd)");
    console.log(`   Plist: ${plistPath}`);
    console.log(`   Logs:  ${logDir}/`);
    console.log(`   Stop:  launchctl unload ${plistPath}`);
  } catch (e) {
    console.error("Failed to load service:", e);
  }
}

function uninstallLaunchd(): void {
  const plistPath = getLaunchdPlistPath();
  if (!existsSync(plistPath)) {
    console.log("Service not installed.");
    return;
  }
  try {
    execSync(`launchctl unload ${plistPath}`);
  } catch {
    // May already be unloaded
  }
  unlinkSync(plistPath);
  console.log("✅ Service uninstalled (macOS launchd)");
}

// --- Linux systemd ---

function getSystemdServicePath(): string {
  const configDir = join(homedir(), ".config", "systemd", "user");
  mkdirSync(configDir, { recursive: true });
  return join(configDir, "liteyuki-local-agent.service");
}

function installSystemd(): void {
  const bin = getAgentBin();

  const unit = `[Unit]
Description=Liteyuki Local Agent
After=network.target

[Service]
Type=simple
ExecStart=${process.execPath} ${bin} -d
Restart=on-failure
RestartSec=5
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=default.target
`;

  const servicePath = getSystemdServicePath();
  writeFileSync(servicePath, unit);

  try {
    execSync("systemctl --user daemon-reload");
    execSync("systemctl --user enable liteyuki-local-agent");
    execSync("systemctl --user start liteyuki-local-agent");
    console.log("✅ Service installed and started (systemd user)");
    console.log(`   Unit:   ${servicePath}`);
    console.log("   Status: systemctl --user status liteyuki-local-agent");
    console.log("   Logs:   journalctl --user -u liteyuki-local-agent -f");
    console.log("   Stop:   systemctl --user stop liteyuki-local-agent");
  } catch (e) {
    console.error("Failed to start service:", e);
  }
}

function uninstallSystemd(): void {
  const servicePath = getSystemdServicePath();
  if (!existsSync(servicePath)) {
    console.log("Service not installed.");
    return;
  }
  try {
    execSync("systemctl --user stop liteyuki-local-agent");
    execSync("systemctl --user disable liteyuki-local-agent");
  } catch {
    // May already be stopped
  }
  unlinkSync(servicePath);
  execSync("systemctl --user daemon-reload");
  console.log("✅ Service uninstalled (systemd user)");
}
