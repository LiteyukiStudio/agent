/**
 * WebSocket 客户端：反向连接云端，接收并执行指令
 */
import WebSocket from "ws";
import { generateKeyPairSync } from "node:crypto";
import { getConfig } from "./config.js";
import { decryptPassword, executeSudoTool, executeTool, isDangerous, isSensitivePath } from "./tools.js";
import { t } from "./i18n/index.js";
import type { ToolRequest, ToolResponse } from "./tools.js";

export type ConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "error";

export interface ConnectionEvents {
  onStatusChange: (status: ConnectionStatus, message?: string) => void;
  onRequest: (request: ToolRequest) => void;
  onResponse: (response: ToolResponse) => void;
}

let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let pingTimer: ReturnType<typeof setInterval> | null = null;
let shouldReconnect = false;
let currentUrl = "";
let currentToken = "";
let events: ConnectionEvents | null = null;
let autoApprove = false;
const SUDO_PASSWORD_TTL_MS = 5 * 60 * 1000;

export function setAutoApprove(value: boolean): void {
  autoApprove = value;
}

export function setEvents(e: ConnectionEvents): void {
  events = e;
}

export function getStatus(): ConnectionStatus {
  if (!ws) return "disconnected";
  switch (ws.readyState) {
    case WebSocket.CONNECTING:
      return "connecting";
    case WebSocket.OPEN:
      return "connected";
    default:
      return "disconnected";
  }
}

function isToolRequest(value: unknown): value is ToolRequest {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<ToolRequest>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.tool === "string" &&
    !!candidate.args &&
    typeof candidate.args === "object" &&
    !Array.isArray(candidate.args)
  );
}

export function connect(url: string, token: string): void {
  currentUrl = url;
  currentToken = token;
  shouldReconnect = true;
  doConnect();
}

export function disconnect(): void {
  shouldReconnect = false;
  resetSessionApprovals();
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (ws) {
    ws.close();
    ws = null;
  }
  events?.onStatusChange("disconnected");
}

function doConnect(): void {
  if (ws) {
    ws.close();
    ws = null;
  }

  events?.onStatusChange("connecting");

  // currentUrl 已包含所有 query 参数（token, device_id, device_name）
  ws = new WebSocket(currentUrl);

  ws.on("open", () => {
    events?.onStatusChange("connected");
    // 每 10 秒发 ping 保持连接（防止代理/nginx 超时断开）
    if (pingTimer) clearInterval(pingTimer);
    pingTimer = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.ping();
      }
    }, 10000);
  });

  ws.on("message", (data) => {
    try {
      const msg = JSON.parse(data.toString());
      // 应用层心跳：服务端发来 ping，回复 pong
      if (msg.type === "ping") {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "pong" }));
        }
        return;
      }
      // 服务端转发的确认响应（Web 前端审批结果）
      if (msg.type === "confirm_response") {
        handleConfirmResponse(msg.id, msg.approved, msg.always, msg.password, msg.encrypted_password);
        return;
      }
      if (!isToolRequest(msg)) return;
      const request = msg;
      events?.onRequest(request);
      void handleRequest(request);
    } catch (err) {
      // ignore malformed messages
    }
  });

  ws.on("close", (code, reason) => {
    ws = null;
    if (pingTimer) { clearInterval(pingTimer); pingTimer = null; }

    resetSessionApprovals();

    // Token 无效 (4001)、被同设备新连接踢出 (4002) 或被用户移除 (4003)：停止重连
    if (code === 4001 || code === 4002 || code === 4003) {
      shouldReconnect = false;
      const reasonStr = reason?.toString() || "Kicked by another session";
      events?.onStatusChange("disconnected", `⚠ ${reasonStr}. ${t.connection.kicked}`);
      return;
    }

    events?.onStatusChange("disconnected");
    scheduleReconnect();
  });

  ws.on("error", (err) => {
    events?.onStatusChange("error", err.message);
    ws?.close();
  });
}

function scheduleReconnect(): void {
  if (!shouldReconnect) return;
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    if (shouldReconnect) {
      doConnect();
    }
  }, 3000);
}

// 等待 Web 前端审批的 pending map: request_id → {resolve, timer}
interface ConfirmResult {
  action: "approve" | "reject" | "always";
  password?: string;  // sudo 密码（如果用户填了的话）
}
const pendingConfirms: Map<string, {
  resolve: (result: ConfirmResult) => void;
  timer: ReturnType<typeof setTimeout>;
  privateKeyPem?: string;
}> = new Map();

// 本次连接中用户选择「始终允许」的操作指纹（连接断开后重置）
const approvedFingerprints = new Set<string>();

// 短期缓存的 sudo 密码（连接断开/过期后清空，绝不写盘）
let cachedSudoPassword: string | null = null;
let cachedSudoPasswordTimer: ReturnType<typeof setTimeout> | null = null;

function clearSudoPassword(): void {
  cachedSudoPassword = null;
  if (cachedSudoPasswordTimer) {
    clearTimeout(cachedSudoPasswordTimer);
    cachedSudoPasswordTimer = null;
  }
}

function rememberSudoPassword(password: string): void {
  cachedSudoPassword = password;
  if (cachedSudoPasswordTimer) clearTimeout(cachedSudoPasswordTimer);
  cachedSudoPasswordTimer = setTimeout(() => {
    cachedSudoPassword = null;
    cachedSudoPasswordTimer = null;
  }, SUDO_PASSWORD_TTL_MS);
}

function resetSessionApprovals(): void {
  approvedFingerprints.clear();
  clearSudoPassword();
  for (const [id, pending] of pendingConfirms) {
    clearTimeout(pending.timer);
    pending.resolve({ action: "reject" });
    pendingConfirms.delete(id);
  }
}

function requestFingerprint(request: ToolRequest): string {
  return JSON.stringify({ tool: request.tool, args: request.args });
}

/** 处理服务端发来的确认响应 */
export function handleConfirmResponse(
  id: string,
  approved: boolean,
  always?: boolean,
  password?: string,
  encryptedPassword?: string,
): void {
  const pending = pendingConfirms.get(id);
  if (pending) {
    clearTimeout(pending.timer);
    pendingConfirms.delete(id);
    let resolvedPassword = password;
    if (!resolvedPassword && encryptedPassword && pending.privateKeyPem) {
      try {
        resolvedPassword = decryptPassword(encryptedPassword, pending.privateKeyPem);
      } catch {
        pending.resolve({ action: "reject" });
        return;
      }
    }
    if (!approved) {
      pending.resolve({ action: "reject" });
    } else if (always) {
      pending.resolve({ action: "always", password: resolvedPassword });
    } else {
      pending.resolve({ action: "approve", password: resolvedPassword });
    }
  }
}

/** 通过 Web 前端请求用户审批（可带密码输入） */
function requestWebConfirmation(request: ToolRequest, needsPassword: boolean = false): Promise<ConfirmResult> {
  return new Promise((resolve) => {
    let privateKeyPem: string | undefined;
    let publicKeyPem: string | undefined;
    if (needsPassword) {
      const pair = generateKeyPairSync("rsa", {
        modulusLength: 2048,
        publicKeyEncoding: { type: "spki", format: "pem" },
        privateKeyEncoding: { type: "pkcs8", format: "pem" },
      });
      privateKeyPem = pair.privateKey;
      publicKeyPem = pair.publicKey;
    }
    // 发送确认请求到服务端，由 Web 前端展示
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: "confirm_request",
        id: request.id,
        tool: request.tool,
        args: request.args,
        needs_password: needsPassword,
        sudo_public_key: publicKeyPem,
      }));
    } else {
      resolve({ action: "reject" });
      return;
    }
    // 超时 120 秒自动拒绝
    const timer = setTimeout(() => {
      pendingConfirms.delete(request.id);
      resolve({ action: "reject" });
    }, 120000);
    pendingConfirms.set(request.id, { resolve, timer, privateKeyPem });
  });
}

/** 检测命令是否需要 sudo */
function needsSudo(command: string): boolean {
  return /\bsudo\b/i.test(command);
}

function getRequestPath(request: ToolRequest): string | null {
  const value = request.args.path;
  return typeof value === "string" ? value : null;
}

function requiresConfirmation(request: ToolRequest): boolean {
  if (request.tool === "run_command") {
    const command = typeof request.args.command === "string" ? request.args.command : "";
    return isDangerous(command);
  }
  if (request.tool === "write_file") {
    return true;
  }
  if (request.tool === "read_file" || request.tool === "list_files") {
    const path = getRequestPath(request);
    return !!path && isSensitivePath(path);
  }
  return false;
}

function isToolAllowed(tool: string): boolean {
  const allowedTools = getConfig().allowedTools;
  return allowedTools.includes(tool);
}

async function handleRequest(request: ToolRequest): Promise<void> {
  if (!isToolAllowed(request.tool)) {
    const response: ToolResponse = {
      id: request.id,
      error: `Tool not allowed by local agent config: ${request.tool}`,
    };
    sendResponse(response);
    events?.onResponse(response);
    return;
  }

  const command = typeof request.args.command === "string" ? request.args.command : "";
  const isSudoCommand = request.tool === "run_command" && needsSudo(command);
  const fingerprint = requestFingerprint(request);
  const hasApprovedFingerprint = approvedFingerprints.has(fingerprint);
  const shouldConfirm = requiresConfirmation(request);

  // Check if the operation needs confirmation. sudo without a cached password still asks for
  // a password even when auto-approve is enabled, because the agent cannot run it unattended.
  if (
    (!autoApprove && !hasApprovedFingerprint && shouldConfirm) ||
    (isSudoCommand && !cachedSudoPassword)
  ) {
    // sudo 命令：如果没有缓存密码则需要密码
    const requirePassword = isSudoCommand && !cachedSudoPassword;

    // 通过 Web 前端请求审批
    const result = await requestWebConfirmation(request, requirePassword);
    if (result.action === "always") {
      // 「始终允许」：本次连接后续相同操作跳过确认
      approvedFingerprints.add(fingerprint);
      if (result.password) {
        rememberSudoPassword(result.password);
      }
    } else if (result.action === "approve") {
      // 一次性使用密码
      if (result.password && !cachedSudoPassword) {
        rememberSudoPassword(result.password);
      }
    } else {
      const response: ToolResponse = {
        id: request.id,
        error: t.confirm.rejected,
      };
      sendResponse(response);
      events?.onResponse(response);
      return;
    }
  }

  // 执行命令（如果是 sudo 且有缓存密码，注入密码）
  if (isSudoCommand && cachedSudoPassword) {
    const response = await executeSudoTool(request, cachedSudoPassword);
    // 如果密码错误，清除缓存
    if (response.error && /incorrect password|try again|sorry/i.test(response.error)) {
      clearSudoPassword();
    }
    sendResponse(response);
    events?.onResponse(response);
  } else {
    const response = await executeTool(request);
    sendResponse(response);
    events?.onResponse(response);
  }
}

function sendResponse(response: ToolResponse): void {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(response));
  }
}
