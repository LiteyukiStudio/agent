/**
 * 配置管理：持久化存储连接信息
 */
import Conf from "conf";

interface Config {
  serverUrl: string | null;
  token: string | null;
  hostname: string | null;
  autoConnect: boolean;
  allowedTools: string[];
}

const config = new Conf<Config>({
  projectName: "liteyuki-local-agent",
  defaults: {
    serverUrl: null,
    token: null,
    hostname: null,
    autoConnect: true,
    allowedTools: ["run_command", "read_file", "write_file", "list_files"],
  },
});

export function getConfig(): Config {
  return {
    serverUrl: config.get("serverUrl"),
    token: config.get("token"),
    hostname: config.get("hostname"),
    autoConnect: config.get("autoConnect"),
    allowedTools: config.get("allowedTools"),
  };
}

export function setConnection(url: string, token: string, hostname?: string): void {
  config.set("serverUrl", url);
  config.set("token", token);
  if (hostname) config.set("hostname", hostname);
}

export function clearConnection(): void {
  config.set("serverUrl", null);
  config.set("token", null);
}

export function getConfigPath(): string {
  return config.path;
}
