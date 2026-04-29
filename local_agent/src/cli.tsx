#!/usr/bin/env node
/**
 * Liteyuki Local Agent - CLI 入口
 *
 * 用法:
 *   liteyuki-agent          交互式模式（Ink TUI）
 *   liteyuki-agent -d       后台模式（headless，适合 systemd/launchd）
 *   liteyuki-agent install   安装为系统服务（macOS launchd / Linux systemd）
 *   liteyuki-agent uninstall 卸载系统服务
 */
import { platform, homedir } from "node:os";
import { existsSync, mkdirSync, writeFileSync, unlinkSync } from "node:fs";
import { join } from "node:path";
import { execSync } from "node:child_process";

const args = process.argv.slice(2);
const command = args[0];

if (command === "-d" || command === "--daemon") {
  // Headless 后台模式
  const { runDaemon } = await import("./daemon.js");
  runDaemon();
} else if (command === "install") {
  installService();
} else if (command === "uninstall") {
  uninstallService();
} else {
  // 交互式 TUI 模式
  const React = await import("react");
  const { render } = await import("ink");
  const { App } = await import("./app.js");
  render(React.createElement(App));
}

// ---------------------------------------------------------------------------
// 系统服务安装 / 卸载
// ---------------------------------------------------------------------------

function getAgentBin(): string {
  // 尝试找到当前可执行文件路径
  return process.argv[1] || "liteyuki-agent";
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
