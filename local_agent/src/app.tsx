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
import { deviceLogin, browserLogin, getHostname, type LoginResult } from "./auth.js";
import type { ToolRequest, ToolResponse } from "./tools.js";

const DEFAULT_SERVER = "https://flow.liteyuki.org";

interface LogEntry {
  time: string;
  type: "info" | "success" | "error" | "request" | "response" | "warn";
  message: string;
}

function timestamp(): string {
  return new Date().toLocaleTimeString("zh-CN", { hour12: false });
}

/** 将 HTTPS URL 转为 WSS URL，附带 hostname */
function toWsUrl(httpUrl: string, token: string, host: string): string {
  const base = httpUrl.replace(/\/+$/, "");
  const wsBase = base.replace(/^http/, "ws");
  return `${wsBase}/ws/local-agent?token=${encodeURIComponent(token)}&hostname=${encodeURIComponent(host)}`;
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
        addLog("request", `← ${req.tool}(${JSON.stringify(req.args).slice(0, 80)})`);
      },
      onResponse: (res) => {
        if (res.error) {
          addLog("error", `→ Error: ${res.error.slice(0, 100)}`);
        } else {
          addLog("response", `→ OK (${res.result?.length || 0} chars)`);
        }
      },
      onConfirmRequired: (req, approve, reject) => {
        setPendingConfirm({ request: req, approve, reject });
        addLog("warn", `⚠ Dangerous command: ${(req.args.command as string).slice(0, 80)}`);
      },
    });

    // Auto-connect if configured
    const cfg = getConfig();
    if (cfg.serverUrl && cfg.token && cfg.autoConnect) {
      const host = cfg.hostname || getHostname();
      addLog("info", `Auto-connecting as "${host}" to ${cfg.serverUrl}...`);
      connect(cfg.serverUrl, cfg.token);
    } else {
      addLog("info", 'Type "/login" to authenticate, or "/help" for commands');
    }
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

  async function handleLogin(serverUrl: string, useDeviceCode: boolean = false) {
    setIsLoggingIn(true);
    const host = getHostname();
    addLog("info", `Authenticating as "${host}" with ${serverUrl}...`);

    let result: LoginResult | null = null;

    if (useDeviceCode) {
      // Device Code 模式（无浏览器环境）
      addLog("info", "Using device code mode...");
      result = await deviceLogin(serverUrl, (msg) => addLog("info", msg));
    } else {
      // 快速浏览器模式（默认）
      result = await browserLogin(serverUrl, (msg) => addLog("info", msg));
    }

    if (result) {
      const wsUrl = toWsUrl(result.serverUrl, result.token, host);
      setConnection(wsUrl, result.token, host);
      addLog("success", "Authentication successful! Token saved.");
      addLog("info", `Connecting as "${host}"...`);
      connect(wsUrl, result.token);
    } else {
      addLog("error", "Authentication failed or timed out.");
    }

    setIsLoggingIn(false);
  }

  function handleSubmit(value: string) {
    setInput("");
    const trimmed = value.trim();
    if (!trimmed) return;

    // Parse commands
    if (trimmed.startsWith("/")) {
      const parts = trimmed.split(/\s+/);
      const cmd = parts[0]!.toLowerCase();

      switch (cmd) {
        case "/login": {
          if (isLoggingIn) {
            addLog("warn", "Already logging in...");
            return;
          }
          // /login [url] [--device]
          const useDevice = parts.includes("--device");
          const serverUrl = parts.find((p, i) => i > 0 && !p.startsWith("--")) || DEFAULT_SERVER;
          handleLogin(serverUrl, useDevice);
          break;
        }

        case "/connect": {
          const url = parts[1];
          const tkn = parts[2];
          if (!url || !tkn) {
            addLog("error", "Usage: /connect <ws-url> <token>");
            return;
          }
          const host = getHostname();
          setConnection(url, tkn, host);
          addLog("info", `Connecting as "${host}" to ${url}...`);
          connect(url, tkn);
          break;
        }

        case "/disconnect":
          disconnect();
          break;

        case "/status": {
          const cfg = getConfig();
          addLog("info", `Status: ${status}`);
          addLog("info", `Server: ${cfg.serverUrl || "(not set)"}`);
          addLog("info", `Token: ${cfg.token ? cfg.token.slice(0, 8) + "..." : "(not set)"}`);
          addLog("info", `Config: ${getConfigPath()}`);
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
          addLog("info", "  /login [url]            Login via browser (fast, default)");
          addLog("info", "  /login [url] --device   Login via device code (no browser)");
          addLog("info", "  /connect <url> <token>  Connect with token directly");
          addLog("info", "  /disconnect             Disconnect from server");
          addLog("info", "  /status                 Show connection status & hostname");
          addLog("info", "  /logout                 Clear saved credentials");
          addLog("info", "  /clear                  Clear log output");
          addLog("info", "  /quit                   Exit");
          break;

        default:
          addLog("error", `Unknown command: ${cmd}. Type /help`);
      }
    } else {
      addLog("info", `Unknown input. Type /help for commands.`);
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
      ? "●"
      : status === "connecting"
        ? "◌"
        : "○";

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
            <Text color="yellow">⏳ Waiting for browser auth...</Text>
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
            ⚠ Confirm dangerous operation? (y/n):{" "}
          </Text>
          <Text>{(pendingConfirm.request.args.command as string).slice(0, 60)}</Text>
        </Box>
      )}

      {/* Input */}
      <Box borderStyle="round" borderColor="gray" paddingX={1}>
        <Text color="green" bold>
          {"❯ "}
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
