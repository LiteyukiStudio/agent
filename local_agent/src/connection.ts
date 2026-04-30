/**
 * WebSocket 客户端：反向连接云端，接收并执行指令
 */
import WebSocket from "ws";
import { executeTool, isDangerous } from "./tools.js";
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
        handleConfirmResponse(msg.id, msg.approved, msg.always);
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
      events?.onStatusChange("disconnected", `⚠ ${reasonStr}. 不再重连。`);
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
const pendingConfirms: Map<string, {
  resolve: (result: "approve" | "reject" | "always") => void;
  timer: ReturnType<typeof setTimeout>;
}> = new Map();

// 本次会话中被「始终允许」的命令（连接断开后清空）
const sessionAllowedCommands: Set<string> = new Set();

/** 处理服务端发来的确认响应 */
export function handleConfirmResponse(id: string, approved: boolean, always?: boolean): void {
  const pending = pendingConfirms.get(id);
  if (pending) {
    clearTimeout(pending.timer);
    pendingConfirms.delete(id);
    if (!approved) {
      pending.resolve("reject");
    } else if (always) {
      pending.resolve("always");
    } else {
      pending.resolve("approve");
    }
  }
}

/** 通过 Web 前端请求用户审批 */
function requestWebConfirmation(request: ToolRequest): Promise<"approve" | "reject" | "always"> {
  return new Promise((resolve) => {
    // 发送确认请求到服务端，由 Web 前端展示
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: "confirm_request",
        id: request.id,
        tool: request.tool,
        args: request.args,
      }));
    }
    // 超时 120 秒自动拒绝
    const timer = setTimeout(() => {
      pendingConfirms.delete(request.id);
      resolve("reject");
    }, 120000);
    pendingConfirms.set(request.id, { resolve, timer });
  });
}

async function handleRequest(request: ToolRequest): Promise<void> {
  // Check if dangerous — skip confirmation if autoApprove is on
  if (
    !autoApprove &&
    request.tool === "run_command" &&
    typeof request.args.command === "string" &&
    isDangerous(request.args.command)
  ) {
    // 检查是否在本次会话中已被「始终允许」
    if (!sessionAllowedCommands.has(request.args.command)) {
      // 通过 Web 前端请求审批
      const result = await requestWebConfirmation(request);
      if (result === "always") {
        // 「始终允许」：记录该命令，后续不再询问
        sessionAllowedCommands.add(request.args.command);
      } else if (result === "reject") {
        const response: ToolResponse = {
          id: request.id,
          error: [
            "⚠️ 用户拒绝了此操作。该命令被安全策略拦截。",
            "【严格禁止】你不得通过任何方式绕过此限制，包括但不限于：",
            "- 使用 python/node/ruby/perl 等脚本语言间接执行系统命令",
            "- 使用 os.system()、subprocess、exec() 等函数",
            "- 将命令写入脚本文件再执行",
            "- 编码/混淆命令内容",
            "- 拆分命令为多步执行",
            "如果需要执行被拒绝的操作，请直接告知用户原因并请求用户手动执行。",
          ].join("\n"),
        };
        sendResponse(response);
        events?.onResponse(response);
        return;
      }
    }
  }

  const response = executeTool(request);
  sendResponse(response);
  events?.onResponse(response);
}

function sendResponse(response: ToolResponse): void {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(response));
  }
}
