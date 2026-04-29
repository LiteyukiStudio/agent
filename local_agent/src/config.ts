/**
 * 配置管理：持久化存储连接信息和设备标识
 *
 * 配置文件位于 ~/.config/liteyuki-local-agent/config.json（由 conf 库管理）
 * - deviceId: 首次运行自动生成 UUID，永不变更，唯一标识这台机器
 * - deviceName: 不持久化，每次启动实时获取（用户可能改系统名称）
 */
import { randomUUID } from "node:crypto";
import Conf from "conf";

interface Config {
  /** 本机唯一 ID（首次运行自动生成，永不变更） */
  deviceId: string;
  /** 服务器 base URL（如 https://flow.liteyuki.org） */
  baseUrl: string | null;
  /** API Token */
  token: string | null;
  /** 是否自动连接 */
  autoConnect: boolean;
  /** 允许执行的工具列表 */
  allowedTools: string[];
}

const config = new Conf<Config>({
  projectName: "liteyuki-local-agent",
  defaults: {
    deviceId: "",
    baseUrl: null,
    token: null,
    autoConnect: true,
    allowedTools: ["run_command", "read_file", "write_file", "list_files"],
  },
});

/**
 * 获取或生成设备唯一 ID。
 * 首次调用时生成 UUID 并持久化，后续永远返回同一个值。
 */
export function getDeviceId(): string {
  let id = config.get("deviceId");
  if (!id) {
    id = randomUUID();
    config.set("deviceId", id);
  }
  return id;
}

export function getConfig(): Config {
  return {
    deviceId: getDeviceId(),
    baseUrl: config.get("baseUrl"),
    token: config.get("token"),
    autoConnect: config.get("autoConnect"),
    allowedTools: config.get("allowedTools"),
  };
}

export function setConnection(baseUrl: string, token: string): void {
  config.set("baseUrl", baseUrl);
  config.set("token", token);
  getDeviceId();
}

export function clearConnection(): void {
  config.set("baseUrl", null);
  config.set("token", null);
  // 不清除 deviceId —— 机器标识永不变
}

export function getConfigPath(): string {
  return config.path;
}
