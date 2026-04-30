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
import { t } from "./i18n/index.js";

import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const pkg = require("../package.json") as { version: string; name: string };

const args = process.argv.slice(2);
const command = args[0];
const flags = new Set(args.slice(1));
const yesMode = flags.has("-y") || flags.has("--yes") || args.includes("-y") || args.includes("--yes");

switch (command) {
  case "-d":
  case "--daemon": {
    if (yesMode) {
      const { setAutoApprove } = await import("./connection.js");
      setAutoApprove(true);
    }
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

  case "start":
    startService();
    break;

  case "stop":
    stopService();
    break;

  case "restart":
    restartService();
    break;

  case "status":
    showStatus();
    break;

  case "sudoers":
    setupSudoers();
    break;

  case "version":
  case "-v":
  case "--version":
    console.log(`${pkg.name} v${pkg.version}`);
    break;

  case "info": {
    const { getDeviceId } = await import("./config.js");
    const { getDeviceName, getOsType } = await import("./auth.js");
    console.log(`${t.cli.help.title} v${pkg.version}`);
    console.log(`──────────────────────────────`);
    console.log(`${t.info.deviceName} ${getDeviceName()}`);
    console.log(`${t.info.deviceId}   ${getDeviceId()}`);
    console.log(`${t.info.osType}     ${getOsType()}`);
    console.log(`${t.info.platform}    ${platform()} ${arch()}`);
    console.log(`${t.info.kernel}      ${release()}`);
    const { getConfig, getConfigPath } = await import("./config.js");
    const cfg = getConfig();
    console.log(`${t.info.server}      ${cfg.baseUrl || t.info.notConfigured}`);
    console.log(`${t.info.token}       ${cfg.token ? cfg.token.slice(0, 8) + "..." : t.info.notSet}`);
    console.log(`${t.info.config}      ${getConfigPath()}`);
    break;
  }

  case "logout": {
    const { clearConnection } = await import("./config.js");
    clearConnection();
    console.log(t.cli.credentialsCleared);
    break;
  }

  case "help":
  case "-h":
  case "--help":
    printHelp();
    break;

  case "-y":
  case "--yes":
  case undefined:
  default:
    if (command && !["", undefined, "-y", "--yes"].includes(command) && command.startsWith("-")) {
      console.error(`Unknown option: ${command}`);
      printHelp();
      process.exit(1);
    }
    // 交互式 TUI 模式
    if (command && command !== "" && command !== "-y" && command !== "--yes") {
      console.error(`Unknown command: ${command}`);
      printHelp();
      process.exit(1);
    }
    if (yesMode) {
      const { setAutoApprove } = await import("./connection.js");
      setAutoApprove(true);
    }
    const React = await import("react");
    const { render } = await import("ink");
    const { App } = await import("./app.js");
    render(React.createElement(App));
    break;
}

function printHelp(): void {
  const h = t.cli.help;
  console.log(`
${h.title} v${pkg.version}

${h.usage}

${h.commands}
  ${h.cmdNone}
  ${h.cmdDaemon}
  ${h.cmdInstall}
  ${h.cmdUninstall}
  ${h.cmdStart}
  ${h.cmdStop}
  ${h.cmdRestart}
  ${h.cmdStatus}
  ${h.cmdSudoers}
  ${h.cmdInfo}
  ${h.cmdLogout}
  ${h.cmdVersion}
  ${h.cmdHelp}

${h.flags}
  ${h.flagYes}

${h.examples}
  ${h.exInteractive}
  ${h.exDaemon}
  ${h.exDaemonYes}
  ${h.exInstall}
  ${h.exRestart}
  ${h.exStop}
  ${h.exInfo}
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
      console.log(t.service.notInstalledHint);
      return;
    }
    console.log(`${t.service.installed} (macOS launchd)`);
    console.log(`Plist:   ${plistPath}`);
    try {
      const output = execSync(`launchctl list | grep ${LAUNCHD_LABEL}`, { encoding: "utf-8" });
      console.log(t.service.running);
      console.log(`         ${output.trim()}`);
    } catch {
      console.log(t.service.notRunning);
    }
  } else if (os === "linux") {
    const servicePath = getSystemdServicePath();
    if (!existsSync(servicePath)) {
      console.log(t.service.notInstalledHint);
      return;
    }
    console.log(`${t.service.installed} (systemd user)`);
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

function stopService(): void {
  const os = platform();
  if (os === "darwin") {
    const plistPath = getLaunchdPlistPath();
    if (!existsSync(plistPath)) {
      console.log(t.service.notInstalled);
      return;
    }
    try {
      execSync(`launchctl unload ${plistPath}`);
      console.log(t.service.stopped);
    } catch {
      console.log(t.service.notRunning);
    }
  } else if (os === "linux") {
    try {
      execSync("systemctl --user stop liteyuki-local-agent");
      console.log(t.service.stopped);
    } catch {
      console.log(t.service.notRunning);
    }
  } else {
    console.error(`${t.service.unsupportedPlatform} ${os}`);
  }
}

function startService(): void {
  const os = platform();
  if (os === "darwin") {
    const plistPath = getLaunchdPlistPath();
    if (!existsSync(plistPath)) {
      console.log(t.service.notInstalled);
      return;
    }
    try {
      execSync(`launchctl load ${plistPath}`);
      console.log(t.service.started);
    } catch {
      console.log(t.service.alreadyRunning);
    }
  } else if (os === "linux") {
    try {
      execSync("systemctl --user start liteyuki-local-agent");
      console.log(t.service.started);
    } catch (e) {
      console.error(t.service.failedStart, e);
    }
  } else {
    console.error(`${t.service.unsupportedPlatform} ${os}`);
  }
}

function restartService(): void {
  const os = platform();
  if (os === "darwin") {
    const plistPath = getLaunchdPlistPath();
    if (!existsSync(plistPath)) {
      console.log(t.service.notInstalled);
      return;
    }
    try {
      execSync(`launchctl unload ${plistPath}`);
    } catch {
      // May not be loaded
    }
    try {
      execSync(`launchctl load ${plistPath}`);
      console.log(t.service.restarted);
    } catch (e) {
      console.error(t.service.failedRestart, e);
    }
  } else if (os === "linux") {
    try {
      execSync("systemctl --user restart liteyuki-local-agent");
      console.log(t.service.restarted);
    } catch (e) {
      console.error(t.service.failedRestart, e);
    }
  } else {
    console.error(`${t.service.unsupportedPlatform} ${os}`);
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
    console.log(`${t.service.installSuccess} (macOS launchd)`);
    console.log(`   Plist: ${plistPath}`);
    console.log(`   Logs:  ${logDir}/`);
    console.log(`   Stop:  launchctl unload ${plistPath}`);
  } catch (e) {
    console.error(t.service.failedStart, e);
  }
}

function uninstallLaunchd(): void {
  const plistPath = getLaunchdPlistPath();
  if (!existsSync(plistPath)) {
    console.log(t.service.notInstalledHint);
    return;
  }
  try {
    execSync(`launchctl unload ${plistPath}`);
  } catch {
    // May already be unloaded
  }
  unlinkSync(plistPath);
  console.log(`${t.service.uninstalled} (macOS launchd)`);
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
    console.log(`${t.service.installSuccess} (systemd user)`);
    console.log(`   Unit:   ${servicePath}`);
    console.log("   Status: systemctl --user status liteyuki-local-agent");
    console.log("   Logs:   journalctl --user -u liteyuki-local-agent -f");
    console.log("   Stop:   systemctl --user stop liteyuki-local-agent");
  } catch (e) {
    console.error(t.service.failedStart, e);
  }
}

function uninstallSystemd(): void {
  const servicePath = getSystemdServicePath();
  if (!existsSync(servicePath)) {
    console.log(t.service.notInstalledHint);
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
  console.log(`${t.service.uninstalled} (systemd user)`);
}

// ---------------------------------------------------------------------------
// sudoers 免密配置（方案 B：高级用户可选）
// ---------------------------------------------------------------------------

const SUDOERS_FILE = "/etc/sudoers.d/liteyuki-agent";
const SUDOERS_COMMANDS = [
  "/usr/bin/apt",
  "/usr/bin/apt-get",
  "/usr/bin/dnf",
  "/usr/bin/yum",
  "/usr/bin/pacman",
  "/usr/bin/systemctl",
  "/usr/bin/docker",
  "/usr/bin/journalctl",
  "/usr/sbin/service",
  "/usr/bin/snap",
  "/usr/bin/flatpak",
];

function setupSudoers(): void {
  const os = platform();
  if (os === "win32") {
    console.error("sudoers is not applicable on Windows.");
    process.exit(1);
  }

  const user = process.env.USER || process.env.LOGNAME || "unknown";
  if (user === "root") {
    console.log("Already running as root, no sudoers needed.");
    return;
  }

  const commands = SUDOERS_COMMANDS.join(", ");
  const content = `# Generated by liteyuki-agent sudoers\n# Allows ${user} to run common admin commands without password\n${user} ALL=(ALL) NOPASSWD: ${commands}\n`;

  console.log("This will create the following sudoers config:");
  console.log(`──────────────────────────────`);
  console.log(`File: ${SUDOERS_FILE}`);
  console.log(`User: ${user}`);
  console.log(`Commands (NOPASSWD):`);
  for (const cmd of SUDOERS_COMMANDS) {
    console.log(`  ${cmd}`);
  }
  console.log(`──────────────────────────────`);
  console.log("\nRequires sudo to write. Proceeding...\n");

  try {
    // 用 tee 写入（需要 sudo 权限）
    execSync(`echo '${content}' | sudo tee ${SUDOERS_FILE} > /dev/null`, {
      stdio: ["inherit", "pipe", "pipe"],
      encoding: "utf-8",
    });
    execSync(`sudo chmod 0440 ${SUDOERS_FILE}`, { stdio: "pipe" });
    // 验证语法
    execSync(`sudo visudo -c -f ${SUDOERS_FILE}`, { stdio: "pipe" });
    console.log("✅ Sudoers config installed successfully!");
    console.log(`   File: ${SUDOERS_FILE}`);
    console.log(`   The following commands no longer require password:`);
    for (const cmd of SUDOERS_COMMANDS) {
      console.log(`     sudo ${cmd.split("/").pop()} ...`);
    }
    console.log("\n   To remove: sudo rm " + SUDOERS_FILE);
  } catch (e) {
    console.error("❌ Failed to install sudoers config.");
    console.error("   Make sure you have sudo access and try again.");
    if (e instanceof Error) {
      console.error(`   Error: ${e.message}`);
    }
  }
}
