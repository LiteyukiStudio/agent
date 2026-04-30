/**
 * WebSocket 客户端：反向连接云端，接收并执行指令
 */
import WebSocket from "ws";
import { executeSudoTool, executeTool, isDangerous } from "./tools.js";
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

export function connect(url: string, token: string): void {
  currentUrl = url;
  currentToken = token;
  shouldReconnect = true;
  doConnect();
}

export function disconnect(): void {
  shouldReconnect = false;
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
        handleConfirmResponse(msg.id, msg.approved, msg.always, msg.password);
        return;
      }
      const request = msg as ToolRequest;
      events?.onRequest(request);
      handleRequest(request);
    } catch (err) {
      // ignore malformed messages
    }
  });

  ws.on("close", (code, reason) => {
    ws = null;
    if (pingTimer) { clearInterval(pingTimer); pingTimer = null; }

    // 被同设备新连接踢出 (4002) 或被用户移除 (4003)：停止重连
    if (code === 4002 || code === 4003) {
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
}> = new Map();

// 本次会话是否已启用「始终允许」模式（连接断开后重置）
let sessionAlwaysApprove = false;

// 本次会话缓存的 sudo 密码（连接断开后清空，绝不写盘）
let cachedSudoPassword: string | null = null;

/** 处理服务端发来的确认响应 */
export function handleConfirmResponse(id: string, approved: boolean, always?: boolean, password?: string): void {
  const pending = pendingConfirms.get(id);
  if (pending) {
    clearTimeout(pending.timer);
    pendingConfirms.delete(id);
    if (!approved) {
      pending.resolve({ action: "reject" });
    } else if (always) {
      pending.resolve({ action: "always", password });
    } else {
      pending.resolve({ action: "approve", password });
    }
  }
}

/** 通过 Web 前端请求用户审批（可带密码输入） */
function requestWebConfirmation(request: ToolRequest, needsPassword: boolean = false): Promise<ConfirmResult> {
  return new Promise((resolve) => {
    // 发送确认请求到服务端，由 Web 前端展示
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: "confirm_request",
        id: request.id,
        tool: request.tool,
        args: request.args,
        needs_password: needsPassword,
      }));
    }
    // 超时 120 秒自动拒绝
    const timer = setTimeout(() => {
      pendingConfirms.delete(request.id);
      resolve({ action: "reject" });
    }, 120000);
    pendingConfirms.set(request.id, { resolve, timer });
  });
}

/** 检测命令是否需要 sudo */
function needsSudo(command: string): boolean {
  return /\bsudo\b/i.test(command);
}

async function handleRequest(request: ToolRequest): Promise<void> {
  const command = typeof request.args.command === "string" ? request.args.command : "";
  const isSudoCommand = request.tool === "run_command" && needsSudo(command);

  // Check if dangerous — skip confirmation if autoApprove or sessionAlwaysApprove is on
  if (
    !autoApprove &&
    !sessionAlwaysApprove &&
    request.tool === "run_command" &&
    isDangerous(command)
  ) {
    // sudo 命令：如果没有缓存密码则需要密码
    const requirePassword = isSudoCommand && !cachedSudoPassword;

    // 通过 Web 前端请求审批
    const result = await requestWebConfirmation(request, requirePassword);
    if (result.action === "always") {
      // 「始终允许」：本次会话后续所有命令都跳过确认
      sessionAlwaysApprove = true;
      if (result.password) {
        cachedSudoPassword = result.password;
      }
    } else if (result.action === "approve") {
      // 一次性使用密码
      if (result.password && !cachedSudoPassword) {
        cachedSudoPassword = result.password;
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
    const response = executeSudoTool(request, cachedSudoPassword);
    // 如果密码错误，清除缓存
    if (response.error && response.error.includes("incorrect password")) {
      cachedSudoPassword = null;
    }
    sendResponse(response);
    events?.onResponse(response);
  } else {
    const response = executeTool(request);
    sendResponse(response);
    events?.onResponse(response);
  }
}

function sendResponse(response: ToolResponse): void {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(response));
  }
}
