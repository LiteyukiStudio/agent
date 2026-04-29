/**
 * Ink React TUI 主界面
 */
import React, { useState, useEffect, useCallback } from "react";
import { Box, Text, useInput, useApp } from "ink";
import TextInput from "ink-text-input";
import {
  connect,
  disconnect,
  setEvents,
  type ConnectionStatus,
} from "./connection.js";
import { getConfig, setConnection, clearConnection, getConfigPath } from "./config.js";
import {
  browserLogin,
  deviceLogin,
  getDeviceName,
  normalizeUrl,
  wsUrl,
  type LoginResult,
} from "./auth.js";
import { getDeviceId } from "./config.js";
import { checkUpdate } from "./update.js";
import type { ToolRequest, ToolResponse } from "./tools.js";

import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const pkg = require("../package.json") as { version: string };
const VERSION = pkg.version;

const DEFAULT_SERVER = "https://flow.liteyuki.org";

interface LogEntry {
  time: string;
  type: "info" | "success" | "error" | "request" | "response" | "warn";
  message: string;
}

function timestamp(): string {
  return new Date().toLocaleTimeString("zh-CN", { hour12: false });
}

/** 从 base URL + token + deviceId + deviceName 构建完整 WS 连接地址 */
function buildWsUrl(baseUrl: string, token: string): string {
  const deviceId = getDeviceId();
  const deviceName = getDeviceName();
  return wsUrl(baseUrl, `/ws/local-agent?token=${encodeURIComponent(token)}&device_id=${encodeURIComponent(deviceId)}&device_name=${encodeURIComponent(deviceName)}`);
}

export function App() {
  const { exit } = useApp();
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [input, setInput] = useState("");
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [pendingConfirm, setPendingConfirm] = useState<{
    request: ToolRequest;
    approve: () => void;
    reject: () => void;
  } | null>(null);

  const addLog = useCallback(
    (type: LogEntry["type"], message: string) => {
      setLogs((prev) => [...prev.slice(-50), { time: timestamp(), type, message }]);
    },
    []
  );

  // Setup connection events
  useEffect(() => {
    setEvents({
      onStatusChange: (s, msg) => {
        setStatus(s);
        if (s === "connected") addLog("success", "Connected to server");
        else if (s === "error") addLog("error", `Connection error: ${msg}`);
        else if (s === "disconnected") addLog("info", "Disconnected");
      },
      onRequest: (req) => {
        addLog("request", `\u2190 ${req.tool}(${JSON.stringify(req.args).slice(0, 80)})`);
      },
      onResponse: (res) => {
        if (res.error) {
          addLog("error", `\u2192 Error: ${res.error.slice(0, 100)}`);
        } else {
          addLog("response", `\u2192 OK (${res.result?.length || 0} chars)`);
        }
      },
      onConfirmRequired: (req, approve, reject) => {
        setPendingConfirm({ request: req, approve, reject });
        addLog("warn", `\u26a0 Dangerous command: ${(req.args.command as string).slice(0, 80)}`);
      },
    });

    // Auto-connect if configured
    const cfg = getConfig();
    if (cfg.baseUrl && cfg.token && cfg.autoConnect) {
      addLog("info", `Auto-connecting as "${getDeviceName()}" to ${cfg.baseUrl}...`);
      const url = buildWsUrl(cfg.baseUrl, cfg.token);
      connect(url, cfg.token);
    } else {
      addLog("info", 'Type "/login" to authenticate, or "/help" for commands');
    }

    // 启动时检查更新
    checkUpdate(VERSION).then((update) => {
      if (update) {
        addLog("warn", `New version available: ${update.current} → ${update.latest}`);
        addLog("warn", `Run: ${update.command}`);
      }
    });
  }, [addLog]);

  // Handle confirmation with y/n keys
  useInput((ch, key) => {
    if (pendingConfirm) {
      if (ch === "y" || ch === "Y") {
        pendingConfirm.approve();
        setPendingConfirm(null);
      } else if (ch === "n" || ch === "N" || key.escape) {
        pendingConfirm.reject();
        setPendingConfirm(null);
        addLog("info", "Operation rejected by user");
      }
    }
  });

  /** 连接到服务器 */
  function doConnect(baseUrl: string, token: string) {
    const url = buildWsUrl(baseUrl, token);
    setConnection(baseUrl, token);
    addLog("info", `Connecting as "${getDeviceName()}" to ${baseUrl}...`);
    connect(url, token);
  }

  async function handleLogin(serverUrl: string, useDeviceCode: boolean = false) {
    setIsLoggingIn(true);
    const base = normalizeUrl(serverUrl);
    addLog("info", `Authenticating as "${getDeviceName()}" with ${base}...`);

    let result: LoginResult | null = null;

    if (useDeviceCode) {
      addLog("info", "Using device code mode...");
      result = await deviceLogin(base, (msg) => addLog("info", msg));
    } else {
      result = await browserLogin(base, (msg) => addLog("info", msg));
    }

    if (result) {
      addLog("success", "Authentication successful! Token saved.");
      doConnect(result.baseUrl, result.token);
    } else {
      addLog("error", "Authentication failed or timed out.");
    }

    setIsLoggingIn(false);
  }

  function handleSubmit(value: string) {
    setInput("");
    const trimmed = value.trim();
    if (!trimmed) return;

    if (trimmed.startsWith("/")) {
      const parts = trimmed.split(/\s+/);
      const cmd = parts[0]!.toLowerCase();

      switch (cmd) {
        case "/login": {
          if (isLoggingIn) {
            addLog("warn", "Already logging in...");
            return;
          }
          const useDevice = parts.includes("--device");
          const serverUrl = parts.find((p, i) => i > 0 && !p.startsWith("--")) || DEFAULT_SERVER;
          handleLogin(serverUrl, useDevice);
          break;
        }

        case "/connect": {
          // /connect <base-url> <token>
          const rawUrl = parts[1];
          const tkn = parts[2];
          if (!rawUrl || !tkn) {
            addLog("error", "Usage: /connect <base-url> <token>");
            addLog("info", "  Example: /connect https://flow.liteyuki.org lys_xxxx");
            return;
          }
          doConnect(normalizeUrl(rawUrl), tkn);
          break;
        }

        case "/disconnect":
          disconnect();
          break;

        case "/status": {
          const cfg = getConfig();
          addLog("info", `Status:     ${status}`);
          addLog("info", `Server:     ${cfg.baseUrl || "(not set)"}`);
          addLog("info", `Device:     ${getDeviceName()}`);
          addLog("info", `Device ID:  ${cfg.deviceId.slice(0, 8)}...`);
          addLog("info", `Token:      ${cfg.token ? cfg.token.slice(0, 8) + "..." : "(not set)"}`);
          addLog("info", `Config:     ${getConfigPath()}`);
          break;
        }

        case "/clear":
          setLogs([]);
          break;

        case "/logout":
        case "/reset":
          clearConnection();
          disconnect();
          addLog("info", "Logged out. Connection config cleared.");
          break;

        case "/quit":
        case "/exit":
          disconnect();
          exit();
          break;

        case "/help":
          addLog("info", "Commands:");
          addLog("info", "  /login [url]            Login via browser (default: flow.liteyuki.org)");
          addLog("info", "  /login [url] --device   Login via device code (no browser)");
          addLog("info", "  /connect <url> <token>  Connect with base URL + token");
          addLog("info", "  /disconnect             Disconnect from server");
          addLog("info", "  /status                 Show connection info");
          addLog("info", "  /logout                 Clear saved credentials");
          addLog("info", "  /clear                  Clear log output");
          addLog("info", "  /quit                   Exit");
          break;

        default:
          addLog("error", `Unknown command: ${cmd}. Type /help`);
      }
    } else {
      addLog("info", "Unknown input. Type /help for commands.");
    }
  }

  const statusColor =
    status === "connected"
      ? "green"
      : status === "connecting"
        ? "yellow"
        : "red";

  const statusIcon =
    status === "connected"
      ? "\u25cf"
      : status === "connecting"
        ? "\u25cc"
        : "\u25cb";

  return (
    <Box flexDirection="column" height={process.stdout.rows || 24}>
      {/* Header */}
      <Box borderStyle="round" borderColor="cyan" paddingX={1}>
        <Text bold color="cyan">
          Liteyuki Local Agent
        </Text>
        <Text> </Text>
        <Text color={statusColor}>
          {statusIcon} {status}
        </Text>
        {isLoggingIn && (
          <>
            <Text> </Text>
            <Text color="yellow">{"\u23f3"} Waiting for browser auth...</Text>
          </>
        )}
      </Box>

      {/* Logs */}
      <Box flexDirection="column" flexGrow={1} paddingX={1}>
        {logs.slice(-15).map((log, i) => (
          <Text key={i}>
            <Text dimColor>{log.time}</Text>
            <Text> </Text>
            <Text
              color={
                log.type === "success"
                  ? "green"
                  : log.type === "error"
                    ? "red"
                    : log.type === "request"
                      ? "cyan"
                      : log.type === "response"
                        ? "blue"
                        : log.type === "warn"
                          ? "yellow"
                          : "white"
              }
            >
              {log.message}
            </Text>
          </Text>
        ))}
      </Box>

      {/* Confirmation prompt */}
      {pendingConfirm && (
        <Box borderStyle="round" borderColor="yellow" paddingX={1}>
          <Text color="yellow" bold>
            {"\u26a0"} Confirm dangerous operation? (y/n):{" "}
          </Text>
          <Text>{(pendingConfirm.request.args.command as string).slice(0, 60)}</Text>
        </Box>
      )}

      {/* Input */}
      <Box borderStyle="round" borderColor="gray" paddingX={1}>
        <Text color="green" bold>
          {"\u276f "}
        </Text>
        <TextInput
          value={input}
          onChange={setInput}
          onSubmit={handleSubmit}
          placeholder={isLoggingIn ? "Waiting for browser..." : "Type /help for commands..."}
        />
      </Box>
    </Box>
  );
}
