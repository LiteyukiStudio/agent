/**
 * Headless 后台模式：无 TUI，纯日志输出，适合 systemd/launchd
 */
import { createRequire } from "node:module";
import { getConfig, getDeviceId } from "./config.js";
import { connect, disconnect, setEvents } from "./connection.js";
import { getDeviceName, getOsType, wsUrl } from "./auth.js";
import { t } from "./i18n/index.js";

const require = createRequire(import.meta.url);
const pkg = require("../package.json") as { version: string };

function log(level: string, msg: string): void {
  const ts = new Date().toISOString();
  console.log(`${ts} [${level}] ${msg}`);
}

export function runDaemon(): void {
  const cfg = getConfig();

  if (!cfg.baseUrl || !cfg.token) {
    log("ERROR", t.daemon.noCredentials);
    process.exit(1);
  }

  const deviceId = getDeviceId();
  const deviceName = getDeviceName();
  log("INFO", `Liteyuki Local Agent (daemon) - ${deviceName} [${deviceId.slice(0, 8)}]`);
  log("INFO", `${t.daemon.server} ${cfg.baseUrl}`);

  setEvents({
    onStatusChange: (status, msg) => {
      if (status === "connected") log("INFO", t.connection.connected);
      else if (status === "error") log("ERROR", `${t.connection.error} ${msg}`);
      else if (status === "disconnected") {
        if (msg) log("WARN", msg);
        else log("WARN", t.connection.reconnecting);
      }
    },
    onRequest: (req) => {
      log("INFO", `<- ${req.tool}(${JSON.stringify(req.args).slice(0, 200)})`);
    },
    onResponse: (res) => {
      if (res.error) {
        log("ERROR", `-> Error: ${res.error.slice(0, 200)}`);
      } else {
        log("INFO", `-> OK (${res.result?.length || 0} chars)`);
      }
    },
  });

  const os = getOsType();
  const fullWsUrl = wsUrl(
    cfg.baseUrl,
    `/ws/local-agent?token=${encodeURIComponent(cfg.token)}&device_id=${encodeURIComponent(deviceId)}&device_name=${encodeURIComponent(deviceName)}&os=${encodeURIComponent(os)}&version=${encodeURIComponent(pkg.version)}`,
  );

  log("INFO", t.connection.connecting);
  connect(fullWsUrl, cfg.token);

  process.on("SIGINT", () => {
    log("INFO", t.daemon.sigint);
    disconnect();
    process.exit(0);
  });

  process.on("SIGTERM", () => {
    log("INFO", t.daemon.sigterm);
    disconnect();
    process.exit(0);
  });
}
