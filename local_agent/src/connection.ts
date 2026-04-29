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
  onConfirmRequired: (
    request: ToolRequest,
    approve: () => void,
    reject: () => void
  ) => void;
}

let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let shouldReconnect = false;
let currentUrl = "";
let currentToken = "";
let events: ConnectionEvents | null = null;

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

  const separator = currentUrl.includes("?") ? "&" : "?";
  const fullUrl = `${currentUrl}${separator}token=${currentToken}`;
  ws = new WebSocket(fullUrl);

  ws.on("open", () => {
    events?.onStatusChange("connected");
  });

  ws.on("message", (data) => {
    try {
      const request = JSON.parse(data.toString()) as ToolRequest;
      events?.onRequest(request);
      handleRequest(request);
    } catch (err) {
      // ignore malformed messages
    }
  });

  ws.on("close", () => {
    ws = null;
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

function handleRequest(request: ToolRequest): void {
  // Check if dangerous
  if (
    request.tool === "run_command" &&
    typeof request.args.command === "string" &&
    isDangerous(request.args.command)
  ) {
    // Need user confirmation
    events?.onConfirmRequired(
      request,
      () => {
        const response = executeTool(request);
        sendResponse(response);
        events?.onResponse(response);
      },
      () => {
        const response: ToolResponse = {
          id: request.id,
          error: "User rejected this operation",
        };
        sendResponse(response);
        events?.onResponse(response);
      }
    );
    return;
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
